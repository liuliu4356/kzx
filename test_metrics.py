import requests
import json

prom_url = "http://prometheus:9090/api/v1/query"

queries = ["up", "node_cpu_seconds_total", "node_memory_MemAvailable_bytes", "node_load1"]

for q in queries:
    r = requests.get(prom_url, params={"query": q})
    data = r.json()
    print(f"\n=== {q} ===")
    if data.get("status") == "success":
        results = data.get("data", {}).get("result", [])
        print(f"Found {len(results)} metrics")
        for res in results[:3]:
            print(f"  {res.get('metric', {})}: {res.get('value', [None, None])[1]}")
    else:
        print(f"Error: {data}")