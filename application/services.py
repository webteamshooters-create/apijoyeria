from .use_cases import SearchProductsUseCase, GetProductUseCase, NormalRingUseCase

class ProductService:
    def __init__(self, search_use_case, get_use_case, repo):
        self.search_use_case = search_use_case
        self.get_use_case = get_use_case
        self.repo = repo

    def search_products(self, query: str = ""):
        # aquí usas el caso de uso
        return self.search_use_case.execute(query)
    
    def get_product(self, product_id: str):
        return self.get_use_case.execute(product_id)

    def normal_ring(self):
        # aquí sí puedes usar el repo directamente
        return self.repo.normal_ring()
    
    def best_sellers(self):
        return self.repo.best_sellers()