import requests

r = requests.get('http://prometheus:9090/api/v1/query', params={'query': "0"})
data = r.json()
results = data.get('data', {}).get('result', [])
print(f"Total results: {len(results)}")
for i, res in enumerate(results):
    print(f"\nResult {i}:")
    print(f"  Type: {type(res)}")
    print(f"  Content: {res}")