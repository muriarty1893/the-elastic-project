import logging

def create_logger():
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger("ProductScraper")
