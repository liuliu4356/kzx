# 🖥️ KZX 智能运维巡检系统

<p align="center">
  <img src="https://img.shields.io/badge/Version-v1.2.0-00D2FF?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License">
</p>

> 🚀 企业级 Prometheus + ELK + AI 自动化运维巡检解决方案 | 多机房架构 | 智能异常检测 | 自动报告生成

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔍 **多维度指标采集** | 自动采集 CPU、内存、磁盘、网络等系统指标，支持 Prometheus Exporter 扩展 |
| 📊 **智能日志分析** | 基于 Elasticsearch + Logstash 构建的分布式日志分析引擎 |
| 🤖 **AI 驱动异常检测** | 集成 Claude AI 大语言模型，智能识别潜在风险 |
| 🏢 **多机房架构** | 支持北京东坝、北京南法信、合肥等多数据中心统一巡检 |
| 📝 **自动化报告** | 一键生成 Markdown/HTML 巡检报告，支持定时任务 |
| 🔔 **多渠道通知** | 支持钉钉、企业微信、邮件等告警通知 |

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                         KZX 巡检系统架构                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                   应用服务层                           │       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │       │
│  │  │   Web UI   │  │  CLI Tool  │  │  Report   │  │       │
│  │  │  (FastAPI) │  │  (Click)   │  │  (Jinja2) │  │       │
│  │  │   :8000    │  │    --     │  │   .md/.html│  │       │
│  │  └────────────┘  └────────────┘  └────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   数据采集层                          │       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │       │
│  │  │ Prometheus│  │Elasticsearch│ │  Scheduler │  │       │
│  │  │  :9090    │  │   :9200    │  │  Cron     │  │       │
│  │  │(指标存储)  │  │ (日志存储)  │  │(定时任务) │  │       │
│  │  └────────���───┘  └────────────┘  └────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   可视化层                          │       │
│  │  ┌────────────┐  ┌────────────┐                   │       │
│  │  │  Grafana   │  │   Kibana   │                   │       │
│  │  │   :3000    │  │   :5601   │                   │       │
│  │  │ (指标看板) │  │ (日志分析)│                   │       │
│  │  └────────────┘  └────────────┘                   │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 一键启动

```bash
# 克隆项目
git clone https://github.com/liuliu4356/kzx.git
cd kzx

# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

### 2. 运行巡检

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config.example.yaml config.yaml
# 编辑 config.yaml 和 .env

# 执行巡检
python -m src.main inspect

# 或启动 Web 界面
python -m src.main web
```

---

## 📖 使用指南

### 命令行选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | config.yaml |
| `--output-dir` | 报告输出目录 | reports/ |
| `--period` | 巡检模式 | instant/1d/1w |
| `--skip-llm` | 跳过 AI 分析 | false |
| `--notify/--no-notify` | 是否发送通知 | true |
| `--format` | 报告格式 | md/html |

### Web 界面

| 服务 | 地址 | 账号 |
|------|------|------|
| 巡检控制台 | http://localhost:8000 | - |
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Elasticsearch | http://localhost:9200 | - |

---

## 📁 项目结构

```
kzx/
├── src/                          # 核心源码
│   ├── main.py                   # CLI 入口
│   ├── config.py                 # 配置管理
│   ├── analyzer.py              # AI 智能分析
│   ├── reporter.py             # 报告生成
│   ├── collectors/             # 数据采集
│   │   ├── prometheus.py       # Prometheus 采集
│   │   └── elasticsearch.py    # ES 日志采集
│   ├── web/                   # Web 服务
│   │   └── app.py             # FastAPI 应用
│   └── notifiers/              # 通知模块
├── config.yaml                 # 主配置
├── docker-compose.yml           # 容器编排
├── templates/                # 报告模板
└── docs/                     # 完整文档
```

---

## 🐛 故障排查

| 问题 | 解决方案 |
|------|----------|
| Docker 启动失败 | 确保 Docker Desktop 已启动，更新到最新版本 |
| 指标采集失败 | 检查 Prometheus Targets 状态和网络连通性 |
| AI 分析失败 | 检查 `.env` 中的 API_KEY 配置 |
| Web 界面 500 | 查��日志 `docker logs kzx-web` |

---

## 📄 许可证

MIT License - 请查看 [LICENSE](LICENSE) 文件

---

<p align="center">
  <a href="https://github.com/liuliu4356/kzx">
    <img src="https://img.shields.io/github/stars/liuliu4356/kzx?style=social" alt="Stars">
  </a>
  <a href="https://github.com/liuliu4356/kzx/issues">
    <img src="https://img.shields.io/github/issues-closed/liuliu4356/kzx" alt="Issues">
  </a>
</p>