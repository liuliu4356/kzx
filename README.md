# X 自动化监控巡检系统

> 基于 Prometheus + ELK + AI 的自动化运维巡检解决方案

[![版本](https://img.shields.io/badge/version-v1.1.0-blue.svg)](CHANGELOG.md)
[![Docker](https://img.shields.io/docker/pulls/prom/prometheus.svg)](https://hub.docker.com/u/prom)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/v/release/liuliu4356/kzx)](https://github.com/liuliu4356/kzx/releases)

## 📋 版本信息

| 版本 | 日期 | 说明 |
|------|------|------|
| [v1.1.0](CHANGELOG.md#v110-2026-05-02---多机房支持版本) | 2026-05-02 | 多机房支持，按生产巡检标准配置 |
| [v1.0.0](CHANGELOG.md#v100-2026-05-02---初始版本) | 2026-05-02 | 初始版本，基础监控架构 |

**[查看完整更新日志](CHANGELOG.md)**

## 📋 项目简介

X 是一个企业级自动化监控巡检系统，用于：

- **基础设施监控** - CPU、内存、磁盘、网络等系统指标
- **日志分析** - 收集、分析系统与应用日志
- **智能告警** - 异常指标自动告警
- **AI 分析** - 使用 Claude AI 分析监控数据，发现潜在问题
- **自动报告** - 生成巡检报告，支持中文/英文

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      数据采集层                              │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ Node        │  Prometheus │   Filebeat  │  MySQL/PostgreSQL│
│ Exporter    │  Exporter   │   Exporter  │  Redis Exporter   │
│   :9100     │   :9090     │   :9200     │  :9187/:9121     │
└──────┬──────┴──────┬──────┴──────┬──────┴────────┬─────────┘
       │             │             │              │
       ▼             ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                      存储与计算层                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Prometheus    │ Elasticsearch   │   Logstash              │
│   :9090         │   :9200        │   :9600 :8080 :5044     │
│   (时序数据库)   │   (日志存储)    │   (日志处理)            │
└────────┬────────┴────────┬────────┴────────────┬────────────┘
         │                │                     │
         ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      应用服务层                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│     Grafana     │     Kibana      │    X 巡检引擎           │
│     :3000       │     :5601       │    (Python CLI)         │
│   (可视化)      │   (日志分析)     │    (AI 分析 + 报告)     │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

| 组件 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 或 Linux (Ubuntu 22.04+) |
| Docker | Docker Desktop 4.0+ 或 Docker Engine 20.10+ |
| Python | 3.10+ |
| 内存 | 推荐 8GB+ |
| 磁盘 | 推荐 50GB+ |

### 2. 克隆项目

```bash
git clone https://github.com/liuliu4356/kzx.git
cd kzx
```

### 3. 启动服务

**Windows:**
```powershell
.\start.bat
```

**Linux:**
```bash
docker compose up -d
```

### 4. 配置与运行

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境
# Windows
.venv\Scripts\activate
# Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 添加 ANTHROPIC_API_KEY

# 运行巡检
python -m src.main inspect
```

## 📖 使用说明

### 命令行选项

```bash
python -m src.main inspect [OPTIONS]

选项:
  --config PATH      配置文件路径 (默认: config.yaml)
  --output-dir PATH  报告输出目录
  --skip-llm        跳过 AI 分析
  --notify/--no-notify  是否发送通知 (默认: True)
```

### 配置说明

编辑 `config.yaml`:

```yaml
prometheus:
  url: http://localhost:9090
  timeout_sec: 10
  queries:
    - name: cpu_usage
      promql: '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
      threshold: 80
      unit: '%'

elasticsearch:
  url: http://localhost:9200
  queries:
    - name: error_logs_24h
      index: 'logstash-*'
      query_string: 'level:ERROR OR level:FATAL'
      time_range_hours: 24

llm:
  provider: anthropic
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
```

## 📊 监控指标

| 指标类型 | 采集工具 | 说明 |
|----------|----------|------|
| 系统指标 | Node Exporter | CPU、内存、磁盘、网络 |
| 数据库指标 | mysqld_exporter, postgres_exporter | 连接数、QPS、TPS |
| 日志 | Filebeat + Logstash | 应用日志、错误日志 |
| 告警 | Alertmanager | 告警通知 |

## 🔧 常用操作

### 查看服务状态

```bash
docker ps
```

### 查看日志

```bash
# 查看 Prometheus 日志
docker logs -f prometheus

# 查看 Elasticsearch 日志
docker logs -f elasticsearch
```

### 重启服务

```bash
# 重启单个服务
docker restart prometheus

# 重启所有服务
docker compose restart
```

### 停止服务

```bash
# Windows
.\stop.bat

# Linux
docker compose down
```

## 📁 目录结构

```
kzx/
├── src/                      # Python 源代码
│   ├── main.py              # 主入口
│   ├── config.py           # 配置加载
│   ├── analyzer.py          # AI 分析
│   ├── reporter.py          # 报告生成
│   ├── collectors/          # 数据采集
│   │   ├── prometheus.py    # Prometheus 采集
│   │   └── elasticsearch.py # ES 采集
│   └── notifiers/           # 通知模块
│       ├── dingtalk.py
│       └── feishu.py
├── docker-compose.yml       # Docker 编排
├── config.yaml             # 主配置
├── requirements.txt         # Python 依赖
├── reports/                 # 巡检报告输出
├── prometheus/              # Prometheus 配置
├── grafana/                 # Grafana 配置
├── logstash/                # Logstash 配置
├── filebeat/                # Filebeat 配置
└── templates/                # 报告模板
```

## 🐛 常见问题

### Q: Docker 启动失败

**解决:** 确保 Docker Desktop 已启动，或在 Linux 上运行:
```bash
sudo systemctl start docker
```

### Q: 报告生成失败

**解决:** 检查 `.env` 文件中的 `ANTHROPIC_API_KEY` 是否正确设置

### Q: Prometheus 无数据

**解决:** 检查 Node Exporter 是否正常运行:
```bash
curl http://localhost:9100/metrics
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- GitHub: https://github.com/liuliu4356/kzx
- Email: your-email@example.com