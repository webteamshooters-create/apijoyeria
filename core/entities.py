from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ProductImage:
    product_id: str
    path: str
    position: int
    is_primary: bool
    original_url: Optional[str] = None

@dataclass
class Product:
    id: str
    data: dict  # Datos dinámicos
    images: List[ProductImage]
    
    @property
    def image_url(self) -> Optional[str]:
        """URL de la imagen principal"""
        principal = next((img for img in self.images if img.is_primary), None)
        return principal.path if principal else None

@dataclass
class ProductSearchResult:
    total: int
    data: List[Product]