import requests
try:
    r = requests.get('http://mock-metrics:9100/metrics')
    print(f"Status: {r.status_code}")
    print(f"Lines: {len(r.text.splitlines())}")
    print("First 5 lines:")
    for line in r.text.splitlines()[:5]:
        print(f"  {line}")
except Exception as e:
    print(f"Error: {e}")