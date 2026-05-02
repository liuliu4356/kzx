import requests

ES = "http://elasticsearch:9200"

# List indexes
r = requests.get(f"{ES}/_cat/indices?h=index")
print("All indexes:")
print(r.text)

# Check logstash-2026.05.02
r = requests.get(f"{ES}/logstash-2026.05.02/_search", json={"size": 5, "query": {"match_all": {}}})
print("\nSearch logstash-2026.05.02:")
print(f'Hits: {r.json()["hits"]["total"]["value"]}')

# Check logstash-*
r = requests.get(f"{ES}/logstash-*/_search", json={"size": 5, "query": {"match_all": {}}})
print("\nSearch logstash-*:")
print(f'Hits: {r.json()["hits"]["total"]["value"]}')

# Try query_string search
r = requests.get(f"{ES}/logstash-*/_search", json={
    "size": 10,
    "query": {"query_string": {"query": "level:ERROR"}}
})
print("\nSearch level:ERROR:")
print(f'Hits: {r.json()["hits"]["total"]["value"]}')
if r.json()["hits"]["total"]["value"] > 0:
    for hit in r.json()["hits"]["hits"][:3]:
        print(f'  {hit["_source"]}')