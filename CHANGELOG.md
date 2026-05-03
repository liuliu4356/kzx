# 三思GDB巡检平台 更新日志

> 遵循语义化版本规范 (Semantic Versioning)

---

## v1.5.0 (2026-05-03) - GDB 组件专项监控

### 新增监控指标（config.example.yaml）

**GDB 组件存活监控（OMM / MDS / CM / PM / DBProxy）**
- ✅ `gdb_omm_up` — OMM 主控节点存活状态，含 FAQ 排查指引
- ✅ `gdb_mds_up` — MDS 元数据服务存活状态
- ✅ `gdb_cm_up` — CM 集群管理服务存活状态
- ✅ `gdb_pm_up` — PM 分区管理服务存活状态
- ✅ `gdb_dbproxy_up` — DBProxy 数据库代理存活状态

**GTM 主备延迟 & 副本健康**
- ✅ `gdb_gtm_replication_lag_sec` — GTM 主备延迟（期望 <5s）
- ✅ `gdb_pm_replica_factor` — 各分区最小副本数（期望 ≥ 3）
- ✅ `gdb_rdb_sync_lag_sec` — RDB 节点间同步延迟（期望 <10s）

**DBProxy 性能 & 备份进程**
- ✅ `gdb_dbproxy_conn_pool_usage` — 连接池使用率（期望 <80%）
- ✅ `gdb_dbproxy_slow_query_rate` — 慢查询速率（期望 <10 q/s）
- ✅ `gdb_dbproxy_error_rate` — 每秒错误数（期望 <1 err/s）
- ✅ `gdb_backup_process_running` — arm_backup_mysql 备份进程存活

**已有指标增强**
- ✅ `instance_up` / `emergency_alerts` 补充 `component: system` 和 `severity: critical` 字段
- ✅ 所有新指标带 `component` / `severity` / `description` / `faq` 字段，为 Phase 2 报告分组做准备

### 配置说明
- 新指标均依赖 GDB Prometheus exporter（v1.5.0+），字段格式详见 `config.example.yaml`
- `anomaly_when: lt` 用于存活类指标（值低于阈值才告警）

---

## v1.4.0 (2026-05-02) - 深色主题改造 + 项目更名

### 项目更名
- ✅ **项目正式更名为「三思GDB巡检平台」**，全站标题、FastAPI 应用名、Logo 均同步更新

### UI 全面深色化改造（参照现代 SaaS Dashboard 风格）
- ✅ **style.css 完全重写** — 深色设计系统，主色调青色 `#0dd9c4`，背景 `#0d1117`，卡片 `#161f2e`
- ✅ **侧边栏重设计** — 深海军蓝背景，每个菜单项配独立彩色图标块（青/蓝/紫/橙/绿），Logo 区域青色渐变图标
- ✅ **系统设置菜单展开为子菜单**，含「数据源连接 / AI分析 / 通知」三个子项，与巡检指标/巡检报告风格统一
- ✅ **巡检控制台全面升级为 Dashboard 风格**
  - 第一行 4 张统计卡片：已配置机房 / Prometheus指标 / ES日志查询 / 历史报告
  - 第二行 4 张统计卡片：数据源连接 / AI模型 / 知识库文件 / 系统就绪状态（动态计算）
  - 每张卡片含彩色图标块 + 大数字 + 状态副标题
- ✅ **全站各页面统一 page-header 区域**，含页面标题 + 副标题说明
- ✅ **各模板新增 `page_title` / `page_subtitle` 块**，不再在 content 内重复渲染 `<h1>`
- ✅ **表格、按钮、表单、Modal、Badge 全部暗色化**

### 后端小更新
- ✅ `page_index` 路由新增 `_kb_count`（知识库文件数）传入模板，用于仪表盘统计卡片
- ✅ FastAPI 应用标题改为「三思GDB巡检平台」

### 新配置字段
无新增配置字段，本版本为纯 UI 改造。

---

## v1.3.0 (2026-05-02) - Web UI 全面升级

### 菜单结构重构
- ✅ **巡检指标** 升级为可折叠子菜单，含 Prometheus指标配置、ES日志查询配置、导入配置、导出配置、配置模板下载 5 个子项
- ✅ **巡检报告** 保持子菜单（历史 + 设置），修复了 `active` 变量未传导致菜单高亮失效的 Bug
- ✅ **新增「项目总览」菜单**，含 6 个子项：项目地址、项目架构、项目文档索引、项目部署文档、小白操作手册、Bug修复并记录；自动渲染对应 Markdown 文档

### 系统设置升级
- ✅ **数据源连接** — 支持多条数据源（Prometheus / Elasticsearch），表格展示，可添加/编辑/删除，支持导出/导入/配置模板下载
- ✅ **AI 分析** — 多大模型管理（支持 Anthropic Claude、OpenAI 兼容内网接口等），可配置多个并设置默认；新增**知识库**（上传 Excel/PDF/Markdown，无大模型时自动用于日志分析）
- ✅ **通知** — 实现完整 UI：邮件（SMTP）、企业微信（Webhook）、飞书（Webhook + 签名密钥）
- ✅ **删除** 批处理窗口 Tab 和导入导出 Tab（功能迁移至对应子菜单）

### 巡检报告优化
- ✅ 报告历史页面移除了顶部指向巡检控制台的 Tab 链接，页面仅展示纯粹的历史报告列表

### 后端新增 API
- ✅ `GET/POST/DELETE /api/datasources` — 多数据源 CRUD
- ✅ `GET /api/datasources/export`、`POST /api/datasources/import` — 数据源导出/导入
- ✅ `POST/DELETE /api/llm/models` — 大模型 CRUD
- ✅ `POST /api/llm/models/{id}/activate` — 设置默认模型
- ✅ `POST /api/knowledge-base/upload`、`/update`、`GET .../download/{filename}`、`DELETE .../{filename}` — 知识库文件管理
- ✅ `POST /api/notifiers` — 保存邮件/企业微信/飞书通知配置
- ✅ `GET /overview/{page}` — 项目总览页（自动读取并渲染 Markdown 文档）

### 新增配置字段（config.yaml）
```yaml
datasources:          # 多数据源列表（新增）
  - id: prom-main
    type: prometheus
    name: 主机房-Prometheus
    url: http://10.0.0.1:9090
    timeout_sec: 10

llm:
  active_model: claude-main  # 默认模型（新增）
  models:                     # 多模型列表（新增）
    - id: claude-main
      name: Claude Sonnet
      provider: anthropic
      model: claude-sonnet-4-6
      api_key_env: ANTHROPIC_API_KEY
    - id: internal-qwen
      name: 内网 Qwen
      provider: openai_compatible
      api_base: http://10.0.0.1:8080/v1

notifiers:            # 完整通知配置（扩展）
  - type: email
    enabled: true
    smtp_host: smtp.example.com
    smtp_port: 465
    smtp_ssl: true
    sender: noreply@example.com
    recipients: [admin@example.com]
  - type: wechat_work
    enabled: false
    webhook_url: https://qyapi.weixin.qq.com/...
  - type: feishu
    enabled: false
    webhook_url: https://open.feishu.cn/...
```

---

## v1.0.0 (2026-05-02) - 初始版本

### 新增功能
- ✅ 基础 Prometheus + ELK 监控架构
- ✅ Prometheus 指标采集 (CPU/内存/磁盘/网络)
- ✅ Elasticsearch 日志收集与分析
- ✅ Grafana 可视化面板
- ✅ AI 分析功能 (Claude integration)
- ✅ 自动报告生成 (Markdown格式)
- ✅ 多通知渠道 (钉钉/飞书)
- ✅ 容器化部署 (Docker Compose)
- ✅ 自动同步到 GitHub

### 支持的服务
- Prometheus (9090)
- Node Exporter (9100)
- Alertmanager (9093)
- Grafana (3000)
- Elasticsearch (9200)
- Kibana (5601)
- Logstash (9600, 8080, 5044)
- Filebeat
- MySQL + Exporter
- PostgreSQL + Exporter
- Redis + Exporter
- Nginx + Exporter

---

## v1.1.0 (2026-05-02) - 多机房支持版本

### 新增功能
- ✅ **多机房架构支持**
  - 北京东坝机房 (主数据中心)
  - 北京南法信机房
  - 合肥机房 (灾备)
- ✅ **按机房分组的巡检报告**
- ✅ **多维度指标配置**
  - 系统资源指标 (CPU/内存/负载/网络/磁盘IO)
  - 数据库性能指标 (连接数/QPS/TPS)
  - 存储与表规模指标

### 监控指标更新 (按生产巡检标准)
| 指标 | 旧阈值 | 新阈值 | 说明 |
|------|--------|--------|------|
| CPU使用率 | 80% | 10% | 生产标准 <10%, 日增幅<1% |
| 内存使用率 | 85% | 60% | 生产标准 <60%, 日增幅<1% |
| 磁盘使用率 | 90% | 80% | 生产标准 <80%, 日增幅<1% |
| 系统负载 | - | <32 | 针对64核服务器 |
| 网络流量 | - | <100Mb/s | 带宽25Gb/s |
| RDB连接数 | - | <6K | 上限10k |
| QPS | - | <2k | |
| TPS | - | <100 | |

### 新增配置
- `datacenters` 配置项 - 定义多机房信息
- `datacenter_filter: true` - 按机房分组
- 告警规则配置
- 日志级别分类 (ERROR/FATAL/WARN/Slow Query)

### 文档更新
- ✅ README.md 完整项目文档
- ✅ 测试环境搭建指南 (Windows/Linux/云服务器)
- ✅ 项目使用说明 (小白入门)
- ✅ CHANGELOG.md 版本更新日志

### 脚本更新
- ✅ auto_push.py - GitHub 自动同步
- ✅ update_doc.py - 文档自动更新

---

## v1.2.0 (2026-05-02) - 功能验证与文档完善

### 新增功能
- ✅ **模拟异常指标系统**
  - mock-metrics 模拟服务
  - 支持CPU/内存/磁盘/网络异常模拟
  - 支持MySQL连接数异常
  - 支持实例宕机(up=0)模拟

- ✅ **ES日志异常模拟**
  - 支持ERROR/FATAL日志模拟
  - 支持WARN/WARNING日志模拟
  - 支持Slow Query日志模拟
  - 支持Connection Lost日志模拟
  - 支持Lock Wait Timeout日志模拟

- ✅ **巡检系统验证**
  - Prometheus指标采集验证 (11个指标)
  - 异常阈值检测验证 (2个异常检测成功)
  - ES日志采集验证 (6种日志类型)
  - 报告生成验证 (Markdown格式)

### Bug修复
- ✅ 修复Prometheus采集器标量返回处理
- ✅ 修复ES日志@timestamp字段缺失问题

### 文档更新
- ✅ 完整使用文档 (小白版)
  - 项目概述与技术架构
  - 生产环境部署步骤 (单节点/集群)
  - 功能验证指南 (7个模块)
  - 物理机模拟测试方法 (麒麟系统)
  - 配置详解 (含HTTPS)
  - 常见问题排查 (8大场景)
  - 维护与更新指南

### 生产部署调整清单
| 调整项 | 说明 |
|--------|------|
| Prometheus地址 | 改为实际IP |
| Elasticsearch地址 | 改为实际IP |
| 数据持久化 | 配置卷挂载 |
| 资源限制 | 设置CPU/内存限制 |
| 防火墙 | 开放必要端口 |
| 安全加固 | 配置HTTPS/用户权限 |

### 测试环境验证结果
```
Prometheus指标: 11个指标, 2个异常
  - mysql_connections: 7200 > 6000 (异常)
  - instance_up: 0 < 1 (异常)

ES日志: 6种类型, 17条ERROR
  - ERROR/FATAL: 7条
  - WARN/WARNING: 2条
  - Slow Query: 2条
  - Connection Lost: 3条
  - Lock Wait Timeout: 3条
```

---

## v1.5.0 (计划中) - GoldenDB 深度集成

### 计划功能
- [ ] GoldenDB 组件专用监控
  - OMM/RDB/MDS/CM/PM 状态检查
  - GTM 主备延迟监控
  - DBProxy 慢日志统计
- [ ] 表规模监控 (记录数/大小)
- [ ] 备份进程检测 (arm_backup_mysql)
- [ ] 多机房可视化大屏
- [ ] 定时任务配置（Web UI 配置 cron 巡检计划）
- [ ] 知识库检索集成（向量检索，接入巡检分析流程）

---

## 版本号规则

```
v主版本.次版本.修订号

- 主版本: 重大架构变更
- 次版本: 新功能添加
- 修订号: bug修复和优化
```

---

## 历史版本

| 版本 | 日期 | 提交 | 说明 |
|------|------|------|------|
| v1.0.0 | 2026-05-02 | 5167d36 | 初始版本 |
| v1.1.0 | 2026-05-02 | fc8958f | 多机房支持 |
| v1.2.0 | 2026-05-02 | —      | 功能验证与文档完善 |
| v1.3.0 | 2026-05-02 | —      | Web UI 全面升级（多数据源/多LLM/知识库/通知UI） |
| v1.4.0 | 2026-05-02 | —      | 深色主题改造 + 项目更名「三思GDB巡检平台」 |

---

*项目：三思GDB巡检平台*