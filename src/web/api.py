"""API路由（使用APIRouter）"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from . import config_store as cs
from .helpers import render_template, _list_reports, _list_kb_files, _get_current_user, _PROJ_ROOT
from ..logging_setup import get_log_path, tail_log

# 创建路由器
router = APIRouter()

# 导入其他需要的模块（延迟导入以避免循环导入）
# 这些会在函数中导入，因为需要访问调度器

# ── API: Sites ───────────────────────────────────────────

@router.post("/api/sites")
async def api_save_site(
    request: Request,
    label: str = Form(...),
    prometheus_url: str = Form(...),
    es_url: str = Form(""),
    original_label: str = Form(""),
):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not _auth.has_permission(user, "can_edit"):
        raise HTTPException(403, "权限不足：需要编辑权限")
    lookup_label = original_label.strip() or label
    cs.save_site({"label": label, "prometheus_url": prometheus_url,
                  "es_url": es_url or None}, lookup_label=lookup_label)
    return JSONResponse({"ok": True})


@router.delete("/api/sites/{label}")
async def api_delete_site(label: str, request: Request):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not _auth.has_permission(user, "can_edit"):
        raise HTTPException(403, "权限不足：需要编辑权限")
    ok = cs.delete_site(label)
    if not ok:
        raise HTTPException(404, "机房不存在")
    return JSONResponse({"ok": True})


# ── API: Prometheus queries ─────────────────────────────────

@router.post("/api/queries/prom")
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


@router.delete("/api/queries/prom/{name}")
async def api_delete_prom(name: str):
    ok = cs.delete_prom_query(name)
    if not ok:
        raise HTTPException(404, "指标不存在")
    return JSONResponse({"ok": True})


# ── API: ES queries ────────────────────────────────────

@router.post("/api/queries/es")
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


@router.delete("/api/queries/es/{name}")
async def api_delete_es(name: str):
    ok = cs.delete_es_query(name)
    if not ok:
        raise HTTPException(404, "查询不存在")
    return JSONResponse({"ok": True})


# ── API: Import/Export ────────────────────────────────────

@router.get("/api/config/export")
async def api_export():
    raw = cs._load_raw()
    return JSONResponse({
        "prometheus": raw.get("prometheus", {}),
        "elasticsearch": raw.get("elasticsearch", {}),
        "sites": raw.get("sites") or raw.get("datacenters", []),
    })


@router.post("/api/config/import")
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


# ── API: Backups ─────────────────────────────────────────
@router.get("/api/backups")
async def api_list_backups():
    backups = cs.list_backups()
    return JSONResponse(backups)


@router.post("/api/backups/create")
async def api_create_backup():
    filename = cs._create_backup()
    if filename:
        return JSONResponse({"ok": True, "filename": filename})
    return JSONResponse({"ok": False, "error": "no config to backup"})


@router.post("/api/backups/{filename}/restore")
async def api_restore_backup(filename: str):
    ok = cs.restore_backup(filename)
    return JSONResponse({"ok": ok})


@router.delete("/api/backups/{filename}")

# 配置备份/恢复
@router.post("/api/config/backup")
async def api_config_backup(request: Request):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = await request.json()
    t = data.get("type", "prometheus")
    name = data.get("name", "")
    raw = cs._load_raw()
    if t == "prometheus":
        cfg = raw.get("prometheus", {})
        fname = f"prometheus_{name or datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    elif t == "elasticsearch":
        cfg = raw.get("elasticsearch", {})
        fname = f"elasticsearch_{name or datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:
        return {"error": "未知类型"}
    backup_dir = Path(_PROJ_ROOT) / "config_backups"
    backup_dir.mkdir(exist_ok=True)
    (backup_dir / fname).write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    return {"ok": f"已备份到 {fname}"}

@router.get("/api/config/backups")
async def api_config_backups():
    backup_dir = Path(_PROJ_ROOT) / "config_backups"
    if not backup_dir.exists():
        return []
    backups = []
    for f in sorted(backup_dir.glob("*.json")):
        name = f.stem
        if name.startswith("prometheus_"):
            backups.append({"type": "prometheus", "name": name.replace("prometheus_", ""), "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
        elif name.startswith("elasticsearch_"):
            backups.append({"type": "elasticsearch", "name": name.replace("elasticsearch_", ""), "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    return backups

@router.post("/api/config/restore")
async def api_config_restore(request: Request):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = await request.json()
    t = data.get("type", "prometheus")
    name = data.get("name", "")
    backup_dir = Path(_PROJ_ROOT) / "config_backups"
    if t == "prometheus":
        fname = f"prometheus_{name}.json"
    elif t == "elasticsearch":
        fname = f"elasticsearch_{name}.json"
    else:
        return {"error": "未知类型"}
    fpath = backup_dir / fname
    if not fpath.exists():
        return {"error": "备份文件不存在"}
    cfg = json.loads(fpath.read_text())
    raw = cs._load_raw()
    raw[t] = cfg
    cs._save(raw)
    return {"ok": "配置已恢复"}

# Web服务管理
@router.get("/api/service/status")
async def api_service_status(request: Request):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    import subprocess
    try:
        out = subprocess.check_output("netstat -tlnp | grep python", shell=True, timeout=5).decode()
        for line in out.split("\n"):
            if ":800" in line:
                parts = line.split()
                return {"running": True, "port": 8000, "info": line}
        return {"running": False}
    except:
        return {"running": False}

@router.post("/api/service/{action}")
async def api_service_action(action: str, request: Request):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    import subprocess
    if action == "stop":
        subprocess.run("pkill -f 'src.main'", shell=True, timeout=10)
        return {"ok": "服务已停止"}
    elif action == "restart":
        subprocess.run("pkill -f 'src.main'", shell=True, timeout=10)
        subprocess.Popen("cd /opt/kzx && nohup /opt/kzx/venv/bin/python -m src.main web --host 0.0.0.0 --port 8000 > /var/log/kzx.log 2>&1 &", shell=True)
        return {"ok": "服务已重启"}
    elif action == "start":
        subprocess.Popen("cd /opt/kzx && nohup /opt/kzx/venv/bin/python -m src.main web --host 0.0.0.0 --port 8000 > /var/log/kzx.log 2>&1 &", shell=True)
        return {"ok": "服务已启动"}
    return {"error": "未知操作"}
async def api_delete_backup(filename: str):
    ok = cs.delete_backup(filename)
    return JSONResponse({"ok": ok})


# ── API: Datasources ─────────────────────────────────────

@router.post("/api/datasources")
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


@router.delete("/api/datasources/{ds_id}")
async def api_delete_datasource(ds_id: str):
    ok = cs.delete_datasource(ds_id)
    if not ok:
        raise HTTPException(404, "数据源不存在")
    return JSONResponse({"ok": True})


@router.get("/api/datasources/export")
async def api_export_datasources():
    return JSONResponse(cs.list_datasources())


@router.post("/api/datasources/import")
async def api_import_datasources(request: Request):
    data = await request.json()
    if not isinstance(data, list):
        raise HTTPException(400, "期望 JSON 数组格式")
    raw = cs._load_raw()
    raw["datasources"] = data
    cs._save_raw(raw)
    return JSONResponse({"ok": True})


# ── API: LLM Models ──────────────────────────────────────

@router.post("/api/llm/models")
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


@router.delete("/api/llm/models/{model_id}")
async def api_delete_llm_model(model_id: str):
    ok = cs.delete_llm_model(model_id)
    if not ok:
        raise HTTPException(404, "模型不存在")
    return JSONResponse({"ok": True})


@router.post("/api/llm/models/{model_id}/activate")
async def api_activate_llm(model_id: str):
    cs.set_active_llm(model_id)
    return JSONResponse({"ok": True})


# ── API: Knowledge Base ──────────────────────────────────

@router.post("/api/knowledge-base/upload")
async def api_kb_upload(files: list[UploadFile] = File(...)):
    from .app import _KB_DIR
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


@router.post("/api/knowledge-base/update")
async def api_kb_update(file: UploadFile = File(...), replace: str = Form("")):
    from .app import _KB_DIR
    _KB_DIR.mkdir(parents=True, exist_ok=True)
    target_name = replace if replace else file.filename
    dest = _KB_DIR / target_name
    content = await file.read()
    dest.write_bytes(content)
    return JSONResponse({"ok": True})


@router.get("/api/knowledge-base/download/{filename}")
async def api_kb_download(filename: str):
    from .app import _KB_DIR
    path = _KB_DIR / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(path), filename=filename)


@router.delete("/api/knowledge-base/{filename}")
async def api_kb_delete(filename: str):
    from .app import _KB_DIR
    path = _KB_DIR / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    path.unlink()
    return JSONResponse({"ok": True})


# ── API: Notifiers ──────────────────────────────────────

@router.post("/api/notifiers")
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


# ── API: Settings ──────────────────────────────────────

@router.post("/api/settings/prometheus")
async def api_prom_settings(
    url: str = Form(...),
    timeout_sec: int = Form(10),
):
    cs.save_prometheus_url(url, timeout_sec)
    return JSONResponse({"ok": True})


@router.post("/api/settings/elasticsearch")
async def api_es_settings(
    url: str = Form(...),
    username_env: str = Form(""),
    password_env: str = Form(""),
    timeout_sec: int = Form(10),
    kibana_url: str = Form(""),
):
    cs.save_es_url(url, username_env, password_env, timeout_sec, kibana_url)
    return JSONResponse({"ok": True})


@router.post("/api/settings/report")
async def api_report_settings(
    output_dir: str = Form("reports"),
    language: str = Form("zh-CN"),
    retention_days: int = Form(7),
):
    cs.save_settings("report", {"output_dir": output_dir, "language": language,
                                 "filename_format": "%Y-%m-%d-%H%M",
                                 "retention_days": retention_days})
    return JSONResponse({"ok": True})


# ── API: Online Test ────────────────────────────────────

@router.post("/api/test/prom")
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
            return JSONResponse({"ok": False, "error": data.get("error", "未知错误"), "log_path": get_log_path()})
        results = data.get("data", {}).get("result", [])
        samples = []
        for r in results[:5]:
            if isinstance(r, dict) and "value" in r:
                inst = r.get("metric", {}).get("instance", "")
                samples.append({"instance": inst, "value": r["value"][1]})
        return JSONResponse({"ok": True, "count": len(results), "samples": samples,
                              "log_path": get_log_path()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "log_path": get_log_path()})


@router.post("/api/test/es")
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
        body = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"query": query_string}},
                        {"range": {"@timestamp": {"gte": since}}},
                    ]
                }
            },
        }
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{es_url.rstrip('/')}/{index}/_search",
                                json=body, auth=auth)
            resp.raise_for_status()
            data = resp.json()
        total_obj = data.get("hits", {}).get("total", 0)
        total = total_obj["value"] if isinstance(total_obj, dict) else int(total_obj)
        return JSONResponse({"ok": True, "total": total, "log_path": get_log_path()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "log_path": get_log_path()})


# ── API: Cron Jobs ────────────────────────────────────────

@router.get("/api/cron")
async def api_list_cron():
    from .app import _scheduler
    jobs = cs.list_cron_jobs()
    next_runs: dict[str, str] = {}
    if _scheduler:
        for j in _scheduler.get_jobs():
            nrt = j.next_run_time
            next_runs[j.id] = nrt.isoformat() if nrt else None
    return JSONResponse({"jobs": jobs, "next_runs": next_runs})


@router.post("/api/cron")
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
    from .app import _scheduler
    if _scheduler:
        from ..scheduler import reload_jobs
        reload_jobs(_scheduler, cs._CONFIG_PATH)
    return JSONResponse({"ok": True})


@router.delete("/api/cron/{job_id}")
async def api_delete_cron(job_id: str):
    ok = cs.delete_cron_job(job_id)
    if not ok:
        raise HTTPException(404, "任务不存在")
    from .app import _scheduler
    if _scheduler:
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass
    return JSONResponse({"ok": True})


@router.post("/api/cron/{job_id}/run-now")
async def api_cron_run_now(job_id: str):
    jobs = cs.list_cron_jobs()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job:
        raise HTTPException(404, "任务不存在")
    import threading
    from ..scheduler import _run_inspection
    threading.Thread(
        target=_run_inspection, args=[cs._CONFIG_PATH, job_id], daemon=True
    ).start()
    return JSONResponse({"ok": True, "msg": f"任务 {job.get('label', job_id)} 已触发"})


@router.get("/api/cron/{job_id}/history")
async def api_cron_history(job_id: str):
    return JSONResponse({"history": cs.get_cron_history(job_id)})


@router.post("/api/cron/{job_id}/toggle")
async def api_cron_toggle(job_id: str, enabled: str = Form("true")):
    ok = cs.toggle_cron_job(job_id, enabled.lower() == "true")
    if not ok:
        raise HTTPException(404, "任务不存在")
    from .app import _scheduler
    if _scheduler:
        from ..scheduler import reload_jobs
        reload_jobs(_scheduler, cs._CONFIG_PATH)
    return JSONResponse({"ok": True})


# ── API: Table Monitor ──────────────────────────────────

@router.get("/api/table-monitor")
async def api_get_table_monitor():
    return JSONResponse(cs.get_table_monitor())


@router.post("/api/table-monitor/settings")
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


@router.post("/api/table-monitor/queries")
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


@router.delete("/api/table-monitor/queries/{name}")
async def api_delete_table_query(name: str):
    ok = cs.delete_table_query(name)
    if not ok:
        raise HTTPException(404, "监控表不存在")
    return JSONResponse({"ok": True})


@router.post("/api/test/table")
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
        return JSONResponse({"ok": True, "msg": "连接成功", "log_path": get_log_path()})
    except ImportError:
        return JSONResponse({"ok": False, "error": "pymysql 未安装", "log_path": get_log_path()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "log_path": get_log_path()})


# ── API: Test LLM ────────────────────────────────────

@router.post("/api/test/llm")
async def api_test_llm(model_id: str = Form(...)):
    try:
        raw = cs._load_raw()
        models = raw.get("llm", {}).get("models", [])
        m = next((x for x in models if x.get("id") == model_id), None)
        if not m:
            return JSONResponse({"ok": False, "error": "模型配置不存在", "log_path": get_log_path()})

        import os as _os
        api_key_env = m.get("api_key_env", "ANTHROPIC_API_KEY")
        api_key = _os.environ.get(api_key_env, "")
        provider = m.get("provider", "anthropic")
        model_name = m.get("model", "")
        api_base = m.get("api_base", "")

        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key or None)
            resp = client.messages.create(
                model=model_name,
                max_tokens=16,
                messages=[{"role": "user", "content": "reply 'ok'"}],
            )
            return JSONResponse({"ok": True, "msg": f"响应: {resp.content[0].text[:50]}", "log_path": get_log_path()})
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key or "dummy", base_url=api_base or None)
            resp = client.chat.completions.create(
                model=model_name, max_tokens=16,
                messages=[{"role": "user", "content": "reply 'ok'"}],
            )
            return JSONResponse({"ok": True, "msg": f"响应: {resp.choices[0].message.content[:50]}", "log_path": get_log_path()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "log_path": get_log_path()})


# ── API: Inspect ──────────────────────────────────────

@router.post("/api/inspect")
async def api_inspect(
    request: Request,
    period: str = Form("instant"),
    start: str = Form(""),
    end: str = Form(""),
    skip_llm: str = Form("false"),
    fmt: str = Form("html"),
):
    from . import auth as _auth
    user = _auth.get_current_user(request)
    if not _auth.has_permission(user, "can_execute"):
        raise HTTPException(403, "权限不足：需要执行权限")

    from dotenv import load_dotenv
    load_dotenv()
    
    def _run(q: queue.Queue):
        try:
            from ..config import load_config, current_batch_window
            from ..collectors import collect_sites
            from ..analyzer import analyze
            from .. import reporter
            
            def emit(msg: str):
                q.put(f"data: {msg}\n\n")
            
            emit("PROGRESS:0")
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
                period_end = datetime.now(timezone.utc())
                period_start = period_end - timedelta(days=7)
                mode = "range"
            
            batch_win = current_batch_window(cfg.batch_windows)
            if batch_win:
                emit(f"⚠️ 当前处于批处理窗口：{batch_win.label}")
            
            emit("PROGRESS:25")
            emit(f"📡 采集各机房数据（{mode} 模式）...")
            site_results = collect_sites(cfg, mode=mode,
                                              period_start=period_start,
                                              period_end=period_end)
            for s in site_results:
                emit(f"  ✅ {s.label}：{s.anomaly_count} 项异常")
            
            emit("PROGRESS:50")
            if skip_llm.lower() == "true":
                emit("⏭️ 跳过 AI 分析")
                ai_analysis = "_已跳过 AI 分析。_"
            else:
                emit("🤖 AI 分析中...")
                ai_analysis = analyze(site_results, cfg.llm, batch_win,
                                         period_start, period_end)
                emit("  ✅ AI 分析完成")
            
            emit("PROGRESS:75")
            emit("📄 生成报告...")
            out_path = reporter.render(site_results, ai_analysis, cfg,
                                               period_start, period_end, fmt=fmt)
            emit("PROGRESS:100")
            emit(f"DONE:{out_path.name}")
            emit(f"LOGPATH:{get_log_path()}")
        except Exception as exc:
            q.put(f"data: ERROR:{exc}\n\n")
            q.put(f"data: LOGPATH:{get_log_path()}\n\n")
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


# ── API: Reports ──────────────────────────────────────

@router.get("/api/reports")
async def api_list_reports():
    return JSONResponse({"reports": _list_reports()})


@router.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    from .app import _REPORTS_DIR
    path = _REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "报告不存在")
    path.unlink()
    return JSONResponse({"ok": True})


# ── API: Logs ────────────────────────────────────────

@router.get("/api/logs")
async def api_get_logs(lines: int = 200):
    return JSONResponse({
        "log_path": get_log_path(),
        "lines": tail_log(lines),
    })
