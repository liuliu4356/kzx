import requests
import json
import time
from datetime import datetime, timezone

def send_error_log():
    """发送ERROR级别日志到Logstash/Elasticsearch"""
    # 方法1：直接写入Elasticsearch（跳过Logstash）
    es_url = "http://localhost:9200"
    index_name = f"logstash-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"
    
    headers = {"Content-Type": "application/json"}
    
    # 模拟多种ERROR日志
    error_logs = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "message": "数据库连接超时: MySQL server has gone away",
            "service": "mysql-1",
            "host": "hefei-omm1",
            "trace_id": "trace-123456"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "FATAL",
            "message": "Redis连接失败: Connection refused",
            "service": "redis-1",
            "host": "dongba-gtm1",
            "trace_id": "trace-789012"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "message": "API请求超时: /api/inspect 响应时间超过5秒",
            "service": "x-web",
            "host": "nanfaxin-omm1",
            "trace_id": "trace-345678"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "message": "磁盘空间不足: /var/log 使用率95%",
            "service": "node-exporter",
            "host": "hefei-gtm1",
            "trace_id": "trace-901234"
        }
    ]
    
    print(f"向Elasticsearch发送{len(error_logs)}条ERROR/FATAL日志...")
    for log in error_logs:
        try:
            resp = requests.post(
                f"{es_url}/{index_name}/_doc",
                headers=headers,
                data=json.dumps(log),
                timeout=5
            )
            if resp.status_code in (200, 201):
                print(f"  [OK] {log['level']}日志已发送: {log['message'][:30]}...")
            else:
                print(f"  [WARN] 发送失败: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  [FAIL] 发送异常: {str(e)[:50]}")
        time.sleep(0.5)

if __name__ == "__main__":
    send_error_log()
    print("日志发送完成")
