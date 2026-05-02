import requests
import sys

queries = [
    "node_load1",
    "node_memory_MemAvailable_bytes",
    "up",
    "node_cpu_seconds_total"
]

for q in queries:
    try:
        r = requests.get('http://prometheus:9090/api/v1/query', params={'query': q})
        data = r.json()
        if data.get('status') == 'success':
            results = data.get('data', {}).get('result', [])
            print(f"{q}: {len(results)} metrics")
            for res in results[:2]:
                labels = res.get('metric', {})
                val = res.get('value', [None, None])[1]
                print(f"  {labels.get('job', 'unknown')}: {val}")
        else:
            print(f"{q}: ERROR - {data}")
    except Exception as e:
        print(f"{q}: Exception - {e}")