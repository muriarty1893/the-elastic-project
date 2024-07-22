import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, helpers
import logging
import os
import time

# Ürün bilgilerini tutan sınıf
class Product:
    def __init__(self, product_name=None, prices=None, rating_count=None):
        self.product_name = product_name
        self.prices = prices or []
        self.rating_count = rating_count or []

# Elasticsearch istemcisini oluşturur
def create_elastic_client():
    return Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

# Web'den veri çekme işlemi
def scrape_web():
    url = "https://www.trendyol.com/oyuncu-mouselari-x-c106088"  # Veri çekilecek web sitesi
    response = requests.get(url)
    products = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        product_nodes = soup.select('div.p-card-wrppr')  # Ürün kartlarını seçiyoruz

        for node in product_nodes:
            # Ürün ismi, fiyatı ve rating count bilgilerini çekiyoruz
            product_name_node = node.select_one("h3.prdct-desc-cntnr-ttl-w")
            price_node = node.select_one("div.prc-box-dscntd")
            rating_count_node = node.select_one("span.ratingCount")

            product_name = (
                " ".join([
                    product_name_node.select_one("span.prdct-desc-cntnr-ttl").get_text().strip(),
                    product_name_node.select_one("span.prdct-desc-cntnr-name").get_text().strip(),
                    product_name_node.select_one("div.product-desc-sub-text").get_text().strip()
                ])
                if product_name_node else None
            )
            price = price_node.get_text().strip() if price_node else None
            rating_count = rating_count_node.get_text().strip() if rating_count_node else None

            product = Product(
                product_name=product_name,
                prices=[price],
                rating_count=rating_count
            )
            products.append(product)
        
        return products, soup  # soup değişkenini de döndürüyoruz

    return products, None

# Elasticsearch'e ürünleri indeksler
def index_products(client, products, logger):
    actions = [
        {
            "_index": "gaming-mous",
            "_source": {
                "product_name": product.product_name,
                "prices": product.prices,
                "rating_count": product.rating_count
            }
        }
        for product in products
    ]

    helpers.bulk(client, actions)

# Elasticsearch'te index varsa kontrol eder, yoksa oluşturur
def create_index_if_not_exists(client, logger):
    if not client.indices.exists(index="gaming-mous"):
        client.indices.create(index="gaming-mous", body={
            "mappings": {
                "properties": {
                    "product_name": {"type": "text"},
                    "prices": {"type": "keyword"},
                    "rating_count": {"type": "keyword"}
                }
            }
        })

# Elasticsearch'te verilen metinle eşleşen ürünleri arar
def search_products(client, search_text, logger):
    search_response = client.search(
        index="gaming-mous",
        body={
            "query": {
                "fuzzy": {
                    "product_name": {
                        "value": search_text,
                        "fuzziness": 2
                    }
                }
            },
            "sort": {
                "_score": {"order": "desc"}
            }
        }
    )

    results = search_response['hits']['hits']
    print("Results:\n--------------------------------------------")
    for i, result in enumerate(results[:10]):
        product = result["_source"]
        print(f"Product: {product['product_name']}")
        for price in product.get('prices', []):
            print(f"Price: {price}")
        print(f"Rating Count: {product.get('rating_count', 'N/A')}")
        print("--------------------------------------------")
    print(f"{len(results)} match(es).")

# Ana fonksiyon
def main():
    # Logger kurulumu
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ProductScraper")
    
    # Elasticsearch istemcisini oluşturur
    client = create_elastic_client()

    # Elasticsearch'te index varsa kontrol eder, yoksa oluşturur
    create_index_if_not_exists(client, logger)

    # Web sitesinden ürünleri çeker
    products, soup = scrape_web()

    flag_file_path = "flags/indexing_done_31.flag"  # Dosya oluşturmak için

    # Dosyanın oluşturulup oluşturulmadığını kontrol eder
    if not os.path.exists(flag_file_path):
        # Çekilen ürünleri Elasticsearch'e indeksler
        index_products(client, products, logger)
        # Dosya oluşturularak indekslemenin yapıldığını işaretler
        os.makedirs(os.path.dirname(flag_file_path), exist_ok=True)
        with open(flag_file_path, 'w') as flag_file:
            flag_file.write('')

    item = "SteelSeries"  # Kullanıcı girdisi

    start_time = time.time()
    search_products(client, item, logger)  # Elasticsearch'te girilen kelimeyi arar
    search_duration = time.time() - start_time
    
    # Sıralama seçeneğini yazdırır
    print("Sorting Option:\n--------------------------------------------")
    sorting_option = soup.select_one('div.selected-order')
    if sorting_option:
        print(f"Sorting Option: {sorting_option.get_text().strip()}")
    total_duration = time.time() - start_time
    print(f"Search completed in {search_duration * 1000:.2f} ms.")
    print(f"All completed in {total_duration * 1000:.2f} ms.")

if __name__ == "__main__":
    main()
