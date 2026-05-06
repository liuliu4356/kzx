# 三思GDB巡检平台 - 功能更新说明

## 更新日期：2026-05-05

### 1. 修复Bug

#### 1.1 修复巡检控制台访问错误
- **问题**：访问 `/console` 路由时返回 Internal Server Error
- **原因**：缺少 `/console` 路由定义
- **修复**：在 `src/web/routes.py` 中添加了 `/console` 路由，映射到巡检控制台页面（与首页相同）

#### 1.2 修复定时任务页面访问错误
- **问题**：访问 `/cron` 路由时返回 404 Not Found
- **原因**：缺少 `/cron` 路由定义
- **修复**：在 `src/web/routes.py` 中添加了 `/cron` 路由，显示定时任务管理页面

### 2. Elasticsearch/Kibana 认证支持

#### 2.1 配置说明
在 `config.yaml` 和 `config.example.yaml` 中添加了 Kibana 认证配置：

```yaml
elasticsearch:
  url: http://localhost:9200
  username_env: ES_USERNAME          # ES 认证用户名环境变量
  password_env: ES_PASSWORD          # ES 认证密码环境变量
  kibana_url: http://localhost:5601  # Kibana 地址（可选）
  kibana_username_env: KIBANA_USERNAME  # Kibana 认证用户名（可选）
  kibana_password_env: KIBANA_PASSWORD  # Kibana 认证密码（可选）
  timeout_sec: 10
```

#### 2.2 使用方法
1. **无需认证**：不设置 `kibana_username_env` 和 `kibana_password_env`
2. **需要认证**：
   - 在环境变量中设置 Kibana 用户名和密码
   - 例如：`export KIBANA_USERNAME=admin`，`export KIBANA_PASSWORD=password`

### 3. Web 服务器 IP 配置

#### 3.1 配置说明
在 `config.yaml` 和 `config.example.yaml` 中添加了 Web 服务器配置：

```yaml
web:
  host: 127.0.0.1  # 监听地址：127.0.0.1（本机）/ 0.0.0.0（所有网卡）/ 指定IP
  port: 8000       # 监听端口，默认 8000
```

#### 3.2 启动方式
1. **使用配置文件**：`python -m src.main web`（从 config.yaml 读取配置）
2. **命令行覆盖**：
   - `python -m src.main web --host 0.0.0.0 --port 8080`
   - `python -m src.main web --host 192.168.1.100`

#### 3.3 默认行为
- 如果 `config.yaml` 中未配置 `web` 部分，默认使用 `127.0.0.1:8000`
- 命令行参数优先级高于配置文件

### 4. 多角色权限系统

#### 4.1 角色定义

| 角色 | 标识 | 权限说明 |
|------|------|----------|
| **管理员** | `admin` | 拥有所有权限：查看、执行巡检、修改配置、管理用户 |
| **操作员** | `operator` | 可以执行巡检、修改配置，但不能管理用户 |
| **普通用户** | `user` | 可以执行巡检、查看报告，但不能修改配置 |
| **只读用户** | `viewer` | 只能查看报告和配置，不能执行任何操作 |

#### 4.2 权限矩阵

| 功能 | admin | operator | user | viewer |
|------|-------|----------|------|--------|
| 查看报告和配置 | ✅ | ✅ | ✅ | ✅ |
| 执行巡检 | ✅ | ✅ | ✅ | ❌ |
| 修改配置（机房、指标、定时任务等） | ✅ | ✅ | ❌ | ❌ |
| 管理用户（添加、删除、改密） | ✅ | ❌ | ❌ | ❌ |

#### 4.3 使用说明

1. **首次使用**：
   - 首次访问 Web UI 时，系统会引导创建管理员账户
   - 默认用户名/密码：`admin/admin`（建议首次登录后修改）

2. **添加用户**：
   - 管理员登录后，访问「用户管理」页面
   - 点击「添加用户」，选择角色并设置密码
   - 支持的角色：admin、operator、user、viewer

3. **权限控制**：
   - 页面按钮会根据用户权限自动显示/隐藏
   - 无权限的操作会显示为禁用状态或提示"权限不足"
   - API 端点会验证用户权限，未授权请求返回 403 错误

#### 4.4 技术实现

- **认证方式**：基于 Session 的服务端认证
- **密码存储**：PBKDF2-HMAC-SHA256 (200,000 轮) 哈希
- **会话有效期**：7 天（可在代码中配置）
- **用户数据**：存储在 `users.json` 文件中

### 5. 文件变更清单

#### 5.1 新增文件
- `UPDATES.md` - 本更新说明文档

#### 5.2 修改文件
- `src/main.py` - 添加 Web 服务器 IP/端口配置读取
- `src/web/routes.py` - 添加 `/console` 和 `/cron` 路由
- `src/web/auth.py` - 扩展角色系统，添加权限检查函数
- `src/web/helpers.py` - 添加权限信息传递到模板
- `src/web/api.py` - 添加关键 API 端点的权限检查
- `src/web/auth_routes.py` - 支持创建不同角色的用户
- `src/web/templates/register.html` - 添加角色选择下拉框
- `src/web/templates/users.html` - 显示所有角色类型
- `src/web/templates/index.html` - 根据权限显示/隐藏按钮
- `src/web/templates/cron.html` - 根据权限控制操作按钮
- `config.yaml` - 添加 Kibana 认证和 Web 服务器配置
- `config.example.yaml` - 添加配置示例和说明

### 6. 测试验证

#### 6.1 路由测试
```bash
# 验证路由已注册
python -c "from src.web.routes import router; print([r.path for r in router.routes])"
# 输出应包含：/, /console, /cron, /sites, /queries, /settings, /reports, /overview, /overview/{page}
```

#### 6.2 角色测试
```bash
# 验证角色定义
python -c "from src.web import auth; print(list(auth.ROLES.keys()))"
# 输出：['admin', 'operator', 'user', 'viewer']
```

#### 6.3 Web 服务器测试
```bash
# 使用默认配置启动
python -m src.main web

# 使用自定义配置启动
python -m src.main web --host 0.0.0.0 --port 8080
```

### 7. 升级指南

#### 7.1 从旧版本升级

1. **备份数据**：
   ```bash
   cp config.yaml config.yaml.bak
   cp users.json users.json.bak
   ```

2. **更新配置文件**：
   - 在 `config.yaml` 中添加 `web` 配置段（参考 `config.example.yaml`）
   - 在 `elasticsearch` 配置中添加 Kibana 认证配置（可选）

3. **更新用户角色**：
   - 现有用户默认保持原有角色（admin 或 viewer）
   - 可以通过「用户管理」页面修改用户角色（需要管理员权限）

4. **重启服务**：
   ```bash
   python -m src.main web
   ```

#### 7.2 注意事项

- 默认 Web 监听地址从 `0.0.0.0` 改为 `127.0.0.1`，如需外部访问请修改配置
- 新增的权限检查可能影响现有 API 调用，请确保调用方有足够权限
- 建议首次升级后修改默认管理员密码

### 8. 常见问题

#### Q1: 访问 /console 或 /cron 仍然报错？
**A**: 请确保已重启 Web 服务器，并清除浏览器缓存。

#### Q2: 如何修改默认监听地址？
**A**: 在 `config.yaml` 中修改 `web.host` 配置，或使用命令行参数 `--host`。

#### Q3: 如何给现有用户分配新角色？
**A**: 目前需要删除用户后重新创建。后续版本会添加角色修改功能。

#### Q4: Kibana 认证配置是必须的吗？
**A**: 不是必须的。如果 Kibana 不需要认证，可以不配置这两个环境变量。

#### Q5: 不同角色的用户看到的页面有什么区别？
**A**: 
- **viewer**：所有操作按钮都是禁用或隐藏的
- **user**：可以执行巡检，但不能修改配置
- **operator**：可以执行巡检和修改配置，但不能管理用户
- **admin**：拥有所有权限

### 9. 后续计划

- [ ] 添加用户角色在线修改功能
- [ ] 添加操作日志审计功能
- [ ] 支持 LDAP/AD 集成
- [ ] 添加 API Token 认证方式
- [ ] 支持更细粒度的权限控制

---

**更新人员**：Claude (Anthropic)  
**版本**：v1.4.0  
**更新时间**：2026-05-05
