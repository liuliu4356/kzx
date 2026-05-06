# 三思GDB巡检平台 更新日志

> 遵循语义化版本规范 (Semantic Versioning)

---

## v2.0.0 (2026-05-06) - 离线部署 / 响应式UI / 备份恢复

### 新增功能

#### 1. 离线部署支持
- **完整离线部署包**：包含 Miniconda3 Python 3.10、所有 Python 依赖包、项目源码
- **离线包目录**：`offline_x/` 目录（145MB）
- **部署脚本**：`deploy.sh` 脚本，支持一键离线部署

#### 2. 响应式UI适配
- **全局响应式**：适配桌面端、平板端、手机端
- **移动端汉堡菜单**：768px 以下自动显示汉堡菜单按钮
- **侧边栏动画**：侧边栏抽屉式展开/收起
- **表单适配**：登录、注册页面响应式优化
- **按钮/表格**：手机端自动调整padding和字号

#### 3. 账号管理
- **左侧菜单**：新增"账号管理"菜单，包含用户列表、注册新用户、注销登录
- **管理员标识**：右下角显示当前用户名和管理员badge
- **GET /logout**：支持GET方式访问注销页面（之前仅支持POST）

#### 4. 备份恢复功能
- **自动备份**：每次修改配置前自动创建备份
- **备份列表**：查看所有历史备份
- **一键恢复**：选择备份文件恢复配置
- **备份删除**：删除不需要的备份文件
- **备份位置**：`backups/config_YYYYMMDD_HHMMSS.yaml`

#### 5. 服务管理脚本
- **上传并重启**：`upload_restart.py` - 上传修改的代码并重启服务
- **服务管理**：`manage_x.py` - 支持 start/stop/restart/status 命令

### Bug 修复

#### 1. 定时任务
- **apscheduler未安装**：安装 apscheduler 包
- **时区错误**：安装 tzlocal 包，修复 `'No time zone found with key local'` 错误
- **全局_scheduler变量**：修复 lifespan 中局部变量无法导出到其他模块的问题

#### 2. 用户页面
- **current_user类型错误**：修复 `'str' object has no attribute 'get'` 错误
- **模板变量传递**：修复 auth_routes.py 中 current_user 传递问题

#### 3. 登录注册
- **GET /logout**：添加 GET 请求处理，支持页面链接直接注销
- **登录页面样式**：PC端和移动端样式优化

### 代码修改列表

| 文件 | 修改内容 |
|------|---------|
| `src/web/app.py` | 添加全局 `_scheduler` 变量，lifespan 修复 |
| `src/web/auth_routes.py` | 修复 current_user 传递，添加 GET /logout |
| `src/web/config_store.py` | 添加备份/恢复功能 |
| `src/web/api.py` | 添加 `/api/backups` 相关API |
| `src/web/helpers.py` | 修复 is_admin 判断逻辑 |
| `src/web/static/style.css` | 添加响应式CSS媒体查询 |
| `src/web/templates/base.html` | 添加账号管理菜单，汉堡菜单按钮 |
| `src/web/templates/login.html` | 响应式样式优化 |
| `src/web/templates/register.html` | 响应式样式优化 |
| `src/web/templates/sites.html` | 添加备份恢复按钮和Modal |
| `src/web/templates/queries.html` | 添加备份恢复按钮和Modal |

### 部署信息

| 服务 | 地址 |
|------|------|
| Prometheus | http://192.168.187.201:19090 |
| Grafana | http://192.168.187.201:3000 |
| Elasticsearch | http://192.168.187.202:9200 |
| Kibana | http://192.168.187.202:5601 |
| X项目 | http://192.168.187.203:8000 |

---

## v1.9.0 (2026-05-06) - 离线部署 / 权限加固 / 内网访问

（见上一版本记录）

---

## 更新日志格式

```
## vX.Y.Z (YYYY-MM-DD) - 更新摘要

### 新增功能
- 功能1说明
- 功能2说明

### Bug 修复
- 修复1说明
- 修复2说明

### 代码修改列表
| 文件 | 修改内容 |
|------|---------|
| path/file.py | 修改说明 |
```
