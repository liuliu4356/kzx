import requests
import time

print("Waiting 15 seconds for server to start...")
time.sleep(15)

try:
    resp = requests.post('http://localhost:8000/api/inspect', 
        data={
            'period': 'instant',
            'fmt': 'html', 
            'skip_llm': 'true'
        },
        stream=True,
        timeout=30)

    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        # Read first few lines
        count = 0
        for line in resp.iter_lines():
            if count > 5:
                break
            print(line.decode() if line else '')
            count += 1
    else:
        print(f"Error: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")