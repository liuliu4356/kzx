from http.server import HTTPServer, BaseHTTPRequestHandler

METRICS = """# HELP node_cpu_seconds_total Seconds in each mode
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{job="mock-anomaly",datacenter="beijing-dongba",role="OMM",mode="idle"} 100000
node_cpu_seconds_total{job="mock-anomaly",datacenter="beijing-dongba",role="GTM",mode="idle"} 90000
node_cpu_seconds_total{job="mock-anomaly",datacenter="beijing-nanfaxin",role="OMM",mode="idle"} 80000
node_cpu_seconds_total{job="mock-anomaly",datacenter="beijing-nanfaxin",role="GTM",mode="idle"} 92000
node_cpu_seconds_total{job="mock-anomaly",datacenter="hefei",role="OMM",mode="idle"} 98000

# HELP node_memory_MemAvailable_bytes Available memory in bytes
# TYPE node_memory_MemAvailable_bytes gauge
node_memory_MemAvailable_bytes{job="mock-anomaly",datacenter="beijing-dongba",role="OMM"} 4000000000
node_memory_MemAvailable_bytes{job="mock-anomaly",datacenter="beijing-dongba",role="GTM"} 12000000000
node_memory_MemAvailable_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",role="OMM"} 5120000000
node_memory_MemAvailable_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",role="GTM"} 14000000000
node_memory_MemAvailable_bytes{job="mock-anomaly",datacenter="hefei",role="OMM"} 14000000000

# HELP node_memory_MemTotal_bytes Total memory
# TYPE node_memory_MemTotal_bytes gauge
node_memory_MemTotal_bytes{job="mock-anomaly",datacenter="beijing-dongba",role="OMM"} 16000000000
node_memory_MemTotal_bytes{job="mock-anomaly",datacenter="beijing-dongba",role="GTM"} 16000000000
node_memory_MemTotal_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",role="OMM"} 16000000000
node_memory_MemTotal_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",role="GTM"} 16000000000
node_memory_MemTotal_bytes{job="mock-anomaly",datacenter="hefei",role="OMM"} 16000000000

# HELP node_load1 System load average
# TYPE node_load1 gauge
node_load1{job="mock-anomaly",datacenter="beijing-dongba",role="OMM"} 45
node_load1{job="mock-anomaly",datacenter="beijing-dongba",role="GTM"} 8
node_load1{job="mock-anomaly",datacenter="beijing-nanfaxin",role="OMM"} 50
node_load1{job="mock-anomaly",datacenter="beijing-nanfaxin",role="GTM"} 6
node_load1{job="mock-anomaly",datacenter="hefei",role="OMM"} 3

# HELP node_filesystem_size_bytes Filesystem size
# TYPE node_filesystem_size_bytes gauge
node_filesystem_size_bytes{job="mock-anomaly",datacenter="beijing-dongba",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="mock-anomaly",datacenter="beijing-dongba",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",mountpoint="/"} 500000000000
node_filesystem_size_bytes{job="mock-anomaly",datacenter="hefei",mountpoint="/"} 500000000000

# HELP node_filesystem_avail_bytes Filesystem available
# TYPE node_filesystem_avail_bytes gauge
node_filesystem_avail_bytes{job="mock-anomaly",datacenter="beijing-dongba",mountpoint="/"} 175000000000
node_filesystem_avail_bytes{job="mock-anomaly",datacenter="beijing-dongba",mountpoint="/"} 350000000000
node_filesystem_avail_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",mountpoint="/"} 90000000000
node_filesystem_avail_bytes{job="mock-anomaly",datacenter="beijing-nanfaxin",mountpoint="/"} 400000000000
node_filesystem_avail_bytes{job="mock-anomaly",datacenter="hefei",mountpoint="/"} 275000000000

# HELP up Instance up status
# TYPE up gauge
up{job="mock-anomaly",datacenter="beijing-dongba",role="OMM"} 1
up{job="mock-anomaly",datacenter="beijing-dongba",role="GTM"} 0
up{job="mock-anomaly",datacenter="beijing-nanfaxin",role="OMM"} 1
up{job="mock-anomaly",datacenter="beijing-nanfaxin",role="GTM"} 0
up{job="mock-anomaly",datacenter="hefei",role="OMM"} 1

# HELP mysql_global_status_threads_connected MySQL connections
# TYPE mysql_global_status_threads_connected gauge
mysql_global_status_threads_connected{job="mock-anomaly",datacenter="beijing-dongba",role="DB"} 4500
mysql_global_status_threads_connected{job="mock-anomaly",datacenter="beijing-nanfaxin",role="DB"} 7200
mysql_global_status_threads_connected{job="mock-anomaly",datacenter="hefei",role="DB"} 1200

# HELP mysql_global_status_questions MySQL questions
# TYPE mysql_global_status_questions counter
mysql_global_status_questions{job="mock-anomaly",datacenter="beijing-dongba",role="DB"} 1000000
mysql_global_status_questions{job="mock-anomaly",datacenter="beijing-nanfaxin",role="DB"} 2500000
mysql_global_status_questions{job="mock-anomaly",datacenter="hefei",role="DB"} 500000

# HELP elasticsearch_cluster_health_status ES cluster health
# TYPE elasticsearch_cluster_health_status gauge
elasticsearch_cluster_health_status{cluster="es-cluster"} 1
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(METRICS.encode())

HTTPServer(("0.0.0.0", 9100), Handler).serve_forever()