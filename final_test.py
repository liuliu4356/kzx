import requests
import time

print("Waiting 30 seconds for server startup...")
time.sleep(30)

pages = [
    ("/", "Index"),
    ("/sites", "Sites"),
    ("/queries", "Queries"),
    ("/settings", "Settings"),
    ("/reports", "Reports"),
]

print("Testing Web pages on http://localhost:8000")
print("=" * 50)

for path, name in pages:
    try:
        r = requests.get(f"http://localhost:8000{path}", timeout=10)
        if r.status_code == 200:
            print(f"[OK] {name} ({path}): {len(r.text)} bytes")
        else:
            print(f"[WARN] {name} ({path}): HTTP {r.status_code}")
    except Exception as e:
        print(f"[FAIL] {name} ({path}): {str(e)[:80]}")