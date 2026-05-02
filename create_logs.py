#!/usr/bin/env python3
import requests
import json

ES_URL = "http://elasticsearch:9200"
index_name = "logstash-2026.05.02"

# Create index
r = requests.put(f"{ES_URL}/{index_name}", json={
    "settings": {"number_of_shards": 1},
    "mappings": {
        "properties": {
            "level": {"type": "keyword"},
            "message": {"type": "text"},
            "datacenter": {"type": "keyword"},
            "service": {"type": "keyword"},
            "timestamp": {"type": "date"}
        }
    }
})
print(f"Create index: {r.status_code}")

# Add logs
logs = [
    {"level": "ERROR", "message": "Connection refused to database server", "datacenter": "北京东坝"},
    {"level": "FATAL", "message": "Database node unreachable - cluster partition", "datacenter": "北京南法信"},
    {"level": "WARN", "message": "High memory usage detected: 85%", "datacenter": "北京东坝"},
    {"level": "WARNING", "message": "Disk space running low - 75% used", "datacenter": "北京南法信"},
    {"level": "INFO", "message": "Slow query: SELECT * FROM orders - took 5.2s", "datacenter": "北京东坝"},
    {"level": "INFO", "message": "Slow Query detected: UPDATE users - execution time: 8.3s", "datacenter": "北京南法信"},
    {"level": "ERROR", "message": "Lost connection to MySQL server during query", "datacenter": "北京东坝"},
    {"level": "ERROR", "message": "Lost connection to database server timeout after 30s", "datacenter": "北京南法信"},
    {"level": "ERROR", "message": "Lock wait timeout: could not acquire lock on row", "datacenter": "北京东坝"},
    {"level": "ERROR", "message": "Lock wait timeout exceeded; try restarting transaction", "datacenter": "北京南法信"},
]

bulk = ""
for log in logs:
    bulk += json.dumps({"index": {"_index": index_name}}) + "\n"
    bulk += json.dumps(log) + "\n"

r = requests.post(f"{ES_URL}/_bulk", data=bulk.encode(), headers={"Content-Type": "application/x-ndjson"})
result = r.json()
print(f"Bulk insert: {r.status_code}, errors: {result.get('errors', False)}")

# Verify
r = requests.get(f"{ES_URL}/{index_name}/_count")
print(f"Count in {index_name}: {r.json()['count']}")

# Check all logstash indexes
r = requests.get(f"{ES_URL}/_cat/indices/logstash*?h=index,docs.count")
print(f"Logstash indices:\n{r.text}")