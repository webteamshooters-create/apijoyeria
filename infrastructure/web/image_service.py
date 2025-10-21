from pathlib import Path
from flask import url_for, send_from_directory
from typing import Optional
from core.ports import ImageService

class LocalImageService(ImageService):
    def __init__(self, products_dir: str):
        self.products_dir = Path(products_dir)
    
    def get_image_url(self, product_id: str) -> Optional[str]:
        if not product_id:
            return None
        
        filename = f"{product_id}.png"
        file_path = self.products_dir / filename
        
        if file_path.exists():
            return url_for("product_image", filename=filename, _external=True)
        return None
    
    def serve_image_file(self, filename: str):
        file_path = self.products_dir / filename
        if not file_path.exists():
            from flask import abort
            abort(404)
        
        return send_from_directory(
            directory=str(self.products_dir),
            path=filename,
            mimetype="image/png",
            as_attachment=False,
            max_age=86400
        )