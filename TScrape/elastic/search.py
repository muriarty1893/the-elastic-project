class Searcher:
    def __init__(self, indexname):
        self.indexname = indexname

    def search_products(self, client, search_text, logger):
        search_response = client.search(
            index=self.indexname,
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
