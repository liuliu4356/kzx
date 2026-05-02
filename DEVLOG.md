# X 项目开发日志

> 目标：面向信创 GoldenDB（GDB）生产环境的自动巡检工具，覆盖指标采集 → AI 分析 → 报告生成 → 告警通知全链路。

---

## Demo-1 · 基础框架搭建

**日期**：2026-05-02  
**状态**：✅ 完成

### 完成内容

| 模块 | 文件 | 说明 |
|---|---|---|
| 配置层 | `src/config.py` | 强类型 dataclass，支持 Prometheus / ES / LLM / Report 四块配置 |
| Prometheus 采集 | `src/collectors/prometheus.py` | httpx 调用 `/api/v1/query`，取 max/min 代表值，阈值判断 |
| ES 采集 | `src/collectors/elasticsearch.py` | 支持 Basic Auth，query_string + 时间范围，提取 top-N hits |
| AI 分析 | `src/analyzer.py` | 调用 Claude API，System Prompt 启用 prompt caching，输出四节 Markdown |
| 报告生成 | `src/reporter.py` | Jinja2 渲染 `templates/report.md.j2`，按 filename_format 写文件 |
| CLI 入口 | `src/main.py` | Click，`init-config` / `inspect` 两条命令，四步流水线 |
| 报告模板 | `templates/report.md.j2` | 含指标表格、ES 日志折叠块、AI 分析节 |

### 关键设计决策

- **PromResult 聚合策略**：取所有 series 的 max（`anomaly_when=gt`）或 min（`anomaly_when=lt`），适合 MVP 快速判断。
- **Prompt Caching**：System Prompt 标记 `cache_control: ephemeral`，重复巡检命中缓存，节省 token。
- **错误不中断流程**：采集失败时 `error` 字段记录原因，继续执行后续步骤，报告中展示采集错误。

### 运行方式

```bash
cp config.example.yaml config.yaml   # 或 python -m src.main init-config
python -m src.main inspect
python -m src.main inspect --skip-llm --no-notify
```

---

## Demo-2 · 通知层（钉钉 + 飞书）

**日期**：2026-05-02  
**状态**：✅ 完成

### 完成内容

| 模块 | 文件 | 说明 |
|---|---|---|
| 钉钉通知 | `src/notifiers/dingtalk.py` | Markdown 消息，支持 `mention_all` @所有人 |
| 飞书通知 | `src/notifiers/feishu.py` | 富文本 post 消息，按行拆分段落 |
| 通知分发器 | `src/notifiers/__init__.py` | 遍历配置的渠道列表，收集错误不中断，返回错误列表 |
| 配置扩展 | `src/config.py` | 新增 `NotifierItem` dataclass，`Config.notifiers` 字段 |

### 通知消息结构

```
系统巡检报告 — ⚠️ 发现异常
异常指标: 1 / 4
异常详情:
- instance_up: 0.00 (阈值 1.0)
报告文件: `reports/2026-05-02-0816.md`
```

### CLI 新增选项

```bash
python -m src.main inspect --no-notify      # 跳过通知
python -m src.main inspect --skip-llm       # 跳过 AI 分析
```

### 配置方式

```yaml
# config.yaml
notifiers:
  - type: dingtalk
    webhook_env: DINGTALK_WEBHOOK
    mention_all: false
  - type: feishu
    webhook_env: FEISHU_WEBHOOK
```

---

## Demo-3 · GDB 专项配置 + 批处理时间窗口

**日期**：2026-05-02  
**状态**：🚧 进行中

### 目标

对照生产巡检模板（GoldenDB 信创环境），补充以下 P0 缺口：

1. PromQL 覆盖 GDB 专项指标（连接数、QPS、TPS、主备延迟、系统负载、网络、磁盘 IO、慢日志）
2. 新增 `batch_windows` 配置，让 AI 感知批处理时间段，避免误报

### 技术方案

- `config.py` 新增 `BatchWindow` dataclass（label / start_hour / end_hour / relaxed_thresholds）
- `analyzer.py` 在构建 user payload 时注入当前是否处于批处理窗口及放宽阈值
- `config.example.yaml` 补充完整 GDB PromQL + batch_windows 示例

---

*后续 Demo 将在此文档追加。*
