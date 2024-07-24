import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, helpers
import logging
import os
import time
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import numpy as np


indexname = "indext7"
flagname = "flags/indexing_done_59.flag"

class Product:
    def __init__(self, product_name=None, prices=None, rating_count=None, attributes=None):
        self.product_name = product_name
        self.prices = prices or []
        self.rating_count = rating_count or []
        self.attributes = attributes or {}

def create_elastic_client():
    return Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

def scrape_web():
    url = "https://www.trendyol.com/sr/oyuncu-mouselari-x-c106088?sst=BEST_SELLER"
    response = requests.get(url)
    products = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        product_nodes = soup.select('div.p-card-chldrn-cntnr.card-border')

        for node in product_nodes:
            product_name_node = node.select_one("h3.prdct-desc-cntnr-ttl-w")
            price_node = node.select_one("div.prc-box-dscntd")
            rating_count_node = node.select_one("span.ratingCount")
            product_link_node = node.select_one("a")

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
            product_link = f"https://www.trendyol.com{product_link_node['href']}" if product_link_node else None

            attributes = scrape_product_details(product_link) if product_link else {}

            product = Product(
                product_name=product_name,
                prices=[price] if price else [],
                rating_count=rating_count,
                attributes=attributes
            )
            products.append(product)

        return products, soup

    return products, None

def scrape_product_details(url):
    response = requests.get(url)
    attributes = {}

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        attribute_mappings = {
            'Mouse Hassasiyeti (Dpi)': 'dpi',
            'RGB Aydınlatma': 'rgb_lighting',
            'Mouse Tipi': 'mouse_type',
            'Buton Sayısı': 'button_count'
        }

        for attr_name, key in attribute_mappings.items():
            attr_node = soup.select_one(f'span[title="{attr_name}"] + span.attribute-value > div.attr-name.attr-name-w')
            attributes[key] = attr_node.get_text().strip() if attr_node else None

    return attributes

def index_products(client, products, logger):
    actions = [
        {
            "_index": indexname,
            "_source": {
                "product_name": product.product_name,
                "prices": product.prices,
                "rating_count": product.rating_count,
                "attributes": product.attributes
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
                    "attributes": {"type": "object", "enabled": False}
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
                                "fields": ["product_name^3", "rating_count"],
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
    print(f"\n\n{len(results)} match(es):")
    print("Results:\n--------------------------------------------")
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

    print("Aggregation Results:\n--------------------------------------------")
    for bucket in search_response['aggregations']['price_ranges']['buckets']:
        print(f"Price range: {bucket['key']} - Doc count: {bucket['doc_count']}")

def parse_dpi(dpi_str):
    try:
        if ' - ' in dpi_str:
            dpi_values = list(map(int, dpi_str.split(' - ')))
            return int(np.mean(dpi_values))
        return int(dpi_str.split()[0])
    except:
        return 0

def collect_data(products):
    data = []
    for product in products:
        product_data = {
            "product_name": product.product_name,
            "price": product.prices[0] if product.prices else 0,
            "rating_count": int(product.rating_count.replace("(","").replace(")","")) if product.rating_count else 0,
            "dpi": parse_dpi(product.attributes.get("dpi", "0")),
            "rgb_lighting": 1 if product.attributes.get("rgb_lighting") == "Evet" else 0,
            "mouse_type": product.attributes.get("mouse_type", ""),
            "button_count": int(product.attributes.get("button_count", 0))
        }
        data.append(product_data)
    return pd.DataFrame(data)

def train_model(df):
    features = ["rating_count", "dpi", "rgb_lighting", "button_count"]
    X = df[features]
    y = df["price"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    print(f"Model R^2 Score: {score}")

    return model

def suggest_product_features(budget, model):
    features = ["rating_count", "dpi", "rgb_lighting", "button_count"]
    feature_ranges = {
        "rating_count": range(0, 1000, 50),
        "dpi": range(100, 16000, 500),
        "rgb_lighting": [0, 1],
        "button_count": range(1, 20)
    }
    
    best_features = None
    min_diff = float('inf')

    for rating_count in feature_ranges["rating_count"]:
        for dpi in feature_ranges["dpi"]:
            for rgb_lighting in feature_ranges["rgb_lighting"]:
                for button_count in feature_ranges["button_count"]:
                    features_values = [rating_count, dpi, rgb_lighting, button_count]
                    predicted_price = model.predict([features_values])[0]
                    diff = abs(budget - predicted_price)
                    if diff < min_diff:
                        min_diff = diff
                        best_features = features_values

    return dict(zip(features, best_features))

def main():
    start_time1 = time.time()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ProductScraper")
    
    client = create_elastic_client()

    create_index_if_not_exists(client, logger)

    products, soup = scrape_web()

    flag_file_path = flagname

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

    products, _ = scrape_web()
    df = collect_data(products)
    print(df.head())

    model = train_model(df)

    budget = 500
    suggested_features = suggest_product_features(budget, model)
    print(f"Suggested features for budget {budget}: {suggested_features}")

if __name__ == "__main__":
    main()
