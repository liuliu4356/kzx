from __future__ import annotations

import queue
import threading
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import config_store as cs
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import json

_WEB_DIR = Path(__file__).parent
_PROJ_ROOT = _WEB_DIR.parent.parent
_KB_DIR = _PROJ_ROOT / "knowledge_base"
_CONFIG_PATH = str(_PROJ_ROOT / "config.yaml")

_scheduler = None

app = FastAPI(title="三思GDB巡检平台")


@app.on_event("startup")
async def _startup():
    global _scheduler
    try:
        from ..scheduler import setup_scheduler
        if Path(_CONFIG_PATH).exists():
            _scheduler = setup_scheduler(_CONFIG_PATH)
            if _scheduler:
                _scheduler.start()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("定时任务启动失败: %s", exc)


@app.on_event("shutdown")
async def _shutdown():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")

jinja_env = Environment(loader=FileSystemLoader(str(_WEB_DIR / "templates")))

def render_template(name: str, context: dict) -> HTMLResponse:
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))


# ── 页面路由 ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    raw = cs.get_all()
    reports = _list_reports()[:10]
    kb_count = len(_list_kb_files()) if _KB_DIR.exists() else 0
    raw["_kb_count"] = kb_count
    return render_template("index.html", {"raw": raw, "reports": reports, "active": "home"})


@app.get("/sites", response_class=HTMLResponse)
async def page_sites(request: Request):
    sites = cs.list_sites()
    return render_template("sites.html", {"sites": sites, "active": "sites"})


@app.get("/queries", response_class=HTMLResponse)
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
    subtab = "es" if tab == "es" else ""
    return render_template("queries.html", {
        "prom_queries": prom_queries,
        "es_queries": es_queries,
        "export_data_json": export_data,
        "active": "queries",
        "subtab": subtab,
    })


@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    raw = cs.get_all()
    kb_files = _list_kb_files()
    return render_template("settings.html", {"raw": raw, "kb_files": kb_files, "active": "settings"})


@app.get("/reports", response_class=HTMLResponse)
async def page_reports(request: Request):
    reports = _list_reports()
    return render_template("reports.html", {"reports": reports, "active": "reports", "subtab": ""})


@app.get("/reports/settings", response_class=HTMLResponse)
async def page_reports_settings(request: Request):
    raw = cs.get_all()
    return render_template("reports_settings.html", {"raw": raw, "active": "reports", "subtab": "settings"})


# ── 项目总览路由 ───────────────────────────────────────────────────────────

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
            {"url": "/overview/guide", "label": "小白操作手册", "desc": "零基础快速入门", "external": False},
            {"url": "/overview/bugs", "label": "Bug修复记录", "desc": "版本更新日志", "external": False},
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
        "title": "Bug修复并记录",
        "files": [_PROJ_ROOT / "CHANGELOG.md", _PROJ_ROOT / "DEVLOG.md"],
    },
}


@app.get("/overview", response_class=HTMLResponse)
async def page_overview_root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/overview/address")


@app.get("/overview/{page}", response_class=HTMLResponse)
async def page_overview(page: str):
    cfg = _OVERVIEW_PAGES.get(page)
    if not cfg:
        raise HTTPException(404, "页面不存在")
    content_raw = ""
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
    })


# ── API: Sites ─────────────────────────────────────────────────────────────

@app.post("/api/sites")
async def api_save_site(
    label: str = Form(...),
    prometheus_url: str = Form(...),
    es_url: str = Form(""),
):
    cs.save_site({"label": label, "prometheus_url": prometheus_url,
                  "es_url": es_url or None})
    return JSONResponse({"ok": True})


@app.delete("/api/sites/{label}")
async def api_delete_site(label: str):
    ok = cs.delete_site(label)
    if not ok:
        raise HTTPException(404, "机房不存在")
    return JSONResponse({"ok": True})


# ── API: Prometheus queries ────────────────────────────────────────────────

@app.post("/api/queries/prom")
async def api_save_prom(
    name: str = Form(...),
    promql: str = Form(...),
    threshold: float = Form(...),
    unit: str = Form(""),
    anomaly_when: str = Form("gt"),
    description: str = Form(""),
    faq: str = Form(""),
):
    cs.save_prom_query({
        "name": name, "promql": promql, "threshold": threshold,
        "unit": unit, "anomaly_when": anomaly_when,
        "description": description, "faq": faq,
    })
    return JSONResponse({"ok": True})


@app.delete("/api/queries/prom/{name}")
async def api_delete_prom(name: str):
    ok = cs.delete_prom_query(name)
    if not ok:
        raise HTTPException(404, "指标不存在")
    return JSONResponse({"ok": True})


# ── API: ES queries ────────────────────────────────────────────────────────

@app.post("/api/queries/es")
async def api_save_es(
    name: str = Form(...),
    index: str = Form(...),
    query_string: str = Form(...),
    time_range_hours: int = Form(24),
    size: int = Form(50),
    ignorable: str = Form("false"),
    description: str = Form(""),
    faq: str = Form(""),
):
    cs.save_es_query({
        "name": name, "index": index, "query_string": query_string,
        "time_range_hours": time_range_hours, "size": size,
        "ignorable": ignorable.lower() == "true",
        "description": description, "faq": faq,
    })
    return JSONResponse({"ok": True})


@app.delete("/api/queries/es/{name}")
async def api_delete_es(name: str):
    ok = cs.delete_es_query(name)
    if not ok:
        raise HTTPException(404, "查询不存在")
    return JSONResponse({"ok": True})


# ── API: Import/Export ────────────────────────────────────────────────────

@app.get("/api/config/export")
async def api_export():
    raw = cs._load_raw()
    return JSONResponse({
        "prometheus": raw.get("prometheus", {}),
        "elasticsearch": raw.get("elasticsearch", {}),
        "sites": raw.get("sites") or raw.get("datacenters", []),
    })


@app.post("/api/config/import")
async def api_import(request: Request):
    body = await request.json()
    data = body.get("data", {})
    raw = cs._load_raw()
    if body.get("prom") and "prometheus" in data:
        raw["prometheus"] = data["prometheus"]
    if body.get("es") and "elasticsearch" in data:
        raw["elasticsearch"] = data["elasticsearch"]
    if body.get("sites"):
        sites = data.get("sites") or data.get("datacenters")
        if sites is not None:
            raw["sites"] = sites
    cs._save_raw(raw)
    return JSONResponse({"ok": True})


# ── API: Datasources ───────────────────────────────────────────────────────

@app.post("/api/datasources")
async def api_save_datasource(
    id: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    url: str = Form(...),
    timeout_sec: int = Form(10),
    username_env: str = Form(""),
    password_env: str = Form(""),
):
    ds: dict = {"id": id, "name": name, "type": type, "url": url, "timeout_sec": timeout_sec}
    if type == "elasticsearch":
        ds["username_env"] = username_env
        ds["password_env"] = password_env
    cs.save_datasource(ds)
    return JSONResponse({"ok": True})


@app.delete("/api/datasources/{ds_id}")
async def api_delete_datasource(ds_id: str):
    ok = cs.delete_datasource(ds_id)
    if not ok:
        raise HTTPException(404, "数据源不存在")
    return JSONResponse({"ok": True})


@app.get("/api/datasources/export")
async def api_export_datasources():
    return JSONResponse(cs.list_datasources())


@app.post("/api/datasources/import")
async def api_import_datasources(request: Request):
    data = await request.json()
    if not isinstance(data, list):
        raise HTTPException(400, "期望 JSON 数组格式")
    raw = cs._load_raw()
    raw["datasources"] = data
    cs._save_raw(raw)
    return JSONResponse({"ok": True})


# ── API: LLM Models ────────────────────────────────────────────────────────

@app.post("/api/llm/models")
async def api_save_llm_model(
    id: str = Form(...),
    name: str = Form(...),
    provider: str = Form("anthropic"),
    model: str = Form(...),
    api_key_env: str = Form(""),
    api_base: str = Form(""),
    max_tokens: int = Form(2048),
):
    cs.save_llm_model({
        "id": id, "name": name, "provider": provider, "model": model,
        "api_key_env": api_key_env, "api_base": api_base or "",
        "max_tokens": max_tokens,
    })
    return JSONResponse({"ok": True})


@app.delete("/api/llm/models/{model_id}")
async def api_delete_llm_model(model_id: str):
    ok = cs.delete_llm_model(model_id)
    if not ok:
        raise HTTPException(404, "模型不存在")
    return JSONResponse({"ok": True})


@app.post("/api/llm/models/{model_id}/activate")
async def api_activate_llm(model_id: str):
    cs.set_active_llm(model_id)
    return JSONResponse({"ok": True})


# ── API: Knowledge Base ────────────────────────────────────────────────────

@app.post("/api/knowledge-base/upload")
async def api_kb_upload(files: list[UploadFile] = File(...)):
    _KB_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        suffix = Path(f.filename).suffix.lower()
        if suffix not in (".xlsx", ".xls", ".pdf", ".md"):
            raise HTTPException(400, f"不支持的文件格式: {suffix}")
        dest = _KB_DIR / f.filename
        content = await f.read()
        dest.write_bytes(content)
        saved.append(f.filename)
    return JSONResponse({"ok": True, "saved": saved})


@app.post("/api/knowledge-base/update")
async def api_kb_update(file: UploadFile = File(...), replace: str = Form("")):
    _KB_DIR.mkdir(parents=True, exist_ok=True)
    target_name = replace if replace else file.filename
    dest = _KB_DIR / target_name
    content = await file.read()
    dest.write_bytes(content)
    return JSONResponse({"ok": True})


@app.get("/api/knowledge-base/download/{filename}")
async def api_kb_download(filename: str):
    path = _KB_DIR / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(path), filename=filename)


@app.delete("/api/knowledge-base/{filename}")
async def api_kb_delete(filename: str):
    path = _KB_DIR / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    path.unlink()
    return JSONResponse({"ok": True})


# ── API: Notifiers ─────────────────────────────────────────────────────────

@app.post("/api/notifiers")
async def api_save_notifier(request: Request):
    fd = await request.form()
    ntype = fd.get("type", "")
    enabled = fd.get("enabled", "false") == "true"
    notifier: dict = {"type": ntype, "enabled": enabled}

    if ntype == "email":
        recipients_raw = fd.get("recipients", "")
        recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        notifier.update({
            "smtp_host": fd.get("smtp_host", ""),
            "smtp_port": int(fd.get("smtp_port", 465)),
            "smtp_ssl": "smtp_ssl" in fd,
            "sender": fd.get("sender", ""),
            "sender_name": fd.get("sender_name", "GDB巡检系统"),
            "recipients": recipients,
            "username_env": fd.get("username_env", ""),
            "password_env": fd.get("password_env", ""),
        })
    elif ntype == "wechat_work":
        mentioned_raw = fd.get("mentioned_list", "")
        mentioned = [m.strip() for m in mentioned_raw.split(",") if m.strip()]
        notifier.update({
            "webhook_url": fd.get("webhook_url", ""),
            "mentioned_list": mentioned,
        })
    elif ntype == "feishu":
        notifier.update({
            "webhook_url": fd.get("webhook_url", ""),
            "secret_env": fd.get("secret_env", ""),
        })

    cs.save_notifier(notifier)
    return JSONResponse({"ok": True})


# ── API: Settings ──────────────────────────────────────────────────────────

@app.post("/api/settings/prometheus")
async def api_prom_settings(
    url: str = Form(...),
    timeout_sec: int = Form(10),
):
    cs.save_prometheus_url(url, timeout_sec)
    return JSONResponse({"ok": True})


@app.post("/api/settings/elasticsearch")
async def api_es_settings(
    url: str = Form(...),
    username_env: str = Form(""),
    password_env: str = Form(""),
    timeout_sec: int = Form(10),
    kibana_url: str = Form(""),
):
    cs.save_es_url(url, username_env, password_env, timeout_sec, kibana_url)
    return JSONResponse({"ok": True})


@app.post("/api/settings/report")
async def api_report_settings(
    output_dir: str = Form("reports"),
    language: str = Form("zh-CN"),
    retention_days: int = Form(7),
):
    cs.save_settings("report", {"output_dir": output_dir, "language": language,
                                "filename_format": "%Y-%m-%d-%H%M",
                                "retention_days": retention_days})
    return JSONResponse({"ok": True})


# ── API: 在线测试指标 ──────────────────────────────────────────────────────

@app.post("/api/test/prom")
async def api_test_prom(promql: str = Form(...)):
    import httpx as _httpx
    try:
        raw = cs._load_raw()
        prom_url = raw.get("prometheus", {}).get("url", "http://localhost:9090")
        timeout = int(raw.get("prometheus", {}).get("timeout_sec", 10))
        with _httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{prom_url.rstrip('/')}/api/v1/query",
                              params={"query": promql})
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != "success":
            return JSONResponse({"ok": False, "error": data.get("error", "未知错误")})
        results = data.get("data", {}).get("result", [])
        samples = []
        for r in results[:5]:
            if isinstance(r, dict) and "value" in r:
                inst = r.get("metric", {}).get("instance", "")
                samples.append({"instance": inst, "value": r["value"][1]})
        return JSONResponse({"ok": True, "count": len(results), "samples": samples})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


@app.post("/api/test/es")
async def api_test_es(
    index: str = Form(...),
    query_string: str = Form(...),
    time_range_hours: int = Form(24),
):
    import httpx as _httpx, os as _os
    from datetime import timedelta as _td
    try:
        raw = cs._load_raw()
        es_cfg = raw.get("elasticsearch", {})
        es_url = es_cfg.get("url", "http://localhost:9200")
        timeout = int(es_cfg.get("timeout_sec", 10))
        uenv = es_cfg.get("username_env") or ""
        penv = es_cfg.get("password_env") or ""
        user = _os.environ.get(uenv) if uenv else None
        pw = _os.environ.get(penv) if penv else None
        auth = (user, pw) if user and pw else None
        since = (datetime.now(timezone.utc) - _td(hours=time_range_hours)).isoformat()
        body = {"size": 0, "query": {"bool": {"must": [
            {"query_string": {"query": query_string}},
            {"range": {"@timestamp": {"gte": since}}},
        ]}}}
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{es_url.rstrip('/')}/{index}/_search",
                               json=body, auth=auth)
            resp.raise_for_status()
            data = resp.json()
        total_obj = data.get("hits", {}).get("total", 0)
        total = total_obj["value"] if isinstance(total_obj, dict) else int(total_obj)
        return JSONResponse({"ok": True, "total": total})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


# ── Cron page ─────────────────────────────────────────────────────────────

@app.get("/cron", response_class=HTMLResponse)
async def page_cron(request: Request):
    jobs = cs.list_cron_jobs()
    # 注入 next_run_time
    next_runs: dict[str, str] = {}
    if _scheduler:
        for j in _scheduler.get_jobs():
            nrt = j.next_run_time
            next_runs[j.id] = nrt.strftime("%Y-%m-%d %H:%M") if nrt else "—"
    return render_template("cron.html", {"jobs": jobs, "next_runs": next_runs, "active": "cron"})


# ── API: Cron Jobs ─────────────────────────────────────────────────────────

@app.get("/api/cron")
async def api_list_cron():
    jobs = cs.list_cron_jobs()
    next_runs: dict[str, str] = {}
    if _scheduler:
        for j in _scheduler.get_jobs():
            nrt = j.next_run_time
            next_runs[j.id] = nrt.isoformat() if nrt else None
    return JSONResponse({"jobs": jobs, "next_runs": next_runs})


@app.post("/api/cron")
async def api_save_cron(
    id: str = Form(...),
    label: str = Form(...),
    cron_expr: str = Form(...),
    mode: str = Form("instant"),
    period_hours: int = Form(24),
    fmt: str = Form("html"),
    notify: str = Form("true"),
    enabled: str = Form("true"),
):
    job = {
        "id": id, "label": label, "cron_expr": cron_expr,
        "mode": mode, "period_hours": period_hours, "fmt": fmt,
        "notify": notify.lower() == "true",
        "enabled": enabled.lower() == "true",
    }
    cs.save_cron_job(job)
    if _scheduler:
        from ..scheduler import reload_jobs
        reload_jobs(_scheduler, _CONFIG_PATH)
    return JSONResponse({"ok": True})


@app.delete("/api/cron/{job_id}")
async def api_delete_cron(job_id: str):
    ok = cs.delete_cron_job(job_id)
    if not ok:
        raise HTTPException(404, "任务不存在")
    if _scheduler:
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass
    return JSONResponse({"ok": True})


@app.post("/api/cron/{job_id}/run-now")
async def api_cron_run_now(job_id: str):
    jobs = cs.list_cron_jobs()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job:
        raise HTTPException(404, "任务不存在")
    import threading
    from ..scheduler import _run_inspection
    threading.Thread(
        target=_run_inspection, args=[_CONFIG_PATH, job_id], daemon=True
    ).start()
    return JSONResponse({"ok": True, "msg": f"任务 {job.get('label', job_id)} 已触发"})


@app.post("/api/cron/{job_id}/toggle")
async def api_cron_toggle(job_id: str, enabled: str = Form(...)):
    ok = cs.toggle_cron_job(job_id, enabled.lower() == "true")
    if not ok:
        raise HTTPException(404, "任务不存在")
    if _scheduler:
        from ..scheduler import reload_jobs
        reload_jobs(_scheduler, _CONFIG_PATH)
    return JSONResponse({"ok": True})


# ── API: Table Monitor ────────────────────────────────────────────────────

@app.get("/api/table-monitor")
async def api_get_table_monitor():
    return JSONResponse(cs.get_table_monitor())


@app.post("/api/table-monitor/settings")
async def api_save_table_monitor_settings(
    enabled: str = Form("false"),
    host: str = Form(""),
    port: int = Form(3306),
    user: str = Form(""),
    password_env: str = Form("GDB_MONITOR_DB_PASS"),
    timeout_sec: int = Form(10),
):
    cs.save_table_monitor_settings({
        "enabled": enabled.lower() == "true",
        "host": host, "port": port, "user": user,
        "password_env": password_env, "timeout_sec": timeout_sec,
    })
    return JSONResponse({"ok": True})


@app.post("/api/table-monitor/queries")
async def api_save_table_query(
    name: str = Form(...),
    database: str = Form(...),
    table: str = Form(...),
    size_threshold_gb: float = Form(100.0),
    row_threshold: int = Form(0),
    description: str = Form(""),
    faq: str = Form(""),
):
    cs.save_table_query({
        "name": name, "database": database, "table": table,
        "size_threshold_gb": size_threshold_gb, "row_threshold": row_threshold,
        "description": description, "faq": faq,
    })
    return JSONResponse({"ok": True})


@app.delete("/api/table-monitor/queries/{name}")
async def api_delete_table_query(name: str):
    ok = cs.delete_table_query(name)
    if not ok:
        raise HTTPException(404, "监控表不存在")
    return JSONResponse({"ok": True})


@app.post("/api/test/table")
async def api_test_table(
    host: str = Form(""),
    port: int = Form(3306),
    user: str = Form(""),
    password_env: str = Form("GDB_MONITOR_DB_PASS"),
):
    import os as _os
    password = _os.environ.get(password_env, "")
    try:
        import pymysql
        conn = pymysql.connect(
            host=host or "localhost", port=port, user=user, password=password,
            database="information_schema", connect_timeout=5, charset="utf8mb4",
        )
        conn.close()
        return JSONResponse({"ok": True, "msg": "连接成功"})
    except ImportError:
        return JSONResponse({"ok": False, "error": "pymysql 未安装"})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})


# ── API: 触发巡检（SSE 流式输出）─────────────────────────────────────────

@app.post("/api/inspect")
async def api_inspect(
    period: str = Form("instant"),
    start: str = Form(""),
    end: str = Form(""),
    skip_llm: str = Form("false"),
    fmt: str = Form("html"),
):
    load_dotenv()

    def _run(q: queue.Queue):
        try:
            from ..config import load_config, current_batch_window
            from ..collectors import collect_sites
            from ..analyzer import analyze
            from .. import reporter

            def emit(msg: str):
                q.put(f"data: {msg}\n\n")

            emit("⏳ 加载配置...")
            cfg = load_config("config.yaml")

            mode = "instant"
            period_start = period_end = None
            if start and end:
                fmt_str = "%Y-%m-%dT%H:%M"
                period_start = datetime.strptime(start, fmt_str).replace(tzinfo=timezone.utc)
                period_end = datetime.strptime(end, fmt_str).replace(tzinfo=timezone.utc)
                mode = "range"
            elif period == "1d":
                period_end = datetime.now(timezone.utc)
                period_start = period_end - timedelta(days=1)
                mode = "range"
            elif period == "1w":
                period_end = datetime.now(timezone.utc)
                period_start = period_end - timedelta(days=7)
                mode = "range"

            batch_win = current_batch_window(cfg.batch_windows)
            if batch_win:
                emit(f"⚠️ 当前处于批处理窗口：{batch_win.label}")

            emit(f"📡 采集各机房数据（{mode} 模式）...")
            site_results = collect_sites(cfg, mode=mode,
                                         period_start=period_start,
                                         period_end=period_end)
            for s in site_results:
                emit(f"  ✅ {s.label}：{s.anomaly_count} 项异常")

            if skip_llm.lower() == "true":
                emit("⏭️ 跳过 AI 分析")
                ai_analysis = "_已跳过 AI 分析。_"
            else:
                emit("🤖 AI 分析中...")
                ai_analysis = analyze(site_results, cfg.llm, batch_win,
                                      period_start, period_end)
                emit("  ✅ AI 分析完成")

            emit("📄 生成报告...")
            out_path = reporter.render(site_results, ai_analysis, cfg,
                                       period_start, period_end, fmt=fmt)
            emit(f"DONE:{out_path.name}")
        except Exception as exc:
            q.put(f"data: ERROR:{exc}\n\n")
        finally:
            q.put(None)

    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run, args=(q,), daemon=True).start()

    def event_stream():
        while True:
            item = q.get()
            if item is None:
                break
            yield item

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── API: Reports ───────────────────────────────────────────────────────────

@app.get("/api/reports")
async def api_list_reports():
    return JSONResponse({"reports": _list_reports()})


@app.get("/reports/view/{filename}")
async def view_report(filename: str):
    path = _PROJ_ROOT / "reports" / filename
    if not path.exists():
        raise HTTPException(404, "报告不存在")
    if filename.endswith(".html"):
        return FileResponse(str(path), media_type="text/html")
    content = path.read_text(encoding="utf-8")
    return HTMLResponse(f"<pre style='font-family:monospace;padding:2rem'>{content}</pre>")


@app.get("/reports/download/{filename}")
async def download_report(filename: str):
    path = _PROJ_ROOT / "reports" / filename
    if not path.exists():
        return JSONResponse({"error": f"not found: {path}"}, status_code=404)
    media_type = "text/html" if filename.endswith(".html") else "text/markdown"
    resp = FileResponse(str(path), media_type=media_type)
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    path = _PROJ_ROOT / "reports" / filename
    if not path.exists():
        raise HTTPException(404, "报告不存在")
    path.unlink()
    return JSONResponse({"ok": True})


# ── 内部辅助 ───────────────────────────────────────────────────────────────

def _list_reports() -> list[dict]:
    try:
        days = int(cs._load_raw().get("report", {}).get("retention_days", 7))
    except Exception:
        days = 7
    _clean_old_reports(days)
    reports_dir = _PROJ_ROOT / "reports"
    if not reports_dir.exists():
        return []
    files = sorted(
        [f for f in reports_dir.iterdir() if f.suffix in (".html", ".md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [{"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1),
             "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
            for f in files]


def _clean_old_reports(days: int = 7):
    reports_dir = _PROJ_ROOT / "reports"
    if not reports_dir.exists():
        return
    cutoff = datetime.now().timestamp() - days * 86400
    for f in reports_dir.iterdir():
        if f.suffix in (".html", ".md") and f.stat().st_mtime < cutoff:
            f.unlink()


def _list_kb_files() -> list[dict]:
    if not _KB_DIR.exists():
        return []
    files = sorted(
        [f for f in _KB_DIR.iterdir() if f.suffix.lower() in (".xlsx", ".xls", ".pdf", ".md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [{"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1),
             "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
            for f in files]
