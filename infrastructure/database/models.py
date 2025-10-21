from dataclasses import dataclass
from typing import List

@dataclass
class DatabaseConfig:
    db_path: str
    products_table: str = "products"
    product_images_table: str = "product_images"
    id_candidates: List[str] = None
    
    def __post_init__(self):
        if self.id_candidates is None:
            self.id_candidates = ["id", "product_id", "sku", "codigo", "code", "id_producto"]