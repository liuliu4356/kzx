import requests

queries = [
    {"name": "cpu_usage", "promql": "0"},
    {"name": "memory_usage", "promql": "0"},
    {"name": "system_load", "promql": "avg(node_load1)"},
    {"name": "disk_usage_root", "promql": "0"},
    {"name": "network_traffic", "promql": "0"},
    {"name": "mysql_connections", "promql": "max(mysql_global_status_threads_connected)"},
    {"name": "mysql_qps", "promql": "0"},
    {"name": "mysql_tps", "promql": "0"},
    {"name": "disk_usage_percent", "promql": "0"},
    {"name": "instance_up", "promql": "min(up)"},
    {"name": "elasticsearch_cluster_health", "promql": "elasticsearch_cluster_health_status"},
]

for q in queries:
    try:
        r = requests.get('http://prometheus:9090/api/v1/query', params={'query': q["promql"]})
        data = r.json()
        results = data.get('data', {}).get('result', [])
        print(f"{q['name']}: {len(results)} results")
        for res in results[:1]:
            v = res.get('value')
            print(f"  value type: {type(v)}, v: {v}")
    except Exception as e:
        print(f"{q['name']}: ERROR - {e}")