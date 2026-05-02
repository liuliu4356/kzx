import requests

metrics = ['up', 'node_load1', 'mysql_global_status_threads_connected', 'elasticsearch_cluster_health_status']
for m in metrics:
    r = requests.get('http://prometheus:9090/api/v1/query', params={'query': m})
    data = r.json()
    results = data.get('data', {}).get('result', [])
    print(f'{m}: {len(results)} results')
    if results:
        for res in results[:2]:
            val = res.get('value', [None, None])[1]
            print(f'  -> {val}')