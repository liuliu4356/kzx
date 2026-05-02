import requests

# Test the inspect API
resp = requests.post('http://localhost:8000/api/inspect', 
    data={
        'period': 'instant',
        'fmt': 'html', 
        'skip_llm': 'true'
    },
    stream=True)

print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type')}")

# Read first few lines
count = 0
for line in resp.iter_lines():
    if count > 10:
        break
    print(line.decode()[:200] if line else '')
    count += 1