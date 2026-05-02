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
**状态**：✅ 完成

### 背景

对照实际生产巡检模板（GoldenDB 信创环境，东坝/南法信/合肥三机房），原有配置存在两个 P0 缺口：PromQL 未覆盖 GDB 专项指标；AI 不感知批处理时间窗口导致误报。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/config.py` | 新增 `BatchWindow` dataclass | 字段：label / start_hour / end_hour / relaxed_thresholds |
| `src/config.py` | 新增 `current_batch_window()` | 基于 UTC 小时判断当前是否处于批处理窗口 |
| `src/analyzer.py` | `analyze()` 接受 `batch_window` 参数 | 注入 context 节到 user payload，告知 AI 当前窗口和放宽阈值 |
| `src/main.py` | 检测并显示批处理窗口 | 在采集前打印 `[批处理窗口]` 提示，传入 analyzer |
| `config.example.yaml` | 全面重写 | 覆盖 GDB 全部 P0 指标（见下表） |

### GDB 新增 PromQL 指标

| 指标名 | 阈值 | 来源 exporter |
|---|---|---|
| `cpu_usage` | < 10%（批处理放宽至 80%） | node_exporter |
| `memory_usage` | < 60% | node_exporter |
| `system_load_per_core` | < 0.5（等价 64核 load5 < 32） | node_exporter |
| `network_throughput_mbps` | < 100 Mb/s | node_exporter |
| `disk_io_latency_ms` | < 100 ms | node_exporter |
| `disk_usage_data` | < 80% | node_exporter |
| `rdb_connections` | < 6000 | mysql_exporter |
| `qps` | < 2000 req/s | mysql_exporter |
| `tps` | < 100 tx/s | mysql_exporter |
| `replication_lag_sec` | < 1s（批处理放宽至 900s） | mysql_exporter |
| `dbproxy_slow_queries` | ≤ 2000（批处理放宽至 50000） | mysql_exporter |
| `instance_up` | = 1 | Prometheus 内置 |
| `emergency_alerts` | = 0 | GDB exporter |

### GDB 新增 ES 查询

| 查询名 | 用途 |
|---|---|
| `gdb_critical_errors` | 需人工排查的错误（连接丢失、锁超时、查询中断、死锁） |
| `gdb_known_ignorable` | 已知可忽略错误（packets out of order），仅统计条数 |
| `component_errors` | MDS/CM/PM/DBProxy 通用错误（排除已知可忽略项） |

### 批处理窗口感知机制

```
巡检开始
  └─ current_batch_window() 检测当前 UTC 小时
      ├─ 命中窗口 → 打印提示 + 将 relaxed_thresholds 注入 AI payload
      │             AI 会在分析时忽略窗口内的"伪异常"
      └─ 未命中  → 正常阈值，AI 按标准判断
```

### 关键设计决策

- **UTC 统一**：`current_batch_window` 使用 UTC 时间，配置中 `start_hour`/`end_hour` 也用 UTC，避免时区混乱。部署时按实际批处理北京时间减 8 小时填写。
- **只注入上下文，不修改采集阈值**：`PromResult.is_anomaly` 始终按原始阈值判断（用于通知摘要计数），批处理上下文仅传给 AI，由 AI 决定是否降低告警优先级。
- **已知可忽略日志单独一条 ES 查询**：不混入 critical 查询，让 AI 能明确区分"已知噪音"与"需排查问题"。

---

---

## Demo-4 · 多机房支持 + ES 日志分类

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

生产环境跨东坝、南法信、合肥三个机房，原有单 Prometheus URL 架构无法分机房展示；ES 日志中"已知可忽略"的噪音会干扰 AI 评分。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/config.py` | 新增 `SiteConfig` dataclass | 字段：label / prometheus_url / es_url（可选） |
| `src/config.py` | `ESQuery` 新增 `ignorable: bool` 字段 | 标记已知噪音查询 |
| `src/collectors/__init__.py` | 新增 `SiteResult` + `collect_sites()` | 按 sites 列表逐机房采集；未配置 sites 时降级为单机房 |
| `src/collectors/elasticsearch.py` | `ESResult` 新增 `ignorable` 字段 | 从 query config 传播到 result |
| `src/reporter.py` | 签名改为 `render(site_results, ai_analysis, cfg)` | 汇总表 + 各机房分节渲染 |
| `src/analyzer.py` | 签名改为 `analyze(site_results, cfg, batch_window)` | payload 按 sites 分组，ignorable 标记传入 AI |
| `src/notifiers/__init__.py` | 签名改为 `notify_all(cfg, site_results, path)` | 摘要按机房列出异常 |
| `src/main.py` | 全面重写采集流程 | 调用 `collect_sites()`，统一打印各机房采集摘要 |
| `templates/report.md.j2` | 全面重写 | 顶部汇总表 + 各机房独立 Prometheus/ES 节 |
| `config.example.yaml` | 新增 `sites` 配置段 + `ignorable: true` 标记 | 东坝/南法信/合肥三机房示例 |

### 多机房运行流程

```
collect_sites(cfg)
  ├─ sites 已配置 → 逐个 SiteConfig 构造专属 PromConfig/ESConfig → 独立采集
  └─ sites 未配置 → 用全局 prometheus.url/elasticsearch.url → 单机房兼容模式

site_results: list[SiteResult]
  └─ SiteResult.anomaly_count  （属性，动态计算）

analyze(site_results, ...)
  └─ payload.sites[i] = {site, prometheus, elasticsearch}
     AI 按机房分析，ignorable 查询不计入评分

report.md.j2
  └─ 顶部汇总表（各机房异常数/状态）
     + 每机房独立 ## 节（指标表 + ES 日志，可忽略查询标注）
```

### ES 日志分类机制

| 查询 | `ignorable` | 报告展示 | 计入 AI 评分 |
|---|---|---|---|
| `gdb_critical_errors` | false | 完整展示 + 折叠 top-N | ✅ 是 |
| `gdb_known_ignorable` | true | 标注「已知/可忽略」 | ❌ 否 |
| `component_errors` | false | 完整展示 | ✅ 是 |

### 向后兼容

不配置 `sites` 时，`collect_sites()` 自动创建 label="默认" 的单机房结果，所有下游模块行为不变。

---

## 待开发（下一步）

| 优先级 | 内容 |
|---|---|
| P2 | 表规模监控：补充表记录数 / 表大小 PromQL（需 GDB exporter 支持） |
| P2 | 数据字典状态检查：禁用/禁写表必须为 0 |
| P2 | 并发采集：多机房目前顺序执行，可用 `concurrent.futures` 并行化 |
| P3 | 历史趋势：对比上次报告，标出新增异常和已恢复项 |
