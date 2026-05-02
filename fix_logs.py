#!/usr/bin/env python3
import requests
import json

ES_URL = "http://elasticsearch:9200"

logs = [
    {"@timestamp": "2026-05-02T08:15:00Z", "level": "ERROR", "message": "Connection refused to database server", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T08:20:00Z", "level": "FATAL", "message": "Database node unreachable - cluster partition", "datacenter": "北京南法信"},
    {"@timestamp": "2026-05-02T07:00:00Z", "level": "WARN", "message": "High memory usage detected: 85%", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T07:30:00Z", "level": "WARNING", "message": "Disk space running low - 75% used", "datacenter": "北京南法信"},
    {"@timestamp": "2026-05-02T08:05:00Z", "level": "INFO", "message": "Slow query: SELECT * FROM orders - took 5.2s", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T08:12:00Z", "level": "INFO", "message": "Slow Query detected: UPDATE users - execution time: 8.3s", "datacenter": "北京南法信"},
    {"@timestamp": "2026-05-02T08:22:00Z", "level": "ERROR", "message": "Lost connection to MySQL server during query", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T08:28:00Z", "level": "ERROR", "message": "Lost connection to database server timeout after 30s", "datacenter": "北京南法信"},
    {"@timestamp": "2026-05-02T08:08:00Z", "level": "ERROR", "message": "Lock wait timeout: could not acquire lock on row", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T08:16:00Z", "level": "ERROR", "message": "Lock wait timeout exceeded; try restarting transaction", "datacenter": "北京南法信"},
    {"@timestamp": "2026-05-02T09:00:00Z", "level": "INFO", "message": "User login successful", "datacenter": "北京东坝"},
    {"@timestamp": "2026-05-02T08:15:00Z", "level": "ERROR", "message": "packets out of order detected from client 25.131.185.101", "datacenter": "北京东坝"},
]

bulk = ""
for log in logs:
    bulk += json.dumps({"index": {"_index": "logstash-2026.05.02"}}) + "\n"
    bulk += json.dumps(log) + "\n"

r = requests.post(f"{ES_URL}/_bulk", data=bulk.encode(), headers={"Content-Type": "application/x-ndjson"})
result = r.json()
print(f"Bulk insert: {r.status_code}, errors: {result.get('errors', False)}")

# Verify
r = requests.get(f"{ES_URL}/logstash-2026.05.02/_count")
print(f"Count in logstash-2026.05.02: {r.json()['count']}")

# Test query
r = requests.get(f"{ES_URL}/logstash-*/_search", json={
    "size": 5,
    "query": {"query_string": {"query": "level:ERROR"}}
})
print(f"ERROR logs: {r.json()['hits']['total']['value']}")