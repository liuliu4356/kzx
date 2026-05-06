#!/bin/bash
# 离线部署脚本 - 在目标 Linux 服务器上运行（需要先上传此脚本）
# 用法: bash prepare_offline.sh

set -e

OUTPUT_DIR="offline_packages"
mkdir -p "$OUTPUT_DIR/packages"

echo "========================================"
echo "离线部署准备脚本"
echo "========================================"

# 1. 导出已安装的 Docker 镜像
echo "[1/4] 检查并导出 Docker 镜像..."

check_and_save() {
    local img=$1
    if docker images -q "$img" &>/dev/null; then
        echo "  导出: $img"
        docker save -o "$OUTPUT_DIR/${img//\//_}.tar" "$img" 2>/dev/null || true
    else
        echo "  跳过: $img (未安装)"
    fi
}

check_and_save "prom/prometheus:latest"
check_and_save "grafana/grafana:latest"
check_and_save "docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
check_and_save "docker.elastic.co/kibana/kibana:8.11.0"

echo "  Docker 镜像导出完成"

# 2. 下载 Miniconda
echo "[2/4] 下载 Miniconda..."
cd "$OUTPUT_DIR"
if [ ! -f "Miniconda3-py310_23.11.0-2-Linux-x86_64.sh" ]; then
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -O miniconda.sh
fi
cd ..

# 3. 下载 Python 包（需要先联网）
echo "[3/4] 检查 Python 依赖包..."
cd "$OUTPUT_DIR/packages"

# 尝试使用 pip download
pip download -d . \
    httpx==0.24.1 \
    anthropic==0.25.0 \
    jinja2==3.1.2 \
    pyyaml \
    click \
    python-dotenv \
    requests \
    fastapi \
    uvicorn \
    python-multipart \
    2>/dev/null || echo "  注意: 需要联网下载 Python 包"

cd ..

# 4. 生成部署脚本
echo "[4/4] 生成部署脚本..."
cat > "$OUTPUT_DIR/deploy.sh" << 'DEPLOYEOF'
#!/bin/bash
# 离线部署脚本 - 在目标服务器上运行
# 此脚本需要在每台服务器上单独运行

set -e

echo "========================================"
echo "离线部署"
echo "========================================"

# 获取本机IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "本机IP: $LOCAL_IP"

# 根据IP判断部署什么
case "$LOCAL_IP" in
    192.168.187.201)
        echo "=== 部署 Prometheus + Grafana ==="
        
        # 加载镜像
        echo "加载 Docker 镜像..."
        for f in *.tar; do
            [ -f "$f" ] && docker load -i "$f" 2>/dev/null || true
        done
        
        # 启动 Prometheus
        echo "启动 Prometheus..."
        docker rm -f prometheus 2>/dev/null || true
        docker run -d --name prometheus -p 19090:9090 prom/prometheus:latest
        
        # 启动 Grafana
        echo "启动 Grafana..."
        docker rm -f grafana 2>/dev/null || true
        docker run -d --name grafana -p 3000:3000 -e GF_SECURITY_ADMIN_PASSWORD=admin123 grafana/grafana:latest
        
        echo "完成! 访问:"
        echo "  Prometheus: http://$LOCAL_IP:19090"
        echo "  Grafana: http://$LOCAL_IP:3000"
        ;;
        
    192.168.187.202)
        echo "=== 部署 Elasticsearch + Kibana ==="
        
        # 加载镜像
        echo "加载 Docker 镜像..."
        for f in *.tar; do
            [ -f "$f" ] && docker load -i "$f" 2>/dev/null || true
        done
        
        # 启动 Elasticsearch
        echo "启动 Elasticsearch..."
        docker rm -f elasticsearch 2>/dev/null || true
        docker run -d --name elasticsearch -p 9200:9200 \
            -e "discovery.type=single-node" \
            -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
            -e "xpack.security.enabled=false" \
            docker.elastic.co/elasticsearch/elasticsearch:8.11.0
        
        sleep 30
        
        # 启动 Kibana
        echo "启动 Kibana..."
        docker rm -f kibana 2>/dev/null || true
        docker run -d --name kibana -p 5601:5601 \
            -e ELASTICSEARCH_HOSTS=http://$LOCAL_IP:9200 \
            docker.elastic.co/kibana/kibana:8.11.0
        
        echo "完成! 访问:"
        echo "  Elasticsearch: http://$LOCAL_IP:9200"
        echo "  Kibana: http://$LOCAL_IP:5601"
        ;;
        
    192.168.187.203)
        echo "=== 部署 X 项目 ==="
        
        # 安装 Miniconda
        echo "安装 Python..."
        if [ ! -d "/opt/python310" ]; then
            bash Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -b -p /opt/python310
        fi
        
        # 创建项目目录
        mkdir -p /opt/kzx
        cd /opt/kzx
        
        # 需要上传 X 项目代码到 /opt/kzx
        if [ ! -f "requirements.txt" ]; then
            echo "错误: 请先上传 X 项目代码到 /opt/kzx"
            exit 1
        fi
        
        # 创建虚拟环境
        echo "创建虚拟环境..."
        /opt/python310/bin/python -m venv venv
        
        # 安装依赖（离线）
        echo "安装依赖..."
        venv/bin/pip install --no-index --find-links=../packages -r requirements.txt 2>/dev/null || \
        venv/bin/pip install -r requirements.txt 2>/dev/null || true
        
        # 启动服务
        echo "启动服务..."
        nohup venv/bin/python -m src.main web --host 0.0.0.0 --port 8000 > /var/log/kzx.log 2>&1 &
        
        echo "完成! 访问:"
        echo "  X项目: http://$LOCAL_IP:8000"
        ;;
        
    *)
        echo "未知IP，请手动配置"
        ;;
esac
DEPLOYEOF

chmod +x "$OUTPUT_DIR/deploy.sh"

echo ""
echo "========================================"
echo "离线包已生成!"
echo "目录: $OUTPUT_DIR/"
echo "========================================"
echo ""
echo "使用说明:"
echo "1. 将离线包目录传到对应服务器"
echo "2. 在服务器上运行: cd offline_packages && bash deploy.sh"
echo ""