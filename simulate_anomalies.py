#!/usr/bin/env python3
import time
import requests
import random

PROMETHEUS = "http://prometheus:9090"
PUSHGW = "http://prometheus:9091"

job_labels = [
    {"job": "dongba-omm", "datacenter": "北京东坝", "instance": "node-exporter-1:9100", "role": "OMM", "ip": "25.131.185.181"},
    {"job": "dongba-gtm", "datacenter": "北京东坝", "instance": "node-exporter-3:9100", "role": "GTM", "ip": "25.131.185.183"},
    {"job": "nanfaxin-omm", "datacenter": "北京南法信", "instance": "node-exporter-5:9100", "role": "OMM", "ip": "26.131.185.181"},
    {"job": "nanfaxin-gtm", "datacenter": "北京南法信", "instance": "node-exporter-6:9100", "role": "GTM", "ip": "26.131.185.183"},
    {"job": "hefei-omm", "datacenter": "合肥", "instance": "node-exporter-8:9100", "role": "OMM", "ip": "27.130.52.141"},
]

anomalies = {
    "北京东坝-OMM": {"cpu": 85, "memory": 75, "disk": 65, "load": 45},
    "北京南法信-OMM": {"cpu": 92, "memory": 68, "disk": 82, "load": 50},
    "合肥-OMM": {"cpu": 5, "memory": 55, "disk": 45, "load": 3},
}

def push_metrics():
    metrics = []
    for labels in job_labels:
        key = f"{labels['datacenter']}-{labels['role']}"
        if key in anomalies:
            a = anomalies[key]
            cpu_idle = 100 - a["cpu"]
            mem_available = int((100 - a["memory"]) / 100 * 16000000000)
            load = a["load"]
            disk_used = a["disk"]
            down = 0
        else:
            cpu_idle = random.randint(92, 98)
            mem_available = random.randint(12000000000, 15000000000)
            load = random.randint(1, 8)
            disk_used = random.randint(30, 60)
            down = 1

        base = f'{{job="{labels["job"]}",datacenter="{labels["datacenter"]}",instance="{labels["instance"]}",ip="{labels["ip"]}",role="{labels["role"]}"}}'
        
        metrics.append(f"node_cpu_seconds_total{mode=\"idle\"} {cpu_idle * 1000}")
        metrics.append(f"node_cpu_seconds_total{mode=\"user\"} {random.randint(100, 500)}")
        metrics.append(f"node_memory_MemTotal_bytes 16000000000")
        metrics.append(f"node_memory_MemAvailable_bytes {mem_available}")
        metrics.append(f"node_load1 {load}")
        metrics.append(f"node_load5 {load * 0.8}")
        metrics.append(f"node_load15 {load * 0.6}")
        metrics.append(f"node_filesystem_size_bytes{{mountpoint=\"/\"}} 500000000000")
        metrics.append(f"node_filesystem_avail_bytes{{mountpoint=\"/\"}} {int(500000000000 * (100 - disk_used) / 100)}")
        metrics.append(f"up {down}")
        
    body = f"# HELP node_cpu_seconds_total CPU time\n# TYPE node_cpu_seconds_total counter\n" + "\n".join([f"node_cpu_seconds_total{m} {v}" for m, v in [(f'{l["job"]}",datacenter="{l["datacenter"]}",instance="{l["instance"]}",ip="{l["ip"]}",role="{l["role"]}",mode="idle"', random.randint(92000, 98000)) for l in job_labels]])
    
    payload = {
        "groups": [{
            "name": "simulated",
            "interval": "30s",
            "labels": {"job": "simulator"},
            "files": [{
                "path": "/tmp/metrics.prom",
                "content": "\n".join([
                    "# HELP node_cpu_seconds_total Seconds spent in each mode",
                    "# TYPE node_cpu_seconds_total counter",
                ] + [f'node_cpu_seconds_total{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}",mode="idle"}} {random.randint(92000,98000)}' for l in job_labels] + [
                    "# HELP node_memory_MemAvailable_bytes Available memory",
                    "# TYPE node_memory_MemAvailable_bytes gauge",
                ] + [f'node_memory_MemAvailable_bytes{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}}} {random.randint(4000000000,14000000000)}' for l in job_labels] + [
                    "# HELP node_load1 System load",
                    "# TYPE node_load1 gauge",
                ] + [f'node_load1{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}}} {random.randint(1,50)}' for l in job_labels])
            }]
        }]
    }
    
    r = requests.post(f"{PROMETHEUS}/api/v1/admin/tsdb/snapshot", json={})
    print(f"Snapshot: {r.status_code}")
    
    for i in range(5):
        try:
            requests.post(f"{PUSHGW}/metrics/job/simulator", data="\n".join([
                f'node_cpu_seconds_total{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}",mode="idle"}} {random.randint(92000,98000)}',
                f'node_memory_MemAvailable_bytes{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}}} {random.randint(4000000000,14000000000)}',
                f'node_load1{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}}} {random.randint(1,50)}',
                f'up{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}}} {random.choice([0,1])}',
            ] for l in job_labels).encode())
            print(f"Pushed batch {i+1}")
        except Exception as e:
            print(f"Push error: {e}")
        time.sleep(1)

def write_to_file():
    lines = []
    labels = [
        {"job": "dongba-omm", "datacenter": "北京东坝", "role": "OMM"},
        {"job": "dongba-gtm", "datacenter": "北京东坝", "role": "GTM"},
        {"job": "nanfaxin-omm", "datacenter": "北京南法信", "role": "OMM"},
        {"job": "nanfaxin-gtm", "datacenter": "北京南法信", "role": "GTM"},
        {"job": "hefei-omm", "datacenter": "合肥", "role": "OMM"},
    ]
    
    for l in labels:
        label_str = f'{{job="{l["job"]}",datacenter="{l["datacenter"]}",role="{l["role"]}"}}'
        
        key = f"{l['datacenter']}-{l['role']}"
        if key in anomalies:
            a = anomalies[key]
            cpu_idle = 100 - a["cpu"]
            mem_avail = int((100 - a["memory"]) / 100 * 16000000000)
            load = a["load"]
            disk_avail = int((100 - a["disk"]) / 100 * 500000000000)
            up_val = 0
        else:
            cpu_idle = random.randint(92, 98)
            mem_avail = random.randint(12000000000, 15000000000)
            load = random.randint(1, 8)
            disk_avail = random.randint(200000000000, 350000000000)
            up_val = 1
        
        lines.append(f"node_cpu_seconds_total{label_str}{{mode="idle"}} {cpu_idle * 100}")
        lines.append(f"node_cpu_seconds_total{label_str}{{mode="user"}} {random.randint(100,500)}")
        lines.append(f"node_memory_MemTotal_bytes{label_str} 16000000000")
        lines.append(f"node_memory_MemAvailable_bytes{label_str} {mem_avail}")
        lines.append(f"node_load1{label_str} {load}")
        lines.append(f"node_load5{label_str} {load * 0.8}")
        lines.append(f"node_load15{label_str} {load * 0.6}")
        lines.append(f'node_filesystem_size_bytes{label_str}{{mountpoint="/"}} 500000000000')
        lines.append(f'node_filesystem_avail_bytes{label_str}{{mountpoint="/"}} {disk_avail}')
        lines.append(f"up{label_str} {up_val}")
    
    with open("/tmp/test_metrics.prom", "w") as f:
        f.write("\n".join(lines))
    print("Written to /tmp/test_metrics.prom")
    return lines

if __name__ == "__main__":
    print("Generating simulated metrics...")
    lines = write_to_file()
    print(f"Generated {len(lines)} metrics")
    print("\nSample metrics:")
    for line in lines[:5]:
        print(f"  {line}")