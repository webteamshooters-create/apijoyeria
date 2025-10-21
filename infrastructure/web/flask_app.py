from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from pathlib import Path

from infrastructure.database.repositories import SQLiteProductRepository
from infrastructure.database.models import DatabaseConfig

from infrastructure.web.controllers import ProductController
from infrastructure.web.image_service import LocalImageService

from application.use_cases import SearchProductsUseCase, GetProductUseCase
from application.services import ProductService


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Configuración
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DB_PATH = (BASE_DIR / "data.sqlite").resolve()
    PRODUCTS_DIR = (BASE_DIR / "resources" / "products").resolve()

    # Inyección de dependencias
    db_config = DatabaseConfig(db_path=str(DB_PATH))
    product_repository = SQLiteProductRepository(db_config)

    # Servicio de imágenes local (solo sirve archivos; las imágenes por producto
    # ya vienen desde el SQLiteProductRepository en cada Product.images)
    image_service = LocalImageService(str(PRODUCTS_DIR))

    search_use_case = SearchProductsUseCase(product_repository)
    get_use_case = GetProductUseCase(product_repository)

    # Nota: ahora inyectamos también el repo en ProductService para normal_ring()
    product_service = ProductService(search_use_case, get_use_case, product_repository)

    product_controller = ProductController(product_service, image_service)

    # Rutas
    @app.route("/ping", methods=["GET", "OPTIONS"])
    @cross_origin(origins="*")
    def ping():
        if request.method == "OPTIONS":
            return ("", 204)
        return product_controller.ping()

    @app.route("/products", methods=["GET", "OPTIONS"])
    @cross_origin(origins="*")
    def products():
        if request.method == "OPTIONS":
            return ("", 204)
        return product_controller.search_products()

    @app.route("/assets/products/<path:filename>", methods=["GET"])
    def product_image(filename: str):
        return product_controller.serve_product_image(filename)

    @app.route("/products/normal-ring", methods=["GET", "OPTIONS"])
    @cross_origin(origins="*")
    def normal_ring():
        if request.method == "OPTIONS":
            return ("", 204)
        return product_controller.normal_ring()
    
    @app.route("/products/best-sellers", methods=["GET", "OPTIONS"])
    @cross_origin(origins="*")
    def best_sellers():
        if request.method == "OPTIONS":
            return ("", 204)
        return product_controller.best_sellers()

    # Manejo de errores
    @app.errorhandler(Exception)
    def handle_any_error(e):
        return jsonify({"error": str(e)}), 500

    # CORS headers
    @app.after_request
    def add_cors_headers(resp):
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        resp.headers.setdefault("Access-Control-Allow-Methods", "GET, OPTIONS")
        resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        resp.headers.setdefault("Access-Control-Max-Age", "86400")
        return resp

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5057, debug=True)