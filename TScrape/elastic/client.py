from elasticsearch import Elasticsearch

def create_elastic_client():
    return Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])
