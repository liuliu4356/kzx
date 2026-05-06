---
name: X-inspection
description: 三思GDB巡检平台开发、部署与运维技能
---

# X 自动化监控巡检系统技能

## When to use

- 开发和调试X项目（三思GDB巡检平台）
- 对接生产Prometheus/ES/Grafana监控系统
- 配置多机房巡检、告警通知
- 使用Claude Code + OpenCode进行AI编程
- 部署项目到生产环境

## Project Overview

X是面向多数据中心的自动化巡检解决方案，技术栈：
- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **监控**: Prometheus + Grafana + Alertmanager
- **日志**: Elasticsearch + Kibana + Logstash + Filebeat (ELK)
- **AI**: Claude API集成，自动生成巡检报告
- **通知**: 支持钉钉/飞书/企业微信

## Quick Start

### 启动项目
```bash
# 启动Docker服务（Prometheus/ES/Grafana等）
cd D:\claude_code开发\X
docker-compose up -d

# 启动Web服务
python -m src.main web --port 8000

# 验证
curl http://localhost:8000/
```

### 执行巡检
```bash
# 即时巡检
python -m src.main inspect --skip-llm --no-notify

# 24小时审计
python -m src.main inspect --period 1d

# 启用AI分析（需要ANTHROPIC_API_KEY）
python -m src.main inspect
```

## Project Structure

```
X/
├── src/
│   ├── config.py          # 配置加载（dataclass + YAML）
│   ├── main.py            # CLI入口（Click框架）
│   ├── analyzer.py        # Claude API调用，AI分析报告
│   ├── reporter.py        # Jinja2渲染md/html报告
│   ├── collectors/
│   │   ├── prometheus.py # Prometheus指标采集
│   │   └── elasticsearch.py # ES日志采集
│   ├── notifiers/
│   │   ├── dingtalk.py   # 钉钉通知
│   │   └── feishu.py    # 飞书通知
│   └── web/
│       ├── app.py        # FastAPI路由 + SSE流式巡检
│       └── config_store.py # config.yaml CRUD
├── docker-compose.yml    # 所有服务容器定义
├── config.yaml           # 主配置文件（gitignore，含敏感信息）
├── config.example.yaml   # 配置示例
├── requirements.txt
├── CLAUDE.md           # Claude Code项目规范
└── AGENTS.md           # Hermes Agent项目配置
```

## Key Commands

| 命令 | 说明 |
|------|------|
| `python -m src.main web` | 启动Web界面（默认8000端口） |
| `python -m src.main inspect` | 执行巡检并生成AI报告 |
| `python -m src.main init-config` | 初始化配置文件 |
| `test_inspection_mock.py` | Mock数据测试（无需Docker） |
| `test_anomaly_scenarios.py` | 生成异常场景测试 |

## Configuration

### config.yaml 关键配置
```yaml
prometheus:
  url: http://localhost:9090  # 生产环境改为实际地址
  queries: [...]  # 监控指标（CPU/内存/磁盘等）

elasticsearch:
  url: http://localhost:9200  # 生产环境改为实际地址
  queries: [...]  # 日志查询（ERROR/WARN/Slow Query）

datacenters:  # 多机房配置
  - name: 北京东坝
    code: dongba
    components: [...]
```

## AI编程规范（CLAUDE.md）

项目已配置CLAUDE.md，包含：
- Python 3.10+语法要求（match/case、str | None）
- 函数必须有完整类型注解
- 错误不raise，写入error字段
- 不添加超出需求的抽象和注释

## Deployment

### 生产环境对接
1. 修改`config.yaml`中的Prometheus/ES地址
2. 启动X应用：`python -m src.main web`
3. 配置定时巡检（crontab或Windows任务计划）

### Git版本管理
- 主分支：`master/main`
- 提交规范：Conventional Commits（feat/fix/docs/chore）
- 自动推送：已配置GitHub Actions和crontab脚本

## Resources

| 类型 | 地址 |
|------|------|
| **GitHub** | https://github.com/liuliu4356/kzx |
| **Gitee** | https://gitee.com/liu4356/kzx |
| **文档** | `Vibe_Coding初体验_X项目开发全记录.md` |
| **Web** | http://localhost:8000 |
| **Prometheus** | http://localhost:9090 |
| **Grafana** | http://localhost:3000 |
| **Kibana** | http://localhost:15601 |

## Troubleshooting

| 问题 | 解决方案 |
|------|----------|
| Docker启动失败 | 检查Docker Desktop是否运行，查看端口占用 |
| 巡检无数据 | 检查config.yaml中URL是否正确（localhost vs 容器地址） |
| Web服务无法访问 | 检查8000端口是否被占用，查看日志 |
| AI报告生成失败 | 检查ANTHROPIC_API_KEY环境变量是否设置 |
