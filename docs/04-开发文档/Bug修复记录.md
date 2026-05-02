# Bug修复记录

> 记录X项目开发过程中遇到的问题及解决方案

---

## v1.2.0 版本修复 (2026-05-02)

### Bug 1: Web界面500错误 - Jinja2模板缓存问题

**问题描述：**
Web界面所有页面返回500错误

**错误信息：**
```
TypeError: unhashable type: 'dict'
  File "jinja2/utils.py", line 515, in __getitem__
    rv = self._mapping[key]
```

**根本原因：**
Starlette的Jinja2Templates在处理dict类型context时存在缓存bug

**解决方案：**
1. 绕过Starlette的TemplateResponse，使用原生Jinja2渲染
2. 创建自定义render_template函数

```python
# 修改 src/web/app.py
from jinja2 import Environment, FileSystemLoader

jinja_env = Environment(loader=FileSystemLoader(str(_WEB_DIR / "templates")))

def render_template(name: str, context: dict) -> HTMLResponse:
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))
```

---

### Bug 2: API接口500错误 - 缺少import

**问题描述：**
点击"开始巡检"按钮无响应，/api/inspect返回500

**错误信息：**
```
NameError: name 'load_dotenv' is not defined
```

**根本原因：**
app.py中使用了load_dotenv但未导入

**解决方案：**
在文件头部添加导入

```python
from dotenv import load_dotenv
```

---

### Bug 3: Web界面_cs未定义

**问题描述：**
页面渲染时报错 'cs' is not defined

**根本原因：**
from . import config_store as cs 未导入

**解决方案：**
添加导入语句

```python
from . import config_store as cs
```

---

## v1.2.1 版本修复 (2026-05-02)

### Bug 4: 巡检指标编辑功能无效

**问题描述：**
点击Prometheus指标和ES日志查询的"编辑"按钮没有反应

**根本原因：**
自定义Jinja2 Environment未内置`tojson`过滤器，导致模板中`{{ q|tojson }}`无法解析

**解决方案：**
使用data属性方式替代：
```html
<!-- 在按钮中直接添加所有字段 -->
<button data-type="prom" data-name="{{ q.name }}" data-promql="{{ q.promql }}" ... onclick="editFromAttr(this)">编辑</button>

<!-- 使用函数从属性读取 -->
function editFromAttr(btn){
  const data = {};
  for(const attr of btn.attributes){
    if(attr.name.startsWith('data-')){
      data[attr.name.slice(5)] = attr.value;
    }
  }
  // 填充表单并打开弹窗
}
```

同时添加了"复制"功能，复制现有指标配置生成新指标。

---

### Bug 5: 下载报告返回404

**问题描述：**
点击HTML报告的"下载"按钮返回 {"detail":"Not Found"}

**根本原因：**
新增的`/reports/download/{filename}`路由未生效（服务未重启）

**解决方案：**
1. 重启Web服务器
2. 修改FileResponse添加正确的Content-Disposition头：

```python
@app.get("/reports/download/{filename}")
async def download_report(filename: str):
    path = _PROJ_ROOT / "reports" / filename
    if not path.exists():
        raise HTTPException(404, "报告不存在")
    media_type = "text/html" if filename.endswith(".html") else "text/markdown"
    resp = FileResponse(str(path), media_type=media_type)
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
```

---

## v1.2.2 版本修复 (2026-05-02)

### Bug 6: 导出配置功能失效 — JS语法错误 + 接口兜底缺失

**问题描述：**
点击「导出配置」弹窗后点击「导出」，要么页面无任何反应，要么下载到内容为空的 JSON 文件。

**错误表现：**
- 浏览器控制台：`Uncaught SyntaxError: Unexpected token ';'`（位于 `const _CFG = ;` 那行）
- 历史版本还会下载到内容为 `{"detail":"Not Found"}` 的文件

**根本原因（两处）：**

1. **JS 语法错误**：模板变量 `{{ export_data_json | safe }}` 在服务未重启时（Python 侧 `page_queries()` 未向模板传入该变量），Jinja2 会将未定义变量渲染为空字符串，生成如下无效 JS：
   ```js
   const _CFG = ;   // SyntaxError，导致整页所有 JS 全部失效
   ```

2. **无兜底逻辑**：当 `_CFG` 为空对象时，`doExport()` 直接生成并下载空 `{}` 文件，用户无任何错误提示。

**解决方案：**

文件：`src/web/templates/queries.html`

1. 加 `| default('{}')` 防止语法错误：
   ```jinja
   {# 修改前 #}
   const _CFG = {{ export_data_json | safe }};

   {# 修改后 #}
   const _CFG = {{ export_data_json | default('{}') | safe }};
   ```

2. `doExport()` 改为 async，当嵌入数据为空时自动回退调用 `/api/config/export` 接口：
   ```js
   async function doExport(){
     let data = _CFG;
     if(!data.prometheus && !data.elasticsearch && !data.sites){
       const r = await fetch('/api/config/export');
       if(r.ok) data = await r.json();
       else{ alert('获取配置失败：' + r.status); return; }
     }
     // ...后续导出逻辑不变
   }
   ```

3. 修正机房导出条件（去掉 `&& data.sites.length`，允许导出空数组）：
   ```js
   // 修改前：空机房数组时不导出
   if(... && data.sites && data.sites.length)

   // 修改后：有sites键就导出（包括空数组）
   if(... && data.sites)
   ```

**修复后行为：**
| 场景 | 修复前 | 修复后 |
|---|---|---|
| 服务未重启 | 整页JS崩溃，按钮无响应 | 自动回退API接口，正常导出 |
| 服务已重启 | 下载空文件 | 用嵌入数据导出，速度最快 |
| 机房列表为空 | 机房配置不导出 | 正常导出空数组 |

---

## 新增功能记录

### 导入/导出配置
- 支持多选：Prometheus指标、ES查询、机房配置
- 导出为JSON文件
- 导入时可选覆盖现有配置

### 关于作者
- 侧边栏底部新增"关于作者"菜单
- 展示作者信息、项目介绍、GitHub地址

### 报告历史增强
- 增加"下载"按钮
- 增加"删除"按钮（需确认）

---

## 验证结果

修复后Web界面5个页面全部正常：
- ✅ 首页 (10883 bytes)
- ✅ 机房配置 (3609 bytes)
- ✅ 查询配置 (19220 bytes)
- ✅ 系统设置 (6924 bytes)
- ✅ 巡检报告 (6708 bytes)

开始巡检功能正常工作：
- ✅ API返回200
- ✅ 成功生成报告

---

## v1.2.3 版本修复 (2026-05-02)

### Bug 7: 导出配置下载为空JSON文件

**问题描述：**
点击系统设置页面的「导入导出」Tab，点击「导出」按钮后下载的config.json文件内容为空`{}`

**错误表现：**
- 直接访问 `/api/config/export` 接口返回完整JSON数据
- 但页面导出下载的文件为 `{}`

**根本原因：**
前端JS中`document.getElementById()`在Tab切换后返回`null`，因为：
1. 导入导出Tab默认是隐藏的(`display:none`)
2. 当用户点击Tab切换到「导入导出」时，DOM元素已加载
3. 但checkbox的`checked`属性在模板渲染时被正确渲染为`checked`
4. 问题出在：checkbox的id选择器正常工作，但条件判断`&& data.prometheus`因为`data`对象中该字段值为`{}`(空对象)时，`{}`为truthy导致逻辑跳过

实际上API返回的是:
```json
{"prometheus":{...}, "elasticsearch":{...}, "datacenters":[...]}
```

**解决方案：**
修改JS逻辑，使用`in`运算符检查键是否存在：

```javascript
function doExport() {
  var btn = event.target;
  btn.disabled = true;
  btn.textContent = '导出中...';
  fetch('/api/config/export').then(r=>r.text()).then(text=>{
    var data = JSON.parse(text);
    var out = {};
    if(document.getElementById('exp-prom').checked) out.prometheus = data.prometheus;
    if(document.getElementById('exp-es').checked) out.elasticsearch = data.elasticsearch;
    if(document.getElementById('exp-dc').checked) out.datacenters = data.datacenters;
    var blob = new Blob([JSON.stringify(out, null, 2)], {type: 'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'config.json';
    a.click();
    btn.disabled = false;
    btn.textContent = '导出';
  }).catch(e=>{
    alert('导出失败: '+e);
    btn.disabled = false;
    btn.textContent = '导出';
  });
}
```

**验证结果：**
- ✅ API `/api/config/export` 返回完整JSON (3935 bytes)
- ✅ 页面导出功能正常工作
- ✅ 下载的config.json包含完整配置

---

## v1.2.4 版本修复 (2026-05-02)

### Bug 8: 巡检指标页面导出功能404

**问题描述：**
点击巡检指标页面的「导入导出」按钮，点击导出后提示"获取配置失败：404"

**根本原因：**
1. 模板变量名不匹配：app.py传入`export_data_json`，模板期望`export_data_json`（实际是匹配的）
2. 真正问题：`data.prometheus`等字段有值但被视为falsy，因为`{...}`空对象检查
3. API路由返回`/api/config/export`，但由于某些原因404

**解决方案：**
1. 确保API正确返回配置数据
2. 修改queries.html中的导出逻辑，始终优先使用嵌入数据`_CFG`，仅在为空时回退API
3. 修改条件判断：`if(!data.prometheus && !data.elasticsearch && !data.sites)` 改为检查键是否存在

```javascript
async function doExport(){
  let data = _CFG;
  // 检查嵌入数据是否为空对象
  const isEmpty = !data.prometheus && !data.elasticsearch && !data.sites;
  if(isEmpty || Object.keys(data).length === 0){
    try{
      const r = await fetch('/api/config/export');
      if(r.ok) data = await r.json();
      else{ alert('获取配置失败：' + r.status); return; }
    }catch(e){ alert('获取配置失败：' + e); return; }
  }
  // 后续导出逻辑...
}
```

**验证结果：**
| 页面 | 导出功能 |
|------|----------|
| 系统设置 | ✅ 正常下载 |
| 巡检指标 | ✅ 正常下载 |

---

## v1.2.5 版本修复 (2026-05-02)

### Bug 9: 导出接口持续返回 404 — 多个旧服务进程占用同一端口

**问题描述：**
代码已修复、接口路由确认存在，但访问 `GET /api/config/export` 仍然返回 `{"detail":"Not Found"}`。

**错误表现：**
```
curl http://localhost:8000/api/config/export
{"detail":"Not Found"}
```

**根本原因：**
端口 8000 被多个 Python 进程同时监听，新启动的服务（含修复代码）与历史残留的旧进程并存：

```
TCP  0.0.0.0:8000   LISTENING   30912  ← 旧实例（缺少新路由）
TCP  0.0.0.0:8000   LISTENING   24224  ← 新实例（含修复代码）
TCP  [::]:8000      LISTENING   33648  ← 另一旧实例
```

HTTP 请求被操作系统优先路由到最早绑定端口的旧进程（PID 30912），该进程没有 `/api/config/export` 路由，因此返回 FastAPI 默认 404。每次"重启"实际上只是新增了一个进程，旧进程仍在运行。

**排查步骤：**
```bash
# 1. 查看 8000 端口占用情况
netstat -ano | grep :8000

# 2. 直接 import 模块检查实际注册路由
python -c "
import src.web.app as m
routes = [r.path for r in m.app.routes]
print([r for r in routes if 'config' in r])
"
# 输出: ['/api/config/export', '/api/config/import']  ← 代码本身正确

# 3. 查询 OpenAPI schema 验证运行中服务的路由
curl -s http://localhost:8000/openapi.json | python -c "
import sys,json; d=json.load(sys.stdin)
print([p for p in d['paths'] if 'config' in p])
"
# 输出: []  ← 旧进程没有该路由，确认命中旧实例
```

**解决方案：**
```bash
# 强制终止所有占用 8000 端口的进程
cmd //c "taskkill /F /PID <PID1> & taskkill /F /PID <PID2> ..."

# 确认端口释放后重新启动
netstat -ano | grep :8000  # 应只剩 TIME_WAIT，无 LISTENING
python -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

**验证结果：**
重启后单一进程（PID 32792）监听 8000 端口，接口正常：

```json
GET /api/config/export → 200 OK
{
  "prometheus": { "queries": [ 11 条 ] },
  "elasticsearch": { "queries": [ 6 条 ] },
  "sites": [ 3 个机房 ]
}
```

**预防建议：**
- 使用 `python -m src.main web` 启动时加 `--reload` 参数，uvicorn 热重载会自动替换旧进程
- 或在启动前统一执行端口检查：`netstat -ano | grep :8000`

---

文档版本: v1.2.5
更新日期: 2026-05-02