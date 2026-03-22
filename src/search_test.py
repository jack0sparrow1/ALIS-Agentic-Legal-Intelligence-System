from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", os.getenv("ES_PASS"))
)

model = SentenceTransformer("all-MiniLM-L6-v2")

query = "laws related to computer networks"
query_vector = model.encode(query).tolist()

response = es.search(
    index="legal_docs",
    query={
        "script_score": {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": query}},
                        {"match": {"keywords": query}}
                    ]
                }
            },
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": query_vector}
            }
        }
    }
)

for hit in response["hits"]["hits"]:
    print(f"Act: {hit['_source']['act_name']}")
    print(f"Section: {hit['_source']['section_number']}")
    print(f"Title: {hit['_source']['section_title']}")
    print(f"Text: {hit['_source']['text'][:200]}...")
    print(f"Score: {hit['_score']}\n")
