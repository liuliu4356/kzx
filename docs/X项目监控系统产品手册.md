# X项目监控系统 产品手册

**版本：** v1.2.0
**日期：** 2026年5月
**作者：** X项目开发组

---

## 前言

本手册系统性地介绍X项目监控系统的功能、安装、配置、使用和维护方法。本手册适用于运维工程师、系统管理员、开发人员以及项目决策者。

---

# 第一篇 基础篇

## 第1章 产品概述

### 1.1 产品定位

X项目是一套**自动化运维巡检系统**，专为多机房（数据中心）环境设计，提供全面的服务器、应用和日志监控能力。

### 1.2 核心功能

- ✅ **指标采集** - 自动采集CPU、内存、磁盘、网络等服务器指标
- ✅ **日志分析** - 自动采集和分析Elasticsearch日志
- ✅ **异常检测** - 基于阈值的智能异常判断
- ✅ **报告生成** - 自动生成Markdown/HTML巡检报告
- ✅ **Web管理** - 可视化Web界面，支持一键巡检
- ✅ **AI分析** - 支持Claude AI智能分析（可选）
- ✅ **多机房支持** - 支持北京东坝、北京南法信、合肥三个机房

### 1.3 技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          X 巡检系统                                   │
├─────────────────────────────────────────────────────────────────────┤
│  应用层                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Web界面   │  │  CLI命令行  │  │  报告生成   │  │   AI分析    │ │
│  │  (FastAPI)  │  │   (Click)   │  │  (Markdown) │  │ (Claude)   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  数据采集层                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Prometheus │  │Elasticsearch│  │   定时任务  │                │
│  │  指标采集    │  │  日志采集   │  │  自动执行   │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
├─────────────────────────────────────────────────────────────────────┤
│  存储层                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Prometheus │  │Elasticsearch│  │   Grafana   │                │
│  │  时序数据库 │  │  搜索引擎   │  │   可视化    │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 支持的机房

| 机房名称 | 代码 | VIP | 用途 |
|----------|------|-----|------|
| 北京东坝 | dongba | 25.131.185.100 | 主机房 |
| 北京南法信 | nanfaxin | 26.131.185.100 | 主机房 |
| 合肥 | hefei | 27.130.52.100 | 灾备机房 |

---

## 第2章 环境要求

### 2.1 硬件要求

| 组件 | CPU | 内存 | 磁盘 | 网络 |
|------|-----|------|------|------|
| Prometheus | 2核 | 4GB | 50GB | 100Mbps |
| Elasticsearch | 2核 | 4GB | 100GB | 100Mbps |
| Grafana | 1核 | 1GB | 10GB | 100Mbps |
| 巡检程序 | 1核 | 1GB | 10GB | 100Mbps |

### 2.2 软件依赖

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Docker | 20.10+ | 容器编排 |
| Docker Compose | 2.0+ | 容器编排 |
| Python | 3.10+ | 运行巡检程序 |

### 2.3 支持的操作系统

- ✅ Ubuntu 20.04+
- ✅ CentOS 7+
- ✅ 麒麟V10（鲲鹏/飞腾）
- ✅ Windows Server 2019+
- ✅ Windows 10/11 (开发测试)

---

# 第二篇 安装篇

## 第3章 测试环境安装

### 3.1 一键启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/liuliu4356/kzx.git
cd kzx

# 2. 一键启动所有服务
docker-compose up -d

# 3. 检查服务状态
docker-compose ps
```

**预期输出：**
```
     Name                    Command               State    Ports
---------------------------------------------------------------------------
prometheus          /bin/prometheus --config ...   Up      9090/tcp
elasticsearch       /usr/local/bin/docker-ent ...   Up      9200/tcp
grafana            /run.sh                         Up      3000/tcp
...
```

### 3.2 服务访问

| 服务 | 地址 | 用户名 | 密码 |
|------|------|--------|------|
| Grafana | http://localhost:3000 | admin | admin |
| Prometheus | http://localhost:9090 | - | - |
| Elasticsearch | http://localhost:9200 | - | - |
| 巡检Web | http://localhost:8000 | - | - |

### 3.3 运行第一次巡检

```bash
# 进入项目目录并运行巡检
cd kzx
docker run --rm --network kzx_x_default -v %cd%:/app -w /app python:3.10-slim \
    pip install -q -r requirements.txt && python -m src.main inspect --skip-llm

# 查看报告
ls -la reports/
```

---

## 第4章 生产环境部署

### 4.1 服务器准备

#### 步骤1：创建专用用户（安全）
```bash
useradd -m -s /bin/bash xmonitor
passwd xmonitor  # 设置密码
```

#### 步骤2：安装Docker
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

#### 步骤3：创建专用网络
```bash
docker network create --subnet=172.20.0.0/16 x-network
```

### 4.2 配置修改

编辑 `config.yaml`：

```yaml
prometheus:
  url: http://实际IP地址:9090  # 修改为实际IP

elasticsearch:
  url: http://实际IP地址:9200  # 修改为实际IP
  username_env: ES_USERNAME    # 设置环境变量
  password_env: ES_PASSWORD
```

### 4.3 数据持久化

编辑 `docker-compose.yml`：

```yaml
services:
  prometheus:
    volumes:
      - ./prometheus-data:/prometheus
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  elasticsearch:
    volumes:
      - ./es-data:/usr/share/elasticsearch/data
```

### 4.4 资源限制（生产环境建议）

```yaml
services:
  prometheus:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### 4.5 安全加固

#### 防火墙配置
```bash
# Ubuntu
firewall-cmd --permanent --add-port=9090/tcp
firewall-cmd --permanent --add-port=9200/tcp
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

#### HTTPS配置（生产环境必须）
使用Nginx反向代理配置SSL证书。

---

# 第三篇 使用篇

## 第5章 Web界面使用

### 5.1 首页功能

打开 http://localhost:8000 进入巡检控制台。

**功能区域：**
- 统计卡片：显示已配置机房数、Prometheus指标数、历史报告数
- 巡检表单：选择巡检模式、报告格式、AI分析选项
- 进度条：实时显示巡检执行步骤
- 最近报告：显示历史巡检报告列表

### 5.2 开始巡检

1. 选择巡检模式：
   - **快照**：当前时刻的数据
   - **过去24小时**：最近1天的数据
   - **过去7天**：最近7天的数据
   - **自定义**：自定义时间段

2. 选择报告格式：
   - HTML（可在浏览器查看）
   - Markdown（.md文件）

3. 选择AI分析：
   - 启用（推荐） - 使用Claude分析
   - 跳过（快速） - 跳过AI分析

4. 点击"🚀 开始巡检"按钮

### 5.3 其他页面

| 页面 | 地址 | 功能 |
|------|------|------|
| 机房配置 | /sites | 管理监控机房 |
| 查询配置 | /queries | 配置PromQL和ES查询 |
| 系统设置 | /settings | 全局配置 |
| 巡检报告 | /reports | 查看历史报告 |

---

## 第6章 命令行使用

### 6.1 基本命令

```bash
# 运行巡检（跳过AI分析）
python -m src.main inspect --skip-llm

# 运行巡检（启用AI分析）
python -m src.main inspect

# 自定义时间段巡检
python -m src.main inspect --period 1d

# 指定输出目录
python -m src.main inspect --output-dir ./my-reports
```

### 6.2 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| --config | 配置文件路径 | --config config.yaml |
| --output-dir | 报告输出目录 | --output-dir ./reports |
| --period | 巡检模式 | instant/1d/1w |
| --start | 自定义起始时间 | --start 2026-05-01T00:00 |
| --end | 自定义结束时间 | --end 2026-05-02T00:00 |
| --skip-llm | 跳过AI分析 | --skip-llm |
| --notify/--no-notify | 发送/不发送通知 | --no-notify |

---

# 第四篇 运维篇

## 第7章 监控指标配置

### 7.1 Prometheus指标

在 `config.yaml` 中配置：

```yaml
prometheus:
  url: http://prometheus:9090
  timeout_sec: 10
  queries:
    - name: cpu_usage
      promql: '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
      threshold: 10
      unit: '%'
      datacenter_filter: true
      description: CPU使用率
```

### 7.2 常用阈值配置

| 指标 | 阈值 | 说明 |
|------|------|------|
| cpu_usage | 10% | CPU使用率 |
| memory_usage | 60% | 内存使用率 |
| disk_usage | 80% | 磁盘使用率 |
| system_load | 32 | 系统负载 |
| mysql_connections | 6000 | MySQL连接数 |
| mysql_qps | 2000 | QPS |

### 7.3 Elasticsearch日志查询

```yaml
elasticsearch:
  queries:
    - name: error_logs_24h
      index: 'logstash-*'
      query_string: 'level:ERROR OR level:FATAL'
      time_range_hours: 24
      size: 50

    - name: warning_logs_24h
      index: 'logstash-*'
      query_string: 'level:WARN OR level:WARNING'
      time_range_hours: 24
      size: 100
```

---

## 第8章 告警与通知

### 8.1 配置告警通知

编辑 `config.yaml`：

```yaml
notifiers:
  - type: dingtalk
    webhook_url: https://oapi.dingtalk.com/robot/send?access_token=xxx

  - type: email
    smtp_host: smtp.example.com
    smtp_port: 587
    from: monitor@example.com
    to: admin@example.com
```

### 8.2 配置定时任务

#### Linux
```bash
crontab -e
# 每天凌晨2点运行巡检
0 2 * * * /usr/bin/python3 /opt/kzx/venv/bin/python -m src.main inspect --skip-llm >> /var/log/inspect.log 2>&1
```

#### Windows
打开"任务计划程序" -> 创建基本任务

---

## 第9章 数据备份与恢复

### 9.1 备份配置

```bash
# 备份配置文件
tar czf config-backup-$(date +%Y%m%d).tar.gz config.yaml prometheus/ grafana/
```

### 9.2 恢复配置

```bash
# 解压恢复
tar xzf config-backup-20260502.tar.gz
```

### 9.3 ES数据备份

```bash
# 快照备份
docker exec elasticsearch curl -X PUT "http://localhost:9200/_snapshot/my_backup/snapshot_1?wait_for_completion=true"
```

---

# 第五篇 开发篇

## 第10章 项目结构

```
kzx/
├── src/                        # 源代码
│   ├── collectors/             # 数据采集
│   │   ├── prometheus.py       # Prometheus采集
│   │   ├── elasticsearch.py    # ES日志采集
│   │   └── prometheus_range.py # 范围数据采集
│   ├── web/                   # Web界面
│   │   ├── app.py             # FastAPI应用
│   │   ├── config_store.py    # 配置管理
│   │   └── templates/          # HTML模板
│   ├── config.py              # 配置解析
│   ├── main.py                # CLI入口
│   ├── analyzer.py            # AI分析
│   └── reporter.py            # 报告生成
├── config.yaml                # 主配置文件
├── docker-compose.yml         # 容器编排
├── templates/                 # 报告模板
└── reports/                  # 生成的报告
```

---

## 第11章 开发指南

### 11.1 添加新指标

1. 在 `config.yaml` 中添加：
```yaml
- name: new_metric
  promql: 'new_metric_query'
  threshold: 100
  unit: ''
```

2. 重启巡检服务

### 11.2 添加新页面

1. 在 `templates/` 创建HTML文件
2. 在 `app.py` 添加路由：
```python
@app.get("/new-page")
async def new_page(request: Request):
    return render_template("new-page.html", {})
```

### 11.3 调试

```bash
# 启动Web服务（热重载）
python -m src.main web --reload

# 运行巡检
python -m src.main inspect --skip-llm
```

---

# 第六篇 故障排除篇

## 第12章 常见问题

### Q1: Docker启动失败

**解决方法：**
- 检查WSL2是否安装
- 更新Windows到最新版本

### Q2: 服务无法访问

**解决方法：**
- 检查端口占用：netstat -ano | findstr "9090"
- 检查防火墙设置

### Q3: 指标采集失败

**解决方法：**
- 检查Prometheus Targets状态
- 检查网络连通性

### Q4: Web界面500错误

**解决方法：**
```bash
# 查看日志
docker logs x-web
# 检查配置
docker exec x-web python -c "from src.web import config_store as cs; print(cs.get_all())"
```

### Q5: 巡检结果与预期不符

**解决方法：**
- 调整config.yaml中的threshold值
- 检查PromQL查询语法

---

# 附录

## 附录A：端口速查表

| 端口 | 服务 | 说明 |
|------|------|------|
| 9090 | Prometheus | 指标存储 |
| 9200 | Elasticsearch | 日志存储 |
| 3000 | Grafana | 可视化 |
| 8000 | 巡检Web | Web界面 |
| 9100 | Node Exporter | 节点监控 |

## 附录B：命令速查表

| 命令 | 说明 |
|------|------|
| `docker-compose up -d` | 启动所有服务 |
| `docker-compose down` | 停止所有服务 |
| `docker-compose logs -f` | 查看日志 |
| `python -m src.main inspect` | 运行巡检 |
| `python -m src.main web` | 启动Web |

## 附录C：配置文件示例

完整配置示例见 `config.example.yaml`

---

**修订历史**

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0.0 | 2026-05-02 | 初始版本 |
| v1.1.0 | 2026-05-02 | 多机房支持 |
| v1.2.0 | 2026-05-02 | Web界面修复，完善文档 |

---

*本手册由X项目开发组编写*
*如有问题，请提交Issue：https://github.com/liuliu4356/kzx/issues*