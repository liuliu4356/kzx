#!/usr/bin/env python3
import requests
import json

ES_URL = "http://elasticsearch:9200"

logs = [
    {"level": "ERROR", "message": "Connection refused to database server", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:15:00Z"},
    {"level": "FATAL", "message": "Database node unreachable - cluster partition", "datacenter": "北京南法信", "service": "db", "timestamp": "2026-05-02T08:25:00Z"},
    {"level": "WARN", "message": "High memory usage detected: 85%", "datacenter": "北京东坝", "service": "monitor", "timestamp": "2026-05-02T07:00:00Z"},
    {"level": "WARNING", "message": "Disk space running low on /data - 75% used", "datacenter": "北京南法信", "service": "storage", "timestamp": "2026-05-02T07:30:00Z"},
    {"level": "INFO", "message": "Slow query: SELECT * FROM orders - took 5.2s", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:05:00Z"},
    {"level": "INFO", "message": "Slow Query detected: UPDATE users SET last_login - execution time: 8.3s", "datacenter": "北京南法信", "service": "mysql", "timestamp": "2026-05-02T08:12:00Z"},
    {"level": "ERROR", "message": "Lost connection to MySQL server during query", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:22:00Z"},
    {"level": "ERROR", "message": "Lost connection to database server timeout after 30s", "datacenter": "北京南法信", "service": "db", "timestamp": "2026-05-02T08:28:00Z"},
    {"level": "ERROR", "message": "Lock wait timeout: could not acquire lock on row id=987654", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:08:00Z"},
    {"level": "ERROR", "message": "Lock wait timeout exceeded; try restarting transaction", "datacenter": "北京南法信", "service": "mysql", "timestamp": "2026-05-02T08:16:00Z"},
    {"level": "INFO", "message": "User login successful", "datacenter": "北京东坝", "service": "auth", "timestamp": "2026-05-02T09:00:00Z"},
]

# Create index with mapping
for suffix in [""]:
    idx = f"logstash-{suffix}".strip("-")
    try:
        requests.put(f"{ES_URL}/{idx}", json={
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
        print(f"Created index: {idx}")
    except Exception as e:
        pass

# Bulk insert to logstash-*
bulk_data = ""
for log in logs:
    bulk_data += json.dumps({"index": {"_index": "logstash-2026.05.02"}}) + "\n"
    bulk_data += json.dumps(log) + "\n"

r = requests.post(f"{ES_URL}/_bulk", data=bulk_data.encode(),
                 headers={"Content-Type": "application/x-ndjson"})
result = r.json()
print(f"Added {len(logs)} logs, errors: {result.get('errors', False)}")

# Check counts
for idx in ["logstash-2026.05.02", "logstash-app-2026.05.02"]:
    try:
        r = requests.get(f"{ES_URL}/{idx}/_count")
        print(f"  {idx}: {r.json()['count']}")
    except:
        pass