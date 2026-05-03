# 三思GDB巡检平台 — Hermes Agent 项目指南

> 本文件被 Hermes Agent 自动读取，定义项目上下文和工作规范。
> 等同于 Claude Code 中的 CLAUDE.md。

---

## 项目概要

**名称**: 三思GDB巡检平台 (v1.4.0)  
**仓库**: https://github.com/liuliu4356/kzx  
**技术栈**: Python 3.10+ · FastAPI · Uvicorn · Jinja2 · httpx · Anthropic SDK · PyYAML · Click  
**项目路径 (WSL2)**: `/mnt/d/claude_code开发/X`  

面向 GoldenDB 信创生产环境的自动巡检工具，覆盖指标采集 → AI 分析 → 报告生成 → 告警通知全链路。

---

## 目录结构（关键）

```
src/
  config.py           # 配置 dataclass + load_config()
  main.py             # CLI 入口（Click）：inspect / web / init-config
  analyzer.py         # Claude API 调用，AI 分析报告
  reporter.py         # Jinja2 渲染 md/html 报告
  collectors/
    __init__.py       # collect_sites()：多机房并发采集
    prometheus.py     # 即时快照 /api/v1/query
    prometheus_range.py # 时间段审计 /api/v1/query_range
    elasticsearch.py  # ES 日志查询
  notifiers/
    __init__.py       # notify_all()
    dingtalk.py / feishu.py
  web/
    app.py            # FastAPI 路由 + SSE 流式巡检
    config_store.py   # config.yaml CRUD
    static/style.css  # 深色 CSS 设计系统
    templates/        # Jinja2 HTML 模板
templates/
  report.md.j2 / report.html.j2   # 报告模板
config.yaml          # 实际配置（gitignore，含敏感信息）
config.example.yaml  # 配置示例
requirements.txt
```

---

## 开发规范

### 运行项目
```bash
# 在 Windows Git Bash 或 WSL2 内：
cd /mnt/d/claude_code开发/X     # WSL2
# 或 cd "D:/claude_code开发/X"   # Git Bash

# 启动 Web 服务
PYTHONIOENCODING=utf-8 python3 -m src.main web

# CLI 巡检（跳过 AI）
python3 -m src.main inspect --skip-llm --no-notify

# 时间段审计
python3 -m src.main inspect --period 1d
```

### 代码规范
- Python 3.10+，使用 `match/case`、`str | None`、`dataclass`
- 所有函数签名都有类型注解
- 错误不中断流程：采集失败写 `error` 字段，不 raise
- 默认不写注释，只在 WHY 不明显时写
- 不添加超出需求的抽象和功能

### 配置扩展
- 新增监控指标：修改 `config.yaml`（prometheus.queries 或 elasticsearch.queries），**无需改代码**
- 新增通知渠道：在 `src/notifiers/` 新建文件，在 `__init__.py` 注册
- 新增 Web 页面：新建模板 + `app.py` 加路由 + `base.html` 加菜单项
- 新增项目总览文档：在 `_OVERVIEW_PAGES` 字典加条目 + `base.html` 加链接

---

## 常用任务

### 发布新版本
1. 更新 `CHANGELOG.md` 和 `DEVLOG.md`
2. `git add` 相关文件（不要 `git add -A`，避免提交敏感文件）
3. `git commit -m "feat/fix/docs: 描述"`
4. `git push origin master`

### 跑测试
```bash
python3 -m src.main inspect --skip-llm --no-notify  # 验证采集链路
curl http://localhost:8000                           # 验证 Web 服务
```

### 调试 Prometheus 采集
```python
from src.config import load_config
from src.collectors.prometheus import collect
cfg = load_config("config.yaml")
results = collect(cfg.prometheus)
for r in results: print(r.name, r.value, r.is_anomaly)
```

---

## 环境变量

| 变量 | 说明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API Key（必须，或通过 config.yaml 指定 key_env） |
| `DINGTALK_WEBHOOK` | 钉钉通知 Webhook URL（可选） |
| `FEISHU_WEBHOOK` | 飞书通知 Webhook URL（可选） |
| `PYTHONIOENCODING` | Windows 下设为 `utf-8` 避免 emoji 编码错误 |

---

## Hermes Skills 推荐使用

在此项目中可调用以下 Skills：

| Skill | 用途 |
|---|---|
| `software-development/plan` | 新功能开发前制定实施方案 |
| `software-development/test-driven-development` | 为采集器、分析器编写测试 |
| `software-development/systematic-debugging` | 系统性排查 Bug |
| `software-development/requesting-code-review` | 提交前代码审查 |
| `software-development/subagent-driven-development` | 大功能分解为子任务并行执行 |
| `devops` | 部署脚本、systemd 服务配置 |

---

## 待开发（Roadmap v1.5.0）

- [ ] GoldenDB 组件专用监控（OMM/RDB/MDS/CM/PM 状态检查）
- [ ] 表规模监控（表记录数 / 表大小 PromQL）
- [ ] 定时任务配置（Web UI 配置 cron 巡检计划）
- [ ] 知识库检索集成（向量检索，接入巡检分析流程）
- [ ] 历史趋势对比（与上次报告 diff，标出新增/已恢复异常）
