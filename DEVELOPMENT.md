# X 项目开发文档（基于 SKILL.md 生成）

> 本文档由 SKILL.md 自动生成，详细说明 X 自动化监控巡检系统的开发、部署与运维流程。

---

## 📖 项目概述

**三思GDB巡检平台** 是面向多数据中心的自动化巡检解决方案，支持：
- Prometheus 指标监控与异常检测
- Elasticsearch 日志分析与错误定位
- AI 驱动的智能巡检报告生成
- 多机房统一管理（东坝、南法信、合肥灾备）
- 钉钉/飞书告警通知集成

**技术栈**：
- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **监控**: Prometheus + Grafana + Alertmanager
- **日志**: Elasticsearch + Kibana + Logstash + Filebeat (ELK)
- **AI**: Claude API 集成，自动生成巡检报告
- **通知**: 支持钉钉/飞书/企业微信

**项目地址**：
- GitHub: https://github.com/liuliu4356/kzx
- Gitee: https://gitee.com/liuliu4356/kzx

---

## 🏗️ 快速开始

### 启动项目

```bash
# 1. 启动 Docker 服务（Prometheus/ES/Grafana 等）
cd D:\claude_code开发\X
docker-compose up -d

# 2. 启动 Web 服务
python -m src.main web --port 8000

# 3. 验证服务
curl http://localhost:8000/
```

### 执行巡检

```bash
# 即时巡检（跳过 AI 分析）
python -m src.main inspect --skip-llm --no-notify

# 24 小时审计
python -m src.main inspect --period 1d

# 启用 AI 分析（需要 ANTHROPIC_API_KEY）
python -m src.main inspect
```

---

## 📂 项目结构

```
X/
├── src/
│   ├── config.py          # 配置加载（dataclass + YAML）
│   ├── main.py            # CLI 入口（Click 框架）
│   ├── analyzer.py        # Claude API 调用，AI 分析报告
│   ├── reporter.py        # Jinja2 渲染 md/html 报告
│   ├── collectors/
│   │   ├── __init__.py       # collect_sites()：多机房并发采集
│   │   ├── prometheus.py     # 即时快照 /api/v1/query
│   │   ├── prometheus_range.py # 时间段审计 /api/v1/query_range
│   │   └── elasticsearch.py # ES 日志查询
│   ├── notifiers/
│   │   ├── __init__.py       # notify_all()
│   │   ├── dingtalk.py       # 钉钉通知
│   │   └── feishu.py        # 飞书通知
│   └── web/
│       ├── app.py            # FastAPI 路由 + SSE 流式巡检
│       ├── config_store.py    # config.yaml CRUD
│       ├── static/style.css # 深色 CSS 设计系统
│       └── templates/        # Jinja2 HTML 模板
├── templates/
│   ├── report.md.j2       # Markdown 报告模板
│   └── report.html.j2      # HTML 报告模板
├── docker-compose.yml    # 所有服务容器定义
├── config.yaml           # 主配置（gitignore，含敏感信息）
├── config.example.yaml   # 配置示例
├── requirements.txt      # Python 依赖
├── CLAUDE.md           # Claude Code 项目规范
├── AGENTS.md           # Hermes Agent 项目配置
└── SKILL.md            # 项目技能文件（本技能）
```

---

## 🔧 配置说明

### Prometheus 配置（config.yaml）

```yaml
prometheus:
  url: http://localhost:9090  # 生产环境改为实际地址
  timeout_sec: 10
  queries:
    - name: cpu_usage
      promql: '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
      threshold: 80
      unit: '%'
      description: CPU 使用率
    # ... 更多指标
```

### Elasticsearch 配置

```yaml
elasticsearch:
  url: http://localhost:9200  # 生产环境改为实际地址
  username_env: ES_USERNAME
  password_env: ES_PASSWORD
  timeout_sec: 10
  queries:
    - name: error_logs_24h
      index: logstash-*
      query_string: level:ERROR OR level:FATAL
      time_range_hours: 24
      size: 50
```

### 多机房配置

```yaml
datacenters:
  - name: 北京东坝
    code: dongba
    vip: 25.131.185.100
    components:
      - name: OMM/RDB/MDS/CM/PM
        count: 2
        ip_range: 25.131.185.181-182
  # ... 更多机房
```

---

## 💻 开发规范（CLAUDE.md）

项目已配置 `CLAUDE.md`，包含：
- 使用 Python 3.10+ 语法（match/case、str | None 类型注解）
- 所有函数必须有完整的类型注解
- 错误不 raise，写入 error 字段，不中断流程
- 默认不写注释，仅 WHY 不明显时写
- 不添加超出需求的抽象层和过度设计

---

## 🚀 部署指南

### 生产环境对接

1. 修改 `config.yaml` 中的 URL：
   - `prometheus.url` → 生产 Prometheus 地址
   - `elasticsearch.url` → 生产 ES 地址

2. 启动应用：
```bash
python -m src.main web --host 0.0.0.0 --port 8000
```

3. 配置定时巡检（crontab）：
```bash
# 每天 8 点和 18 点执行
0 8,18 * * * cd /path/to/X && python -m src.main inspect --skip-llm
```

### Docker 部署（推荐）

```bash
# 构建镜像
docker build -t x-inspection:latest .

# 启动容器
docker run -d \
  --name x-inspection \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/reports:/app/reports \
  -e ANTHROPIC_API_KEY=your_key \
  x-inspection:latest
```

---

## 🧪 测试

### Mock 测试（无需 Docker）

```bash
# 运行模拟巡检测试
python test_inspection_mock.py

# 生成异常场景
python test_anomaly_scenarios.py --scenario all

# 生成测试数据
python generate_test_anomalies.py --type es --count 30
```

### 验证清单

- [ ] Web 服务可访问 http://localhost:8000
- [ ] 巡检命令可执行 `python -m src.main inspect --skip-llm`
- [ ] 报告目录有输出 `ls reports/`
- [ ] Prometheus 可访问 http://localhost:9090
- [ ] Grafana 可访问 http://localhost:3000
- [ ] Kibana 可访问 http://localhost:15601

---

## 📚 资源链接

| 类型 | 地址 |
|------|------|
| **项目 GitHub** | https://github.com/liuliu4356/kzx |
| **项目 Gitee** | https://gitee.com/liuliu4356/kzx |
| **Claude Code 官网** | https://claude.ai/code |
| **OpenCode 官网** | https://opencode.ai |
| **Hermes Agent 官网** | https://hermes-agent.lzw.me |
| **Web 验证** | http://localhost:8000 |
| **Prometheus** | http://localhost:9090 |
| **Grafana** | http://localhost:3000 |
| **Kibana** | http://localhost:15601 |

---

> 本文档由 SKILL.md 自动生成，基于 X 项目技能文件。
> 最后更新：2026-05-03
