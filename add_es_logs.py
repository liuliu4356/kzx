#!/usr/bin/env python3
import requests
import json
import random
from datetime import datetime

ES_URL = "http://elasticsearch:9200"
INDEXES = ["logstash-app-2026.05.02", "logstash-2026.05.02"]

logs = [
    # ERROR/FATAL logs
    {"level": "ERROR", "message": "Connection refused to database server 25.131.185.101", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:15:00Z"},
    {"level": "ERROR", "message": "OutOfMemoryError: Java heap space exhausted", "datacenter": "北京东坝", "service": "jvm", "timestamp": "2026-05-02T08:20:00Z"},
    {"level": "FATAL", "message": "Database node 26.131.185.145 unreachable - cluster partition", "datacenter": "北京南法信", "service": "db", "timestamp": "2026-05-02T08:25:00Z"},
    {"level": "ERROR", "message": "Authentication failed for user admin@localhost", "datacenter": "北京东坝", "service": "auth", "timestamp": "2026-05-02T08:30:00Z"},

    # WARN/WARNING logs
    {"level": "WARN", "message": "High memory usage detected: 85%", "datacenter": "北京东坝", "service": "monitor", "timestamp": "2026-05-02T07:00:00Z"},
    {"level": "WARNING", "message": "Disk space running low on /data - 75% used", "datacenter": "北京南法信", "service": "storage", "timestamp": "2026-05-02T07:30:00Z"},
    {"level": "WARN", "message": "Connection pool exhausted, waiting for available connection", "datacenter": "北京东坝", "service": "dbproxy", "timestamp": "2026-05-02T08:00:00Z"},
    {"level": "WARNING", "message": "SSL certificate expires in 7 days", "datacenter": "合肥", "service": "security", "timestamp": "2026-05-02T08:10:00Z"},
    {"level": "WARN", "message": "Slow response from upstream server (500ms)", "datacenter": "北京南法信", "service": "nginx", "timestamp": "2026-05-02T08:15:00Z"},

    # Slow query logs
    {"level": "INFO", "message": "Slow query: SELECT * FROM orders WHERE status='pending' - took 5.2s", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:05:00Z"},
    {"level": "INFO", "message": "Slow Query detected: UPDATE users SET last_login=NOW() WHERE id>10000 - execution time: 8.3s", "datacenter": "北京南法信", "service": "mysql", "timestamp": "2026-05-02T08:12:00Z"},
    {"level": "INFO", "message": "Slow query: JOIN orders_items ON orders.id = order_items.order_id - took 12.5s", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:18:00Z"},

    # Connection lost logs
    {"level": "ERROR", "message": "Lost connection to MySQL server during query", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:22:00Z"},
    {"level": "ERROR", "message": "Lost connection to database server 25.131.185.120:3306 - timeout after 30s", "datacenter": "北京南法信", "service": "db", "timestamp": "2026-05-02T08:28:00Z"},

    # Lock wait timeout logs
    {"level": "ERROR", "message": "Lock wait timeout: could not acquire lock on row id=987654 in table orders", "datacenter": "北京东坝", "service": "mysql", "timestamp": "2026-05-02T08:08:00Z"},
    {"level": "ERROR", "message": "Lock wait timeout exceeded; try restarting transaction - table: users, index: PRIMARY", "datacenter": "北京南法信", "service": "mysql", "timestamp": "2026-05-02T08:16:00Z"},

    # Normal info logs (should pass)
    {"level": "INFO", "message": "User login successful: user@example.com", "datacenter": "北京东坝", "service": "auth", "timestamp": "2026-05-02T09:00:00Z"},
    {"level": "INFO", "message": "Backup completed successfully - 2.3GB archived", "datacenter": "合肥", "service": "backup", "timestamp": "2026-05-02T09:10:00Z"},
]

# Create index if not exists
try:
    requests.put(f"{ES_URL}/{INDEX}", json={"mappings": {
        "properties": {
            "level": {"type": "keyword"},
            "message": {"type": "text"},
            "datacenter": {"type": "keyword"},
            "service": {"type": "keyword"},
            "timestamp": {"type": "date"}
        }
    }})
    print(f"Index {INDEX} created or exists")
except Exception as e:
    print(f"Index creation: {e}")

# Bulk insert logs - need newline separated JSON
bulk_data = ""
for log in logs:
    bulk_data += json.dumps({"index": {"_index": INDEX}}) + "\n"
    bulk_data += json.dumps(log) + "\n"

if bulk_data:
    r = requests.post(f"{ES_URL}/_bulk", data=bulk_data.encode(),
                     headers={"Content-Type": "application/x-ndjson"})
    print(f"Bulk insert: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        print(f"Added {len(logs)} logs, errors: {result.get('errors', False)}")
    else:
        print(f"Error: {r.text[:200]}")

# Verify
for idx in INDEXES:
    try:
        r = requests.get(f"{ES_URL}/{idx}/_count")
        print(f"Total docs in {idx}: {r.json()['count']}")
    except:
        pass