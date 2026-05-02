#!/bin/bash

PROM="http://prometheus:9090"

echo "Pushing simulated metrics to Prometheus..."

curl -s -X POST "${PROM}/api/v1/label/values/name=node_cpu_seconds_total" > /dev/null 2>&1

cat > /tmp/metrics.prom << 'EOF'
# HELP node_cpu_seconds_total Seconds in each mode
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{job="dongba-omm",datacenter="北京东坝",role="OMM",mode="idle"} 1500
node_cpu_seconds_total{job="dongba-omm",datacenter="北京东坝",role="OMM",mode="user"} 8000
node_cpu_seconds_total{job="dongba-gtm",datacenter="北京东坝",role="GTM",mode="idle"} 9000
node_cpu_seconds_total{job="nanfaxin-omm",datacenter="北京南法信",role="OMM",mode="idle"} 800
node_cpu_seconds_total{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM",mode="idle"} 9200
node_cpu_seconds_total{job="hefei-omm",datacenter="合肥",role="OMM",mode="idle"} 9800

# HELP node_memory_MemAvailable_bytes Available memory in bytes
# TYPE node_memory_MemAvailable_bytes gauge
node_memory_MemAvailable_bytes{job="dongba-omm",datacenter="北京东坝",role="OMM"} 4000000000
node_memory_MemAvailable_bytes{job="dongba-gtm",datacenter="北京东坝",role="GTM"} 12000000000
node_memory_MemAvailable_bytes{job="nanfaxin-omm",datacenter="北京南法信",role="OMM"} 5120000000
node_memory_MemAvailable_bytes{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM"} 14000000000
node_memory_MemAvailable_bytes{job="hefei-omm",datacenter="合肥",role="OMM"} 14000000000
node_memory_MemTotal_bytes{job="dongba-omm",datacenter="北京东坝",role="OMM"} 16000000000
node_memory_MemTotal_bytes{job="dongba-gtm",datacenter="北京东坝",role="GTM"} 16000000000
node_memory_MemTotal_bytes{job="nanfaxin-omm",datacenter="北京南法信",role="OMM"} 16000000000
node_memory_MemTotal_bytes{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM"} 16000000000
node_memory_MemTotal_bytes{job="hefei-omm",datacenter="合肥",role="OMM"} 16000000000

# HELP node_load1 System load average
# TYPE node_load1 gauge
node_load1{job="dongba-omm",datacenter="北京东坝",role="OMM"} 45
node_load1{job="dongba-gtm",datacenter="北京东坝",role="GTM"} 8
node_load1{job="nanfaxin-omm",datacenter="北京南法信",role="OMM"} 50
node_load1{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM"} 6
node_load1{job="hefei-omm",datacenter="合肥",role="OMM"} 3

# HELP node_filesystem_size_bytes Filesystem size
# TYPE node_filesystem_size_bytes gauge
node_filesystem_size_bytes{job="dongba-omm",datacenter="北京东坝",role="OMM",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="dongba-gtm",datacenter="北京东坝",role="GTM",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="nanfaxin-omm",datacenter="北京南法信",role="OMM",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="hefei-omm",datacenter="合肥",role="OMM",mountpoint="/"} 500000000000

# HELP node_filesystem_avail_bytes Filesystem available bytes
# TYPE node_filesystem_avail_bytes gauge
node_filesystem_avail_bytes{job="dongba-omm",datacenter="北京东坝",role="OMM",mountpoint="/"} 175000000000
node_filesystem_avail_bytes{job="dongba-gtm",datacenter="北京东坝",role="GTM",mountpoint="/"} 350000000000
node_filesystem_avail_bytes{job="nanfaxin-omm",datacenter="北京南法信",role="OMM",mountpoint="/"} 90000000000
node_filesystem_avail_bytes{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM",mountpoint="/"} 400000000000
node_filesystem_avail_bytes{job="hefei-omm",datacenter="合肥",role="OMM",mountpoint="/"} 275000000000

# HELP up Instance up status
# TYPE up gauge
up{job="dongba-omm",datacenter="北京东坝",role="OMM",instance="10.0.0.1:9100"} 1
up{job="dongba-gtm",datacenter="北京东坝",role="GTM",instance="10.0.0.2:9100"} 0
up{job="nanfaxin-omm",datacenter="北京南法信",role="OMM",instance="10.0.0.3:9100"} 1
up{job="nanfaxin-gtm",datacenter="北京南法信",role="GTM",instance="10.0.0.4:9100"} 0
up{job="hefei-omm",datacenter="合肥",role="OMM",instance="10.0.0.5:9100"} 1

# HELP mysql_global_status_threads_connected MySQL connections
# TYPE mysql_global_status_threads_connected gauge
mysql_global_status_threads_connected{job="dongba-db",datacenter="北京东坝",role="DB"} 4500
mysql_global_status_threads_connected{job="nanfaxin-db",datacenter="北京南法信",role="DB"} 7200
mysql_global_status_threads_connected{job="hefei-db",datacenter="合肥",role="DB"} 1200

# HELP mysql_global_status_questions MySQL questions
# TYPE mysql_global_status_questions counter
mysql_global_status_questions{job="dongba-db",datacenter="北京东坝",role="DB"} 1000000
mysql_global_status_questions{job="nanfaxin-db",datacenter="北京南法信",role="DB"} 2500000
mysql_global_status_questions{job="hefei-db",datacenter="合肥",role="DB"} 500000

# HELP elasticsearch_cluster_health_status ES cluster health
# TYPE elasticsearch_cluster_health_status gauge
elasticsearch_cluster_health_status{cluster="es-cluster"} 1
EOF

echo "Metrics written to /tmp/metrics.prom"
echo "Content:"
cat /tmp/metrics.prom