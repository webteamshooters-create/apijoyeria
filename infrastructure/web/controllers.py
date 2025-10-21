# controllers.py
from flask import request, abort, current_app
from urllib.parse import urljoin
from core.ports import ImageService
from application.services import ProductService
import unicodedata, re, json

# ========= utils =========
def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()

def tokens_from_category(cat_norm: str):
    if not cat_norm:
        return []
    return [t for t in re.split(r"[^a-z0-9]+", cat_norm) if t]

def title_case_basic(s: str):
    if not s:
        return ""
    prep = {"de","del","la","las","los","y","o","en","con","para","por","al"}
    parts = re.sub(r"\s+", " ", str(s)).strip().split(" ")
    out = []
    for i, w in enumerate(parts):
        lw = w.lower()
        out.append(lw if (i > 0 and lw in prep) else lw[:1].upper() + lw[1:])
    return " ".join(out)

# ========= mapeo de encabezados -> claves canónicas (SOLO renombrar keys en el JSON) =========
KEY_MAP = {
    "descripcion": "Descripción",
    "acabado": "Acabado", 
    "cadena": "Cadena",
    "cierre": "Cierre",
    "corte": "Corte",
    "detalle": "Detalle",
    "dije": "Dije",
    "disenio": "Diseño",
    "estilo": "Estilo",
    "ideal_para": "Ideal para",
    "inspiracion": "Inspiración",
    "lado1": "Lado 1",
    "lado2": "Lado 2", 
    "material": "Material",
    "modelo": "Modelo",
    "montura": "Montura",
    "origen": "Origen",
    "piedra": "Piedra",
    "piedra_central": "Piedra Central",
    "piedras": "Piedras",
    "piezas": "Piezas",
    "set": "Set",
    "significado": "Significado",
    "tamanio": "Tamaño",
    "tamanios_disponibles": "Tamaños Disponibles",
    "uso": "Uso",
    "versatilidad": "Versatilidad",
    "categoria": "Categoría",
}
# soporto variaciones (con/sin acentos, mayúsculas, espacios)
KEY_MAP_NORM = {norm(k): v for k, v in KEY_MAP.items()}

def remap_keys(item: dict) -> dict:
    out = {}
    for k, v in (item or {}).items():
        nk = norm(k)                 # normalizo para buscar en el mapa
        canon = KEY_MAP_NORM.get(nk) # si hay mapeo, uso la clave canónica
        if canon:
            out[canon] = v
        else:
            # si no hay mapeo, conservo la clave ORIGINAL tal cual (sin deformarla)
            out[k] = v
    # migración de categoría legacy -> categoria si aún viene con ese nombre
    if "categoria" not in out:
        for lk in ("COLECCION/ SIMBOLISMO", "COLECCION / SIMBOLISMO", "coleccion/simbolismo"):
            if lk in out and out[lk]:
                out["categoria"] = out[lk]
                break
    return out

# ========= controlador =========
class ProductController:
    def __init__(self, product_service: ProductService, image_service: ImageService):
        self.product_service = product_service
        self.image_service = image_service

    def search_products(self):
        try:
            q = (request.args.get("q") or "").strip()
            result = self.product_service.search_products(q)
            base_url = request.url_root

            enriched = []
            for product in result.data:
                # 1) copia base de BD y renombra solo las keys necesarias
                item = remap_keys(dict(product.data or {}))

                # 2) normalización y tokens de categoría (para front)
                cat_raw = item.get("categoria", "")
                cat_norm = norm(cat_raw)
                item["categoria_norm"] = cat_norm
                item["categoria_tokens"] = tokens_from_category(cat_norm)

                # 3) nombre presentable (no pisa tu 'nombres'); si no existe, usa "Producto"
                nombres_raw = (
                    item.get("nombres")
                    or item.get("nombre")
                    or item.get("producto")
                    or item.get("title")
                    or item.get("título")
                )
                item["nombres_display"] = title_case_basic(nombres_raw or "Producto")

                # 4) imágenes y URLs absolutas
                imgs = sorted(getattr(product, "images", []) or [], key=lambda i: (i.position or 0))
                item["images"] = [
                    {
                        "product_id": img.product_id,
                        "path": img.path,
                        "position": img.position,
                        "is_primary": img.is_primary,
                        "original_url": img.original_url,
                    }
                    for img in imgs
                ]
                for idx, img in enumerate(imgs, start=1):
                    key = "image_url" if idx == 1 else f"image_url{idx}"
                    item[key] = urljoin(base_url, (img.path or "").lstrip("/"))

                enriched.append(item)

            payload = {"total": result.total, "data": enriched}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json; charset=utf-8",
            )
        except Exception as e:
            payload = {"error": str(e)}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=500,
                mimetype="application/json; charset=utf-8",
            )

    def serve_product_image(self, filename: str):
        if not filename.lower().endswith(".png"):
            abort(404)
        return self.image_service.serve_image_file(filename)
    
    def normal_ring(self):
        try:
            result = self.product_service.normal_ring()
            base_url = request.url_root

            enriched = []
            for product in result:
                item = remap_keys(dict(product.data or {}))

                # Normalización de categoría
                cat_raw = item.get("categoria", "")
                cat_norm = norm(cat_raw)
                item["categoria_norm"] = cat_norm
                item["categoria_tokens"] = tokens_from_category(cat_norm)

                # Nombre display
                nombres_raw = (
                    item.get("nombres")
                    or item.get("nombre")
                    or item.get("producto")
                    or item.get("title")
                    or item.get("título")
                )
                item["nombres_display"] = title_case_basic(nombres_raw or "Producto")

                # Imágenes
                imgs = sorted(getattr(product, "images", []) or [], key=lambda i: (i.position or 0))
                item["images"] = [
                    {
                        "product_id": img.product_id,
                        "path": img.path,
                        "position": img.position,
                        "is_primary": img.is_primary,
                        "original_url": img.original_url,
                    }
                    for img in imgs
                ]
                for idx, img in enumerate(imgs, start=1):
                    key = "image_url" if idx == 1 else f"image_url{idx}"
                    item[key] = urljoin(base_url, (img.path or "").lstrip("/"))

                enriched.append(item)

            payload = {"total": len(enriched), "data": enriched}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json; charset=utf-8",
            )
        except Exception as e:
            payload = {"error": str(e)}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=500,
                mimetype="application/json; charset=utf-8",
            )
    
    def best_sellers(self):
        try:
            products = self.product_service.best_sellers()
            base_url = request.url_root

            enriched = []
            for product in products:
                item = remap_keys(dict(product.data or {}))

                # normalización de categoría
                cat_raw = item.get("categoria", "")
                cat_norm = norm(cat_raw)
                item["categoria_norm"] = cat_norm
                item["categoria_tokens"] = tokens_from_category(cat_norm)

                # nombre presentable
                nombres_raw = (
                    item.get("nombres")
                    or item.get("nombre")
                    or item.get("producto")
                    or item.get("title")
                    or item.get("título")
                )
                item["nombres_display"] = title_case_basic(nombres_raw or "Producto")

                # imágenes y URLs absolutas
                imgs = sorted(getattr(product, "images", []) or [], key=lambda i: (i.position or 0))
                item["images"] = [
                    {
                        "product_id": img.product_id,
                        "path": img.path,
                        "position": img.position,
                        "is_primary": img.is_primary,
                        "original_url": img.original_url,
                    }
                    for img in imgs
                ]
                for idx, img in enumerate(imgs, start=1):
                    key = "image_url" if idx == 1 else f"image_url{idx}"
                    item[key] = urljoin(base_url, (img.path or "").lstrip("/"))

                enriched.append(item)

            payload = {"total": len(enriched), "data": enriched}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json; charset=utf-8",
            )
        except Exception as e:
            payload = {"error": str(e)}
            return current_app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=500,
                mimetype="application/json; charset=utf-8",
            )
