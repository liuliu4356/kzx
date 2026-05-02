import requests

queries = [
    "100 - (avg(node_cpu_seconds_total{mode='idle'}) / avg(node_cpu_seconds_total{mode='idle'}) * 100)",
    "avg(node_load1)",
    "min(up)"
]

for q in queries:
    r = requests.get('http://prometheus:9090/api/v1/query', params={'query': q})
    data = r.json()
    results = data.get('data', {}).get('result', [])
    print(f"\n=== {q[:50]}... ===")
    print(f"Results: {len(results)}")
    for res in results:
        v = res.get('value')
        print(f"  Value type: {type(v)}, Value: {v}")