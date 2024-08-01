from elasticsearch import helpers
from .client import create_elastic_client

class Indexer:
    def __init__(self, indexname):
        self.indexname = indexname
        self.client = create_elastic_client()

    def create_index_if_not_exists(self, logger):
        if not self.client.indices.exists(index=self.indexname):
            self.client.indices.create(index=self.indexname, body={
                "mappings": {
                    "properties": {
                        "product_name": {"type": "text"},
                        "prices": {"type": "float"},
                        "rating_count": {"type": "keyword"},
                        "attributes": {"type": "object", "enabled": False}
                    }
                }
            })

    def index_products(self, products, logger):
        actions = [
            {
                "_index": self.indexname,
                "_source": {
                    "product_name": product.product_name,
                    "prices": product.prices,
                    "rating_count": product.rating_count,
                    "attributes": product.attributes
                }
            }
            for product in products
        ]
        helpers.bulk(self.client, actions)
