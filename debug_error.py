import requests

try:
    r = requests.get('http://localhost:8000/', timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 500:
        print(f"Body: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")