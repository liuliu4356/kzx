import requests
import time

print("Waiting 20 seconds for server startup...")
time.sleep(20)

pages = [
    ("/", "Index"),
    ("/sites", "Sites"),
]

print("Testing...")
for path, name in pages:
    try:
        r = requests.get(f"http://localhost:8000{path}", timeout=15)
        print(f"{name}: {r.status_code}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")