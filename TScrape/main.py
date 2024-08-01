import os
import time
from config.logger import create_logger
from elastic.indexer import Indexer
from elastic.search import Searcher
from scraping.scraper import Scraper

def main():
    start_time1 = time.time()
    
    logger = create_logger()
    
    indexname = "indext31"
    flagname = "flags/indexing_done_81.flag"
    
    indexer = Indexer(indexname)
    scraper = Scraper()
    searcher = Searcher(indexname)
    
    indexer.create_index_if_not_exists(logger)

    products, soup = scraper.scrape_web()

    flag_file_path = flagname

    if not os.path.exists(flag_file_path):
        indexer.index_products(products, logger)
        os.makedirs(os.path.dirname(flag_file_path), exist_ok=True)

        with open(flag_file_path, 'w') as flag_file:
            flag_file.write('')

    item = "steelseries"
    if os.path.exists(flag_file_path):
        start_time2 = time.time()
        searcher.search_products(indexer.client, item, logger)
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
