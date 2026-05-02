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

文档版本: v1.2.0
更新日期: 2026-05-02