"""页面路由（/, /sites, /queries, /settings, /reports, /overview/*）"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .helpers import render_template, _list_reports, _list_kb_files, _get_current_user, _PROJ_ROOT, _KB_DIR
from . import config_store as cs
from . import auth as _auth

router = APIRouter()


# ── 页面路由 ───────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    raw = cs.get_all()
    reports = _list_reports()[:10]
    kb_count = len(_list_kb_files()) if _KB_DIR.exists() else 0
    raw["_kb_count"] = kb_count
    return render_template("index.html", {"raw": raw, "reports": reports, "active": "home"}, request)


@router.get("/sites", response_class=HTMLResponse)
async def page_sites(request: Request):
    sites = cs.list_sites()
    return render_template("sites.html", {"sites": sites, "active": "sites"}, request)


@router.get("/queries", response_class=HTMLResponse)
async def page_queries(request: Request):
    raw = cs._load_raw()
    prom_queries = raw.get("prometheus", {}).get("queries", [])
    es_queries = raw.get("elasticsearch", {}).get("queries", [])
    sites = raw.get("sites") or raw.get("datacenters", [])
    export_data = json.dumps({
        "prometheus": raw.get("prometheus", {}),
        "elasticsearch": raw.get("elasticsearch", {}),
        "sites": sites,
    }, ensure_ascii=False)
    tab = request.query_params.get("tab", "")
    subtab = "es" if tab == "es" else ("io" if tab == "io" else "prom")
    user = _auth.get_current_user(request)
    is_admin = _auth.has_permission(user, "can_edit") if user else False
    return render_template("queries.html", {
        "prom_queries": prom_queries,
        "es_queries": es_queries,
        "sites": sites,
        "export_data_json": export_data,
        "active": "queries",
        "subtab": subtab,
        "is_admin": is_admin,
    }, request)


@router.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    raw = cs.get_all()
    kb_files = _list_kb_files()
    tab = request.query_params.get("tab", "conn")
    return render_template("settings.html", {"raw": raw, "kb_files": kb_files, "active": "settings", "subtab": tab}, request)


@router.get("/reports", response_class=HTMLResponse)
async def page_reports(request: Request):
    reports = _list_reports()
    return render_template("reports.html", {"reports": reports, "active": "reports", "subtab": ""}, request)


@router.get("/reports/settings", response_class=HTMLResponse)
async def page_reports_settings(request: Request):
    raw = cs.get_all()
    return render_template("reports_settings.html", {"raw": raw, "active": "reports", "subtab": "settings"}, request)


@router.get("/console", response_class=HTMLResponse)
async def page_console(request: Request):
    """巡检控制台页面（与首页相同）"""
    raw = cs.get_all()
    reports = _list_reports()[:10]
    kb_count = len(_list_kb_files()) if _KB_DIR.exists() else 0
    raw["_kb_count"] = kb_count
    return render_template("index.html", {"raw": raw, "reports": reports, "active": "home"}, request)


@router.get("/cron", response_class=HTMLResponse)
async def page_cron(request: Request):
    """定时任务页面"""
    from .app import _scheduler
    jobs = cs.list_cron_jobs()
    next_runs: dict[str, str] = {}
    if _scheduler:
        for j in _scheduler.get_jobs():
            nrt = j.next_run_time
            next_runs[j.id] = nrt.isoformat() if nrt else None
    return render_template("cron.html", {"jobs": jobs, "next_runs": next_runs, "active": "cron"}, request)


# ── 项目总览路由 ───────────────────────────────────────────────

_OVERVIEW_PAGES = {
    "address": {
        "title": "项目地址",
        "files": [_PROJ_ROOT / "README.md"],
        "extra_links": [
            {"url": "https://github.com/liuliu4356/kzx", "label": "GitHub 仓库", "desc": "源代码托管", "external": True},
        ],
    },
    "architecture": {
        "title": "项目架构",
        "files": [_PROJ_ROOT / "docs" / "X项目监控系统产品手册.md", _PROJ_ROOT / "README.md"],
        "section_hint": "architecture",
    },
    "docs": {
        "title": "项目文档索引",
        "files": [_PROJ_ROOT / "docs" / "00-文档索引" / "README.md"],
        "extra_links": [
            {"url": "/overview/deploy", "label": "项目部署文档", "desc": "生产/测试环境部署", "external": False},
            {"url": "/overview/kylin-deploy", "label": "麒麟系统部署指南", "desc": "国产麒麟系统服务部署", "external": False},
            {"url": "/overview/guide", "label": "小白操作手册", "desc": "零基础快速入门", "external": False},
            {"url": "/overview/bugs", "label": "Bug修复记录", "desc": "版本更新日志", "external": False},
            {"url": "/overview/notify", "label": "通知配置文档", "desc": "钉钉/飞书/企业微信配置", "external": False},
        ],
    },
    "deploy": {
        "title": "项目部署文档",
        "files": [
            _PROJ_ROOT / "docs" / "01-部署文档" / "01-生产环境部署指南.md",
            _PROJ_ROOT / "docs" / "01-部署文档" / "02-测试环境搭建指南.md",
            _PROJ_ROOT / "测试环境搭建指南.md",
        ],
    },
    "kylin": {
        "title": "麒麟系统本地部署与实战使用手册",
        "files": [_PROJ_ROOT / "docs" / "01-部署文档" / "04-麒麟系统本地部署与实战使用手册.md"],
    },
    "physical": {
        "title": "物理机安装指南（无 Docker 环境）",
        "files": [_PROJ_ROOT / "docs" / "01-部署文档" / "03-物理机安装指南.md"],
    },
    "guide": {
        "title": "小白操作手册",
        "files": [
            _PROJ_ROOT / "docs" / "02-小白文档" / "小白操作手册.md",
            _PROJ_ROOT / "小白操作手册.md",
        ],
    },
    "faq": {
        "title": "常见问题解答 (FAQ)",
        "files": [_PROJ_ROOT / "docs" / "03-FAQ文档" / "常见问题解答.md"],
    },
    "devguide": {
        "title": "开发者指南",
        "files": [_PROJ_ROOT / "docs" / "04-开发文档" / "项目开发指南.md"],
    },
    "bugs": {
        "title": "Bug修复记录",
        "files": [_PROJ_ROOT / "CHANGELOG.md"],
    },
    "kylin-deploy": {
        "title": "麒麟系统服务部署指南",
        "files": [_PROJ_ROOT / "docs" / "麒麟系统部署指南.md"],
    },
    "manual": {
        "title": "产品手册",
        "files": [_PROJ_ROOT / "docs" / "X项目监控系统产品手册.md"],
    },
    "product": {
        "title": "项目介绍",
        "files": [],
        "content": """
<h2>三思GDB巡检平台 v1.10.0</h2>
<p>面向GoldenDB数据库分布式集群的自动化巡检工具。</p>

<h3>核心功能</h3>
<ul>
<li>多机房Prometheus/ES数据源采集</li>
<li>AI智能分析异常指标</li>
<li>自动化报告生成</li>
<li>多渠道告警通知</li>
</ul>

<h3>技术栈</h3>
<ul>
<li>Python 3.10+ / FastAPI</li>
<li>Prometheus / ELK</li>
<li>Anthropic Claude API</li>
<li>Jinja2 模板</li>
</ul>

<h3>版本</h3>
<p>当前版本: <strong>v1.10.0</strong> (2026-05-06)</p>
""",
    },
    "notify": {
        "title": "通知配置文档",
        "files": [],
        "content": """
<div class="card" style="max-width:800px;margin-bottom:1.5rem">
<h3>📧 邮件通知配置</h3>
<p>SMTP服务器: smtp.qq.com 或 smtp.163.com</p>
<p>端口: 465(SSL) 或 25</p>
<p>QQ邮箱需开启IMAP/SMTP，获取授权码作为密码</p>
</div>

<div class="card" style="max-width:800px;margin-bottom:1.5rem">
<h3>💬 钉钉通知配置</h3>
<ol><li>打开电脑版钉钉 → 进入群设置 → 智能群助手</li>
<li>点击添加机器人 → 选择自定义</li>
<li>设置机器人名称 → 添加 → 复制Webhook地址</li>
<li>格式: https://oapi.dingtalk.com/robot/send?access_token=xxx</li></ol>
</div>

<div class="card" style="max-width:800px;margin-bottom:1.5rem">
<h3>💬 企业微信通知配置</h3>
<ol><li>打开企业微信 → 进入群设置 → 群机器人</li>
<li>点击添加机器人 → 设置名称</li>
<li>复制Webhook地址</li>
<li>格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx</li></ol>
</div>

<div class="card" style="max-width:800px;margin-bottom:1.5rem">
<h3>🚀 飞书通知配置</h3>
<ol><li>打开飞书 → 进入群设置 → 群机器人</li>
<li>点击添加机器人 → 选择自定义</li>
<li>设置名称 → 复制Webhook地址</li>
<li>格式: https://open.feishu.cn/open-apis/bot/v2/hook/xxx</li></ol>
</div>

<div class="card" style="max-width:800px">
<h3>🔗 配置步骤</h3>
<ol><li>进入系统设置 → 通知</li>
<li>找到对应的通知渠道</li>
<li>启用开关</li>
<li>粘贴Webhook URL</li>
<li>点击保存</li></ol>
</div>
""",
    },
}


@router.get("/overview", response_class=HTMLResponse)
async def page_overview_root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/overview/address")


@router.get("/overview/{page}", response_class=HTMLResponse)
async def page_overview(page: str, request: Request):
    cfg = _OVERVIEW_PAGES.get(page)
    if not cfg:
        raise HTTPException(404, "页面不存在")
    content_raw = cfg.get("content", "")
    if not content_raw:
        for fp in cfg.get("files", []):
            if fp.exists():
                try:
                    content_raw = fp.read_text(encoding="utf-8")
                except Exception:
                    try:
                        content_raw = fp.read_text(encoding="gbk")
                    except Exception:
                        pass
                if content_raw:
                    break
    return render_template("project_overview.html", {
        "page_title": cfg["title"],
        "content_raw": content_raw,
        "content_html": "",
        "extra_links": cfg.get("extra_links", []),
        "empty_msg": "文档文件不存在或无法读取",
        "active": "overview",
        "subtab": page,
    }, request)
