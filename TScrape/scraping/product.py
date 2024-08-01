class Product:
    def __init__(self, product_name=None, prices=None, rating_count=None, attributes=None):
        self.product_name = product_name
        self.prices = prices or []
        self.rating_count = rating_count or []
        self.attributes = attributes or {}