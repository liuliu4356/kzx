#!/usr/bin/env python3
"""模拟 3 台服务器的日志生成器 - 包含错误类型"""

import random
import time
import requests
from datetime import datetime

SERVERS = [
    {"name": "node-1", "role": "web-server"},
    {"name": "node-2", "role": "api-server"},
    {"name": "node-3", "role": "database-server"},
]

ERROR_TYPES = {
    "connection": [
        "Connection refused to database server",
        "Failed to connect to Redis: timeout after 30s",
        "MySQL connection lost, reconnecting...",
        "API gateway unreachable: 504 Gateway Timeout",
        "Failed to connect to external API: SSL handshake failed",
        "MongoDB connection pool exhausted",
        "RabbitMQ connection error: broker not reachable",
        "LDAP server connection failed",
    ],
    "restart": [
        "Service restart initiated by system",
        "Process crashed, restarting automatically",
        "Docker container restarted due to OOM",
        "System reboot scheduled for maintenance",
        "Application restart required: configuration changed",
        "Service failed health check, restarting...",
        "Pod restarted in Kubernetes cluster",
        "System service unexpected termination, restarting",
    ],
    "memory": [
        "Memory usage exceeded 95%, triggering alert",
        "Out of memory: killed process java (PID: 12345)",
        "Memory leak detected in application module",
        "Swap space exhausted, system performance degraded",
        "OOM killer activated, terminating processes",
        "Memory allocation failed: insufficient resources",
        "High memory pressure: reducing cache size",
        "JVM heap size at maximum capacity",
    ],
    "disk": [
        "Disk space critical: only 5% remaining",
        "Disk write failed: no space left on device",
        "Mount point /data unavailable",
        "RAID array degraded, rebuild required",
        "Filesystem read-only, remount needed",
    ],
    "cpu": [
        "CPU usage at 100% for sustained period",
        "Process taking 100% CPU, possible infinite loop",
        "High CPU load: system may become unresponsive",
    ],
}

def send_log(server, level, message):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "server": server["name"],
        "role": server["role"],
    }
    try:
        resp = requests.post(
            "http://localhost:8080",
            json=log_entry,
            timeout=5
        )
        return resp.status_code == 200
    except Exception:
        return False

def main():
    print("=" * 60)
    print("开始生成测试日志 - 包含错误类型")
    print("=" * 60)
    print("发送到: http://localhost:8080")
    print("日志将存储到 Elasticsearch")
    print("-" * 60)
    
    error_weights = [
        ("connection", 0.15),
        ("restart", 0.10),
        ("memory", 0.20),
        ("disk", 0.08),
        ("cpu", 0.07),
    ]
    
    while True:
        server = random.choice(SERVERS)
        
        roll = random.random()
        
        if roll < 0.40:
            level = "ERROR"
            error_type = random.choices(
                [e[0] for e in error_weights],
                weights=[e[1] for e in error_weights]
            )[0]
            message = random.choice(ERROR_TYPES[error_type])
        elif roll < 0.60:
            level = "WARNING"
            message = random.choice([
                "High resource usage detected",
                "Service response time degraded",
                "Connection pool near capacity",
                "Certificate expires in 7 days",
                "Disk usage above 80%",
            ])
        elif roll < 0.85:
            level = "INFO"
            message = random.choice([
                "Request processed successfully",
                "Database connection established",
                "Cache hit for key: session_data",
                "Health check passed",
                "Backup completed",
                "User login successful",
            ])
        else:
            level = "DEBUG"
            message = random.choice([
                "Processing request ID: " + str(random.randint(10000, 99999)),
                "Cache refresh completed",
                "Metrics collected successfully",
                "Queue message processed",
            ])
        
        success = send_log(server, level, message)
        status = "✓" if success else "✗"
        
        print(f"[{status}] {server['name']:8} {level:8} {message[:50]}")
        
        if level == "ERROR":
            time.sleep(random.uniform(2, 5))
        else:
            time.sleep(random.uniform(3, 10))

if __name__ == "__main__":
    main()