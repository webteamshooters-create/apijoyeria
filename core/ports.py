from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Product, ProductSearchResult

class ProductRepository(ABC):
    """Puerto para acceso a datos de productos"""
    
    @abstractmethod
    def search_products(self, query: str = "") -> ProductSearchResult:
        pass
    
    @abstractmethod
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        pass

class ImageService(ABC):
    """Puerto para servicios de imágenes"""
    
    @abstractmethod
    def get_image_url(self, product_id: str) -> Optional[str]:
        pass