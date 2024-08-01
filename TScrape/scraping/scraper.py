import requests
from bs4 import BeautifulSoup
from .product import Product

class Scraper:
    def scrape_web(self):
        url = "https://www.trendyol.com/sr/oyuncu-mouselari-x-c106088?sst=BEST_SELLER"
        response = requests.get(url)
        products = []

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            product_nodes = soup.select('div.p-card-chldrn-cntnr.card-border')

            for node in product_nodes:
                product_name = self.extract_product_name(node)
                price = self.extract_price(node)
                rating_count = self.extract_rating_count(node)
                product_link = self.extract_product_link(node)
                attributes = self.scrape_product_details(product_link) if product_link else {}

                product = Product(
                    product_name=product_name,
                    prices=[price] if price else [],
                    rating_count=rating_count,
                    attributes=attributes
                )
                products.append(product)

            return products, soup

        return products, None

    def scrape_product_details(self, url):
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

    def extract_product_name(self, node):
        product_name_node = node.select_one("h3.prdct-desc-cntnr-ttl-w")
        return (
            " ".join([
                product_name_node.select_one("span.prdct-desc-cntnr-ttl").get_text().strip() if product_name_node.select_one("span.prdct-desc-cntnr-ttl") else "",
                product_name_node.select_one("span.prdct-desc-cntnr-name").get_text().strip() if product_name_node.select_one("span.prdct-desc-cntnr-name") else "",
                product_name_node.select_one("div.product-desc-sub-text").get_text().strip() if product_name_node.select_one("div.product-desc-sub-text") else ""
            ])
            if product_name_node else None
        )

    def extract_price(self, node):
        price_node = node.select_one("div.prc-box-dscntd")
        price = price_node.get_text().strip() if price_node else None
        if price:
            return float(price.replace("TL", "").replace(",", "").replace(".", ""))
        return None

    def extract_rating_count(self, node):
        rating_count_node = node.select_one("span.ratingCount")
        return rating_count_node.get_text().strip() if rating_count_node else None

    def extract_product_link(self, node):
        product_link_node = node.select_one("a")
        return f"https://www.trendyol.com{product_link_node['href']}" if product_link_node else None
