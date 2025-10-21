import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from core.entities import Product, ProductImage, ProductSearchResult
from core.ports import ProductRepository
from .models import DatabaseConfig

def quote_ident(s: str) -> str:
    """Cita un identificador SQLite, escapando comillas dobles."""
    return '"' + str(s).replace('"', '""') + '"'

class SQLiteProductRepository(ProductRepository):
    """Adaptador para SQLite (solo devuelve imágenes existentes en la BD)."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._verify_database()

    def _verify_database(self):
        if not Path(self.config.db_path).exists():
            raise FileNotFoundError(f"No se encontró la base de datos: {self.config.db_path}")

    def _get_connection(self):
        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _detect_id_column(self, conn) -> str:
        table = quote_ident(self.config.products_table)
        cur = conn.execute(f'PRAGMA table_info({table});')
        cols = [r["name"] for r in cur.fetchall()]
        if not cols:
            return "id"
        lower_cols = {c.lower(): c for c in cols}
        for candidate in self.config.id_candidates:
            if candidate in lower_cols:
                return lower_cols[candidate]
        return cols[0]

    def _list_columns(self, conn) -> List[str]:
        table = quote_ident(self.config.products_table)
        cur = conn.execute(f'PRAGMA table_info({table});')
        return [r["name"] for r in cur.fetchall()]

    def _build_like_clause(self, query: str, columns: List[str]) -> Tuple[str, List[str]]:
        like = f"%{query}%"
        parts = [f'{quote_ident(c)} LIKE ?' for c in columns]
        return "(" + " OR ".join(parts) + ")", [like] * len(columns)

    def _row_to_product(self, row: dict, images: List[ProductImage], id_column: str) -> Product:
        product_data = dict(row)
        product_id = str(product_data.get(id_column) or "")
        return Product(
            id=product_id,
            data=product_data,
            images=images
        )

    def search_products(self, query: str = "") -> ProductSearchResult:
        conn = self._get_connection()
        try:
            id_column = self._detect_id_column(conn)
            columns = self._list_columns(conn)
            if not columns:
                return ProductSearchResult(total=0, data=[])

            table = quote_ident(self.config.products_table)
            columns_str = ", ".join(quote_ident(c) for c in columns)
            sql = f"SELECT {columns_str} FROM {table}"
            params: List[str] = []

            if query.strip():
                where_clause, where_params = self._build_like_clause(query, columns)
                sql += f" WHERE {where_clause}"
                params.extend(where_params)

            # 👉 aquí agregamos el ORDER BY nombres
            sql += f" ORDER BY {quote_ident('nombres')} ASC"

            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
            products_with_images = self._load_product_images(conn, rows, id_column)

            return ProductSearchResult(total=len(products_with_images), data=products_with_images)
        finally:
            conn.close()


    def _load_product_images(self, conn, rows: List[dict], id_column: str) -> List[Product]:
        if not rows:
            return []

        # Construye lista de IDs (únicos, no vacíos)
        product_ids = [str(r.get(id_column) or "").strip() for r in rows]
        product_ids = [pid for pid in dict.fromkeys(product_ids) if pid]  # únicos + no vacíos

        images_by_product: Dict[str, List[ProductImage]] = {}
        if product_ids:
            placeholders = ",".join("?" for _ in product_ids)
            img_table = quote_ident(self.config.product_images_table)
            images_sql = f"""
                SELECT product_id, path, position, is_primary, original_url
                FROM {img_table}
                WHERE product_id IN ({placeholders})
                ORDER BY product_id, position ASC
            """
            for img_row in conn.execute(images_sql, product_ids).fetchall():
                d = dict(img_row)
                pid = str(d["product_id"])
                images_by_product.setdefault(pid, []).append(ProductImage(
                    product_id=pid,
                    path=d["path"],
                    position=int(d["position"]) if d["position"] is not None else 0,
                    is_primary=bool(d["is_primary"]),
                    original_url=d.get("original_url")
                ))

        products: List[Product] = []
        for row in rows:
            pid = str(row.get(id_column) or "").strip()
            images = images_by_product.get(pid, [])  # <- SOLO lo que exista en BD
            products.append(self._row_to_product(row, images, id_column))
        return products

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        conn = self._get_connection()
        try:
            id_column = self._detect_id_column(conn)
            columns = self._list_columns(conn)
            if not columns:
                return None

            table = quote_ident(self.config.products_table)
            columns_str = ", ".join(quote_ident(c) for c in columns)
            sql = f"SELECT {columns_str} FROM {table} WHERE {quote_ident(id_column)} = ?"
            row = conn.execute(sql, [product_id]).fetchone()
            if not row:
                return None

            product_data = dict(row)
            images = self._get_images_for_product(conn, product_id)
            return self._row_to_product(product_data, images, id_column)
        finally:
            conn.close()

    def _get_images_for_product(self, conn, product_id: str) -> List[ProductImage]:
        img_table = quote_ident(self.config.product_images_table)
        sql = f"""
            SELECT product_id, path, position, is_primary, original_url
            FROM {img_table}
            WHERE product_id = ?
            ORDER BY position ASC
        """
        out: List[ProductImage] = []
        for r in conn.execute(sql, [product_id]).fetchall():
            d = dict(r)
            out.append(ProductImage(
                product_id=str(d["product_id"]),
                path=d["path"],
                position=int(d["position"]) if d["position"] is not None else 0,
                is_primary=bool(d["is_primary"]),
                original_url=d.get("original_url")
            ))
        return out
    
    def normal_ring(self) -> List[Product]:
        """
        Devuelve los productos cuyo nombre contenga 'anillo'
        y cuya categoría no contenga 'compromiso'.
        Incluye imágenes relacionadas.
        """
        conn = self._get_connection()
        try:
            id_column = self._detect_id_column(conn)
            columns = self._list_columns(conn)
            if not columns:
                return []

            table = quote_ident(self.config.products_table)
            columns_str = ", ".join(quote_ident(c) for c in columns)
            sql = f"""
                SELECT {columns_str}
                FROM {table}
                WHERE LOWER(nombres) LIKE '%anillo%'
                AND LOWER(categoria) NOT LIKE '%compromiso%'
            """
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            return self._load_product_images(conn, rows, id_column)
        finally:
            conn.close()
    
    def best_sellers(self) -> List[Product]:
        """
        Devuelve productos marcados como BEST SELLER (case-insensitive),
        incluyendo sus imágenes.
        """
        conn = self._get_connection()
        try:
            id_column = self._detect_id_column(conn)
            columns = self._list_columns(conn)
            if not columns:
                return []

            table = quote_ident(self.config.products_table)
            columns_str = ", ".join(quote_ident(c) for c in columns)

            # COLLATE NOCASE para tolerar 'Best Seller', 'best seller', etc.
            sql = f"""
                SELECT {columns_str}
                FROM {table}
                WHERE {quote_ident('plus')} = 'BEST SELLER' COLLATE NOCASE
            """

            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            return self._load_product_images(conn, rows, id_column)
        finally:
            conn.close()

    
    