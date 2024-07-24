import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, helpers
import logging
import os
import time

indexname="ml-4"

class Product:
    def __init__(self, product_name=None, prices=None, rating_count=None, dpi=None, rgb_lighting=None, mouse_type=None, button_count=None):
        self.product_name = product_name
        self.prices = prices or []
        self.rating_count = rating_count or []
        self.dpi = dpi or ""
        self.rgb_lighting = rgb_lighting or ""
        self.mouse_type = mouse_type or ""
        self.button_count = button_count or ""

def create_elastic_client():
    return Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

def scrape_web():
    url = "https://www.trendyol.com/sr/oyuncu-mouselari-x-c106088?sst=BEST_SELLER"
    response = requests.get(url)
    products = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        product_nodes = soup.select('div.p-card-wrppr')

        for node in product_nodes:

            product_name_node = node.select_one("h3.prdct-desc-cntnr-ttl-w")
            price_node = node.select_one("div.prc-box-dscntd")
            rating_count_node = node.select_one("span.ratingCount")
            
            attributes = {
                'dpi': 'Mouse Hassasiyeti (Dpi)',
                'rgb_lighting': 'RGB Aydınlatma',
                'mouse_type': 'Mouse Tipi',
                'button_count': 'Buton Sayısı'
            }
            
            attribute_values = {}
            for key, title in attributes.items():
                attribute_node = node.select_one(f'span[title="{title}"] + span.attribute-value > div.attr-name.attr-name-w')
                attribute_values[key] = attribute_node.get_text().strip() if attribute_node else None

            product_name = (
                " ".join([
                    product_name_node.select_one("span.prdct-desc-cntnr-ttl").get_text().strip() if product_name_node.select_one("span.prdct-desc-cntnr-ttl") else "",
                    product_name_node.select_one("span.prdct-desc-cntnr-name").get_text().strip() if product_name_node.select_one("span.prdct-desc-cntnr-name") else "",
                    product_name_node.select_one("div.product-desc-sub-text").get_text().strip() if product_name_node.select_one("div.product-desc-sub-text") else ""
                ])
                if product_name_node else None
            )
            price = price_node.get_text().strip() if price_node else None
            if price:
                price = float(price.replace("TL", "").replace(",", "").replace(".", ""))
            rating_count = rating_count_node.get_text().strip() if rating_count_node else None

            product = Product(
                product_name=product_name,
                prices=[price] if price else [],
                rating_count=rating_count,
                dpi=attribute_values['dpi'],
                rgb_lighting=attribute_values['rgb_lighting'],
                mouse_type=attribute_values['mouse_type'],
                button_count=attribute_values['button_count']
            )
            products.append(product)
        
        return products, soup

    return products, None

def index_products(client, products, logger):
    actions = [
        {
            "_index": indexname,
            "_source": {
                "product_name": product.product_name,
                "prices": product.prices,
                "rating_count": product.rating_count,
                "dpi": product.dpi,
                "rgb_lighting": product.rgb_lighting,
                "mouse_type": product.mouse_type,
                "button_count": product.button_count
            }
        }
        for product in products
    ]

    helpers.bulk(client, actions)

def create_index_if_not_exists(client, logger):
    if not client.indices.exists(index=indexname):
        client.indices.create(index=indexname, body={
            "mappings": {
                "properties": {
                    "product_name": {"type": "text"},
                    "prices": {"type": "float"},
                    "rating_count": {"type": "keyword"},
                    "dpi": {"type": "text"},
                    "rgb_lighting": {"type": "text"},
                    "mouse_type": {"type": "text"},
                    "button_count": {"type": "text"}
                }
            }
        })

def search_products(client, search_text, logger):
    search_response = client.search(
        index=indexname,
        body={
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": search_text,
                                "fields": ["product_name^3", "rating_count", "dpi", "rgb_lighting", "mouse_type", "button_count"],
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "range": {
                                "prices": {
                                    "gte": 0
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "price_ranges": {
                    "range": {
                        "field": "prices",
                        "ranges": [
                            {"to": 50},
                            {"from": 50, "to": 1000},
                            {"from": 1000}
                        ]
                    }
                }
            }
        }
    )

    results = search_response['hits']['hits']
    print("Results:\n--------------------------------------------")
    print(f"{len(results)} match(es):")
    print("--------------------------------------------")
    for i, result in enumerate(results[:10]):
        product = result["_source"]
        print(f"Product: {product['product_name']}")
        for price in product.get('prices', []):
            print(f"Price: {price}")
            carry = product.get('rating_count', 'N/A').replace("(","").replace(")","")
        if(int(carry) < 100):
            print(f"Rating Count: {product.get('rating_count', 'N/A')} warning! number of rate is below 100")
            print("--------------------------------------------")
        else:
            print(f"Rating Count: {product.get('rating_count', 'N/A')}")
            print("--------------------------------------------")
        print(f"DPI: {product.get('dpi', 'N/A')}")
        print(f"RGB Lighting: {product.get('rgb_lighting', 'N/A')}")
        print(f"Mouse Type: {product.get('mouse_type', 'N/A')}")
        print(f"Button Count: {product.get('button_count', 'N/A')}")

    print("Aggregation Results:\n--------------------------------------------")
    for bucket in search_response['aggregations']['price_ranges']['buckets']:
        print(f"Price range: {bucket['key']} - Doc count: {bucket['doc_count']}")

def features():
    print("praise")

def main():
    start_time1 = time.time()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ProductScraper")
    
    client = create_elastic_client()

    create_index_if_not_exists(client, logger)

    products, soup = scrape_web()

    flag_file_path = "flags/indexing_done_49.flag"

    if not os.path.exists(flag_file_path):

        index_products(client, products, logger)

        os.makedirs(os.path.dirname(flag_file_path), exist_ok=True)

        with open(flag_file_path, 'w') as flag_file:
            flag_file.write('')

    item = "steelseries"
    if os.path.exists(flag_file_path):
        start_time2 = time.time()
        search_products(client, item, logger)
        search_duration = time.time() - start_time2

        print("Sorting Option:\n--------------------------------------------")
        sorting_option = soup.select_one('div.selected-order')
        if sorting_option:
            print(f"Sorting Option: {sorting_option.get_text().strip()}")
        total_duration = time.time() - start_time1
        print(f"Search completed in {search_duration * 1000:.2f} ms.")
        print(f"All completed in {total_duration * 1000:.2f} ms.")

if __name__ == "__main__":
    main()
# PRAISE
