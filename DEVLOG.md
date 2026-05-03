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

---

## Demo-5 · 双模式巡检（快照 + 时间段审计）

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

快照模式只能看当前一刻，无法捕捉凌晨 2 点 CPU 突增等时间段内的异常。需要支持：按 1 天 / 1 周 / 自定义时间段进行审计，找出所有超阈值时段，并标注时间、机房、节点 IP。同时引入并发采集，多机房并行执行以缩短耗时。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/collectors/prometheus_range.py` | **新增** | `/api/v1/query_range` 采集、异常窗口提取、AnomalyWindow dataclass |
| `src/collectors/__init__.py` | 重写 | SiteResult 支持双模式字段；`collect_sites()` 支持 mode/period_start/period_end 参数；`ThreadPoolExecutor` 并发采集 |
| `src/config.py` | 新增 `InspectionConfig` | `step_minutes` 字段，默认 5 分钟 |
| `src/analyzer.py` | 双 payload 构建函数 | range 模式传异常窗口摘要（不传原始时序，节省 token）；instant 模式保持原格式 |
| `src/reporter.py` | 接受 period_start/end | 传入模板渲染 |
| `src/notifiers/__init__.py` | 双模式摘要 | range 模式输出异常窗口总数和峰值 |
| `templates/report.md.j2` | 完全重写 | 双模式 Jinja2 条件渲染 |
| `src/main.py` | 新增 `--period/--start/--end` | 解析时间段，传入 collect_sites + analyzer + reporter |
| `config.example.yaml` | 新增 `inspection` 节 | `step_minutes: 5` |

### 新数据模型

```
AnomalyWindow
  start_ts      ISO 时间字符串（UTC）
  end_ts        ISO 时间字符串（UTC）
  instance      节点 IP（已去除端口）
  max_value     窗口内最大值
  threshold     阈值
  unit          单位
  duration_minutes  持续时长

PromRangeResult
  name / promql / threshold / unit / anomaly_when
  period_min / period_max / period_avg   整个时段的统计值
  anomaly_windows: list[AnomalyWindow]
  is_anomaly → bool (有窗口即为 True)
```

### 异常窗口合并算法

```
对每个 instance 的时序：
  1. 筛选出所有超阈值点（violations）
  2. 相邻两点间隔 ≤ 2×step_minutes（秒）→ 合并为同一窗口
  3. 记录窗口起止时间、最大值、持续时长
```

### 并发采集

```
ThreadPoolExecutor(max_workers=min(机房数, 8))
  → 各机房 Prometheus range query + ES query 并行执行
  → 按原始 site 顺序拼装结果（保证报告顺序一致）
```

### 时间段审计报告样例

```
#### 🔴 cpu_usage

- 统计：最高 85.300% / 平均 8.123% / 最低 0.900% · 阈值 10%

🔴 异常窗口（2 段）

| 时间段 | 节点 IP | 峰值 | 阈值 | 持续时长 |
|---|---|---|---|---|
| 🔴 2026-05-01 18:03 UTC ~ 2026-05-01 19:31 UTC | 25.131.185.41 | 85.300% | 10% | 90 分钟 |
| 🔴 2026-05-01 18:07 UTC ~ 2026-05-01 19:28 UTC | 25.131.185.43 | 79.100% | 10% | 83 分钟 |
```

### 运行方式

```bash
# 快照（默认）
python -m src.main inspect

# 过去 24 小时
python -m src.main inspect --period 1d

# 过去 7 天
python -m src.main inspect --period 1w

# 自定义时间段（UTC）
python -m src.main inspect --start 2026-05-01T00:00 --end 2026-05-02T00:00
```

---

---

## Demo-6 · Web 可视化管理界面

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

所有配置写在 config.yaml，非技术用户难以维护；需要一个简洁的 Web UI 支持在线调整机房、巡检指标、触发巡检、查看报告，同时支持 HTML / Markdown 双格式报告。

### 完成内容

| 模块 | 说明 |
|---|---|
| `src/web/app.py` | FastAPI 应用，页面路由 + REST API + SSE 流式巡检输出 |
| `src/web/config_store.py` | config.yaml 读写层（CRUD for sites / prom queries / es queries / settings） |
| `src/web/static/style.css` | 纯 CSS 设计系统，无外部依赖 |
| `src/web/templates/base.html` | 侧边栏导航 + 公共 JS 工具函数 |
| `src/web/templates/index.html` | 巡检控制台：选模式/格式，SSE 实时进度，一键查看报告 |
| `src/web/templates/sites.html` | 机房增删改，Modal 表单 |
| `src/web/templates/queries.html` | PromQL 和 ES 查询管理，含描述/FAQ 编辑 |
| `src/web/templates/settings.html` | 数据源连接 / AI / 通知 / 批处理窗口，Tab 布局 |
| `src/web/templates/reports.html` | 历史报告列表，一键打开 |
| `templates/report.html.j2` | HTML 报告模板，🔴 异常窗口表、FAQ 块、完整样式 |
| `src/reporter.py` | 新增 `fmt` 参数（"md"/"html"），注入 FAQ 到结果对象 |
| `src/collectors/*.py` | `PromResult`/`PromRangeResult`/`ESResult` 均加 `faq` 字段 |
| `src/config.py` | `PromQuery`/`ESQuery` 加 `description`/`faq` 字段 |
| `src/main.py` | 新增 `web` 命令（uvicorn 启动），`inspect` 加 `--format md/html` |
| `requirements.txt` | 新增 fastapi / uvicorn[standard] / python-multipart |

### Web UI 页面结构

```
🏠 巡检控制台  → 选模式/格式 → 点「开始巡检」→ SSE 实时日志 → 报告链接
🏢 机房管理   → 机房列表 + 添加/编辑/删除（Modal）
📊 巡检指标   → Prometheus 指标 + ES 查询（Tabs），含描述/FAQ
⚙️ 系统设置   → 数据源 / AI / 通知 / 批处理窗口（Tabs）
📋 报告历史   → 报告列表 + 一键查看（HTML/MD）
```

### FAQ 机制

配置指标时填写 FAQ 字段，当该指标出现异常时，FAQ 内容自动附在报告对应位置：

```yaml
prometheus:
  queries:
    - name: cpu_usage
      faq: |
        1. 检查是否在批处理窗口（凌晨 2-4 点属正常）
        2. 执行 top -c 查看高 CPU 进程
        3. 联系 DBA 确认是否有大查询在运行
```

报告中异常项下方会显示「💡 处理建议」折叠块。

### 启动方式

```bash
pip install -r requirements.txt

# 启动 Web 界面
python -m src.main web
# → 浏览器打开 http://localhost:8000

# CLI 仍然可用
python -m src.main inspect --period 1d --format html
```

---

## Demo-7 · Web 进度可视化 + Kibana 跳转链接

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

Web 页面「开始巡检」只有滚动日志，用户无法一眼判断当前在哪个阶段；ES 日志结果需要手动去 Kibana 查询，操作繁琐。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/web/templates/index.html` | 新增 4 步进度条 | ⚙️ 加载配置 → 📡 采集数据 → 🤖 AI 分析 → 📄 生成报告，SSE 消息驱动状态切换（pending/active/done/error） |
| `src/config.py` | `ESConfig` 新增 `kibana_url` 字段 | 默认空字符串，`load_config()` 读取 `elasticsearch.kibana_url` |
| `src/collectors/elasticsearch.py` | `ESResult` 新增 `time_range_hours` 字段 | 从 `ESQuery` 传播，用于构造 Kibana 时间范围参数 |
| `src/reporter.py` | 注册 `urlencode` Jinja2 过滤器，传入 `kibana_url` | 使用 `urllib.parse.quote` 对 ES 查询字符串编码 |
| `templates/report.html.j2` | ES 块新增 Kibana 跳转链接 | `r.total > 0` 且 `kibana_url` 已配置时显示「🔗 Kibana」链接 |
| `templates/report.md.j2` | ES 命中行新增 Kibana Markdown 链接 | 格式：`[🔗 Kibana 查看](URL)` |
| `src/web/templates/settings.html` | ES 设置表单新增 Kibana 地址输入框 | 含 form-hint 说明 |
| `src/web/config_store.py` | `save_es_url()` 新增 `kibana_url` 参数 | 写入 `elasticsearch.kibana_url` |
| `src/web/app.py` | `/api/settings/elasticsearch` 新增 `kibana_url` 表单字段 | 透传至 `save_es_url()` |
| `config.example.yaml` | ES 节新增 `kibana_url` 示例 | `http://localhost:5601` |

### Kibana 跳转链接格式

```
{kibana_url}/app/discover#/?_g=(time:(from:now-{hours}h,to:now))&_a=(query:(language:lucene,query:'{url_encoded_query}'))
```

- 时间范围：取该 ES 查询配置的 `time_range_hours`
- 查询语言：Lucene（与 ES 采集一致）
- 查询字符串：`urllib.parse.quote(query, safe='')` 编码

### 4 步进度条逻辑

```
SSE 消息关键词 → 步骤映射
  "加载配置"  → step 1 active
  "采集"      → step 1 done, step 2 active
  "AI 分析"   → step 2 done, step 3 active
  "生成报告"  → step 3 done, step 4 active
  DONE:xxx    → 所有步骤 done，显示报告链接
  ERROR:xxx   → 当前步骤 error（红色）
```

---

## Demo-8 · 指标管理增强 + 报告优化

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

Web UI 需要四项增强：巡检指标导入导出全选/多选；报告自动归档天数可配置；添加指标时在线验证；报告指标表增加说明列。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/web/templates/queries.html` | 指标表头新增全选复选框，每行新增勾选列 | 导出时若有勾选项则仅导出勾选的 queries，否则导出全部 |
| `src/web/templates/queries.html` | 新增「📄 配置模板」按钮 | 下载标准格式 JSON 模板，引导用户按正确格式填写再导入 |
| `src/web/templates/queries.html` | Prom / ES 编辑 Modal 各新增「🧪 在线测试」按钮 | 调用后端测试接口，即时展示结果：Prometheus 显示时序数量+样本值，ES 显示命中总数 |
| `src/web/app.py` | 新增 `POST /api/test/prom` | 用当前配置的 Prometheus URL 执行 PromQL，返回时序数量和前 5 个样本 |
| `src/web/app.py` | 新增 `POST /api/test/es` | 用当前配置的 ES URL 执行 ES 查询，返回命中总数 |
| `src/web/app.py` | `api_report_settings()` 新增 `retention_days` 参数 | 保存至 `config.yaml` |
| `src/web/app.py` | `_list_reports()` 从 config 读 `retention_days` | 动态归档，默认 7 天 |
| `src/web/templates/reports_settings.html` | retention_days 字段改为从配置读取 | 可在 Web UI 直接调整保留天数并保存 |
| `src/config.py` | `ReportConfig` 新增 `retention_days: int = 7` | load_config 解析 `report.retention_days` |
| `src/collectors/prometheus.py` | `PromResult` 新增 `description: str = ""` | — |
| `src/collectors/prometheus_range.py` | `PromRangeResult` 新增 `description: str = ""` | — |
| `src/collectors/elasticsearch.py` | `ESResult` 新增 `description: str = ""` | — |
| `src/reporter.py` | 注入 description 到各 Result 对象 | 与 faq 注入逻辑相同，按 name 匹配 |
| `templates/report.html.j2` | Prom 快照表新增「说明」第一列；range 模式指标名右侧显示说明；ES 块显示说明 | — |
| `templates/report.md.j2` | Prom 快照表新增说明列；range 模式指标名后附说明；ES heading 后附说明 | — |

### 在线测试流程

```
用户在「添加/编辑」Modal 中填写 PromQL / ES 查询
  → 点「🧪 在线测试」
  → 前端 POST /api/test/prom 或 /api/test/es
  → 后端用 config.yaml 中的连接信息执行实际查询
  → 返回结果显示在按钮上方：
      Prom: ✅ 查询成功，共 N 个时序：instance1=0.123 | instance2=0.456
      ES:   ✅ 查询成功，命中 N 条（近 24h）
      失败: ❌ 错误信息
```

### 多选导出规则

```
Prom 表有勾选 → 仅导出勾选行的 prometheus.queries
Prom 表无勾选 → 导出全部 prometheus.queries
ES  表有勾选 → 仅导出勾选行的 elasticsearch.queries
ES  表无勾选 → 导出全部 elasticsearch.queries
机房配置按原有章节复选框控制
```

---

## Demo-9 · Web UI 全面升级（菜单重构 + 多数据源 + 多LLM + 知识库 + 通知UI）

**日期**：2026-05-02  
**状态**：✅ 完成

### 背景

原有 Web UI 菜单结构扁平、系统设置仅支持单数据源和单一 Claude 配置、通知渠道没有 UI 只能手改 yaml、巡检指标的导入/导出/模板按钮藏在页面内部难以发现。根据产品需求，对整体菜单和功能区做全面升级。

### 完成内容

| 文件 | 变更 | 说明 |
|---|---|---|
| `src/web/templates/base.html` | 侧边栏全面重构 | 巡检指标/巡检报告/项目总览均改为可折叠子菜单；`toggleMenu()` 函数控制展开收起；修复了原 `active` 变量未传导致高亮失效的 Bug |
| `src/web/static/style.css` | 新增样式 | `.menu-label`（子菜单标题）、`.kb-list/.kb-item`（知识库文件列表）、`.notifier-section`（通知配置区块）、`.md-content`（Markdown 渲染样式）、`.ds-type-prom/.ds-type-es`（数据源类型徽章） |
| `src/web/templates/queries.html` | URL 参数处理 | `window.addEventListener('load')` 检测 `?tab=es`/`?action=import|export|template` 并自动触发对应操作；移除页面内导入/导出/模板按钮（迁移至侧边栏） |
| `src/web/templates/settings.html` | 完整重写 | 删除「批处理窗口」和「导入导出」Tab；数据源连接改为多条数据源表格（带类型、增删改、导入/导出/模板）；AI分析改为多模型管理+知识库；通知改为邮件/企业微信/飞书三个实际配置区 |
| `src/web/templates/reports.html` | 精简 | 移除顶部与巡检控制台耦合的 Tab 链接，页面只展示报告历史列表 |
| `src/web/templates/project_overview.html` | 新建 | 渲染项目各类文档；前端 JS 实现简易 Markdown→HTML 转换（无外部依赖） |
| `src/web/config_store.py` | 新增 6 个函数 | `list/save/delete_datasource`、`list_llm_models/save_llm_model/delete_llm_model/set_active_llm`、`get_notifier/save_notifier` |
| `src/web/app.py` | 新增路由和 API | 见下方 API 清单；所有页面路由补传 `active`/`subtab` 变量；新增知识库目录 `_KB_DIR` 管理；新增 `_list_kb_files()` |

### 新增 API 清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/datasources` | 添加/更新数据源 |
| DELETE | `/api/datasources/{id}` | 删除数据源 |
| GET | `/api/datasources/export` | 导出数据源为 JSON |
| POST | `/api/datasources/import` | 导入数据源 JSON 数组 |
| POST | `/api/llm/models` | 添加/更新大模型配置 |
| DELETE | `/api/llm/models/{id}` | 删除大模型 |
| POST | `/api/llm/models/{id}/activate` | 设为默认模型 |
| POST | `/api/knowledge-base/upload` | 上传知识库文件（支持多文件） |
| POST | `/api/knowledge-base/update` | 替换更新知识库文件 |
| GET | `/api/knowledge-base/download/{filename}` | 下载知识库文件 |
| DELETE | `/api/knowledge-base/{filename}` | 删除知识库文件 |
| POST | `/api/notifiers` | 保存通知配置（email/wechat_work/feishu） |
| GET | `/overview/{page}` | 项目总览页（address/architecture/docs/deploy/guide/bugs） |

### 知识库设计

- 存储路径：`{项目根}/knowledge_base/`
- 支持格式：`.xlsx`、`.xls`、`.pdf`、`.md`
- 使用时机：巡检遇到日志类报错，且 `llm.active_model` 未配置或模型不可用时，自动检索知识库文档作为分析参考
- 管理方式：Web UI 上传/下载/更新/删除，无需接触文件系统

### 多数据源 vs 机房管理 的区分

| 概念 | 说明 |
|---|---|
| 机房管理（`sites`） | 逻辑机房，绑定该机房专属的 Prometheus/ES URL，是巡检的采集单元 |
| 数据源连接（`datasources`） | 命名连接池，独立管理所有 Prometheus 和 ES 连接，供机房引用或全局使用 |

两者解耦，允许多机房共用同一个数据源，也允许独立数据源不绑定机房。

### 关键设计决策

- **侧边栏「导入/导出/模板」链接采用 URL 参数跳转**（`/queries?action=import`），而非在 base.html 里硬编码 JS 函数调用，避免在非 queries 页面调用未定义函数。
- **Markdown 渲染不引入外部库**：项目 `requirements.txt` 无 `markdown` 包，前端用 20 行 JS 正则完成基础渲染，避免增加依赖；同时保留原始 `<pre>` 作为降级展示。
- **通知 `enabled` 状态用 checkbox 控制**：不强制用户删除配置来禁用通知，方便临时关闭再重开。

---

## Demo-10 · 深色主题改造 + 项目更名

**日期**：2026-05-02
**状态**：✅ 完成

### 背景

原有 Web UI 采用浅色方案，视觉风格偏传统；参照现代 SaaS Dashboard（深色 + 彩色图标卡片）进行全面改造，同时将项目正式更名为「三思GDB巡检平台」。

### 完成内容

| 模块 | 变更 | 说明 |
|---|---|---|
| `src/web/static/style.css` | **完全重写** | 深色设计系统：`--bg-app:#0d1117` / `--bg-card:#161f2e` / 主色青色 `#0dd9c4`；覆盖全部组件（按钮/表单/表格/Badge/Modal/Log/步骤条/Tab/Markdown） |
| `src/web/templates/base.html` | **完全重写** | 深色侧边栏 + 彩色 `nav-icon` 图标块（`.ni-teal/.ni-blue/.ni-purple/.ni-orange/.ni-green/.ni-cyan`）；Logo 区域青色渐变图标；系统设置升级为可折叠子菜单（数据源连接/AI分析/通知）；新增 `page_title`/`page_subtitle` block；Footer 关于作者保留 |
| `src/web/templates/index.html` | **完全重写** | 8 格统计卡片仪表盘（第一行：机房/Prometheus/ES查询/报告；第二行：数据源/AI模型/知识库/系统就绪）；每格含彩色图标块 + 大数字 + 副标题；按钮状态优化（巡检中禁用+文字变更） |
| `src/web/templates/*.html` (6个) | 移除 `<h1 class="page-title">` | 改用 `{% block page_title %}` + `{% block page_subtitle %}`，由 base.html 统一渲染页头 |
| `src/web/app.py` | 小更新 | FastAPI 标题改为「三思GDB巡检平台」；`page_index` 注入 `_kb_count` 用于仪表盘知识库卡片 |

### 设计令牌（CSS 变量）

```
--bg-app:       #0d1117   主背景
--bg-sidebar:   #111827   侧边栏
--bg-card:      #161f2e   卡片背景
--bg-input:     #1e2d3d   输入框背景
--teal:         #0dd9c4   主色（青色）
--green:        #22c55e   成功色
--blue:         #3b82f6   信息色
--purple:       #a855f7   紫色
--orange:       #f59e0b   警告色
--red:          #ef4444   错误色
```

### 关键设计决策

- **CSS 变量 + 语义化颜色类**：`sv-teal/sv-green/sv-warn/sv-ok` 等，统计卡片数值颜色由数据动态决定（无数据→橙色警告，有数据→对应主题色）
- **系统就绪状态**：前端 JS 动态计算（机房数>0 且 Prometheus指标数>0 → 绿色「就绪」，否则橙色「待配置」），无需后端参与
- **暗色 Modal 遮罩**：`backdrop-filter: blur(3px)`，现代感背景虚化

---

## Demo-11 · GDB 组件专项监控（v1.5.0 Phase 1）

**日期**：2026-05-03
**状态**：✅ 完成

### 背景

GoldenDB 生产环境的 Prometheus exporter 已暴露 OMM/MDS/CM/PM/GTM/DBProxy/RDB/Backup 8 大组件的专项指标，但原有 `config.example.yaml` 未覆盖。本 Demo 以**零代码改动**方式补全这部分监控覆盖。

### 完成内容

| 文件 | 变更 | 说明 |
|---|---|---|
| `config.example.yaml` | 追加 12 条 PromQL + 增强 2 条 | 覆盖 GDB 8 大组件；新增 `component` / `severity` / `description` / `faq` 字段 |
| `CHANGELOG.md` | 新增 v1.5.0 条目 | - |

### 新增指标分组

**A — 组件存活**（severity: critical）：`gdb_omm_up` / `gdb_mds_up` / `gdb_cm_up` / `gdb_pm_up` / `gdb_dbproxy_up`

**B — 复制延迟 & 副本健康**（severity: critical/warning）：`gdb_gtm_replication_lag_sec` / `gdb_pm_replica_factor` / `gdb_rdb_sync_lag_sec`

**C — DBProxy 性能 & 备份**（severity: warning）：`gdb_dbproxy_conn_pool_usage` / `gdb_dbproxy_slow_query_rate` / `gdb_dbproxy_error_rate` / `gdb_backup_process_running`

### 关键设计决策

- 存活类指标使用 `anomaly_when: lt`，防止 exporter 无数据时误报，PromQL 使用 `min(...) or vector(0)` 兜底
- 连接池使用率用比值（`max(...active/.../max_connections)`），比绝对数更稳定
- 所有指标预置 `component` / `severity` 字段，为 Phase 2（报告分组）做数据准备，Phase 1 升级配置不改代码

---

## 待开发（下一步）

| 优先级 | 内容 |
|---|---|
| P1 | **v1.5.0 Phase 2**：PromQuery 加 component/severity 字段 + 报告按组件分组 |
| P1 | **v1.5.0 Phase 3**：表规模监控（pymysql 采集器 + Web UI 配置） |
| P1 | **v1.5.0 Phase 4**：APScheduler 定时巡检 + Web UI 任务管理页 |
| P3 | 历史趋势对比：与上次报告 diff，标出新增/已恢复异常 |
| P3 | 知识库检索集成：巡检分析时自动向量检索知识库（当前仅存储，未接入检索） |
