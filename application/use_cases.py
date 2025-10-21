from core.entities import ProductSearchResult
from core.ports import ProductRepository

class SearchProductsUseCase:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository
    
    def execute(self, query: str = "") -> ProductSearchResult:
        return self.product_repository.search_products(query)

class GetProductUseCase:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository
    
    def execute(self, product_id: str):
        return self.product_repository.get_product_by_id(product_id)

class NormalRingUseCase:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def execute(self):
        return self.repo.normal_ring()
