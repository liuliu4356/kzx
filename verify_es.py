import requests

# Check indexes
r = requests.get('http://elasticsearch:9200/_cat/indices?h=index,docs.count')
print("=== ES Indexes ===")
print(r.text)

# Check log levels
queries = [
    ('level:ERROR', 'ERROR'),
    ('level:WARN OR level:WARNING', 'WARN'),
    ('message:*slow* OR message:*Slow*', 'SLOW'),
    ('message:*Lost connection*', 'CONN_LOST'),
    ('message:*Lock wait timeout*', 'LOCK'),
]

print("\n=== Log Counts ===")
for q, name in queries:
    r = requests.get('http://elasticsearch:9200/logstash-*/_search', json={
        "size": 0,
        "query": {"query_string": {"query": q}}
    })
    count = r.json()['hits']['total']['value']
    print(f"{name}: {count} logs")