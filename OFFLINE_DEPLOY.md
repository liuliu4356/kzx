# 离线部署方案

## 已下载的离线包

| 服务器 | 文件 | 大小 |
|--------|------|------|
| 192.168.187.201 (201) | prom_prometheus_latest.tar | 405MB |
| 192.168.187.201 (201) | grafana_grafana_latest.tar | 1.1GB |
| 192.168.187.202 (202) | elasticsearch_8.11.0.tar | 1.4GB |
| 192.168.187.202 (202) | kibana_8.11.0.tar | 1.1GB |

**总计**: 约 3.8GB

---

## 离线部署步骤

### 服务器 201 - Prometheus + Grafana

```bash
# 1. 上传离线包
scp offline/server_201/*.tar root@192.168.187.201:/tmp/

# 2. SSH登录
ssh root@192.168.187.201

# 3. 加载镜像
cd /tmp
docker load -i prom_prometheus_latest.tar
docker load -i grafana_grafana_latest.tar

# 4. 启动服务
docker run -d --name prometheus -p 19090:9090 prom/prometheus:latest
docker run -d --name grafana -p 3000:3000 -e GF_SECURITY_ADMIN_PASSWORD=admin123 grafana/grafana:latest
```

### 服务器 202 - Elasticsearch + Kibana

```bash
# 1. 上传离线包
scp offline/server_202/*.tar root@192.168.187.202:/tmp/

# 2. SSH登录
ssh root@192.168.187.202

# 3. 加载镜像
cd /tmp
docker load -i elasticsearch_8.11.0.tar
docker load -i kibana_8.11.0.tar

# 4. 启动服务
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# 等待ES启动
sleep 30

docker run -d --name kibana -p 5601:5601 \
  -e ELASTICSEARCH_HOSTS=http://localhost:9200 \
  docker.elastic.co/kibana/kibana:8.11.0
```

### 服务器 203 - X项目

**注意**: 203 服务器的 Python 环境已部署好离线包，本次无需再次部署。

如需重新部署：

```bash
# 1. 上传X项目代码到 /opt/kzx
scp -r X/src X/templates X/config.example.yaml X/requirements.txt X/AGENTS.md root@192.168.187.203:/opt/kzx/

# 2. SSH登录
ssh root@192.168.187.203

# 3. 部署
cd /opt/kzx
bash deploy_offline.sh
```

---

## 服务地址

| 服务 | 地址 |
|------|------|
| Prometheus | http://192.168.187.201:19090 |
| Grafana | http://192.168.187.201:3000 |
| Elasticsearch | http://192.168.187.202:9200 |
| Kibana | http://192.168.187.202:5601 |
| X项目 | http://192.168.187.203:8000 |

---

## 注意事项

1. 离线部署包文件较大，需要用 U 盘或局域网传输
2. Docker 镜像加载后会自动出现在本地镜像列表中
3. 如之前已有同名容器，需先删除: `docker rm -f 容器名`
4. X项目需要上传项目代码后才能离线部署