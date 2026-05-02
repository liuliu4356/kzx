from __future__ import annotations

import queue
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import config_store as cs
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import json

app = FastAPI(title="GDB 巡检系统")

_WEB_DIR = Path(__file__).parent
_PROJ_ROOT = _WEB_DIR.parent.parent

app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")

# Use direct Jinja2 to avoid Starlette template caching issue
from jinja2 import Environment, FileSystemLoader

jinja_env = Environment(loader=FileSystemLoader(str(_WEB_DIR / "templates")))

def render_template(name: str, context: dict) -> HTMLResponse:
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))

templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))


# ── 页面路由 ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    raw = cs.get_all()
    reports = _list_reports()[:10]
    return render_template("index.html", {"raw": raw, "reports": reports})


@app.get("/sites", response_class=HTMLResponse)
async def page_sites(request: Request):
    sites = cs.list_sites()
    return render_template("sites.html", {"sites": sites})


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
    return render_template("queries.html", {
        "prom_queries": prom_queries,
        "es_queries": es_queries,
        "export_data_json": export_data,
    })


@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    raw = cs.get_all()
    return render_template("settings.html", {"raw": raw})


@app.get("/reports", response_class=HTMLResponse)
async def page_reports(request: Request):
    reports = _list_reports()
    return render_template("reports.html", {"reports": reports, "subtab": request.query_params.get("subtab", "")})


@app.get("/reports/settings", response_class=HTMLResponse)
async def page_reports_settings(request: Request):
    raw = cs.get_all()
    return render_template("reports_settings.html", {"raw": raw, "subtab": "settings"})


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


# ── API: Import/Export ───────────────────────────────────────────────────────

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


@app.post("/api/settings/llm")
async def api_llm_settings(
    model: str = Form(...),
    api_key_env: str = Form("ANTHROPIC_API_KEY"),
    max_tokens: int = Form(2048),
    enable_prompt_caching: str = Form("true"),
):
    cs.save_settings("llm", {
        "provider": "anthropic", "model": model,
        "api_key_env": api_key_env, "max_tokens": max_tokens,
        "enable_prompt_caching": enable_prompt_caching.lower() == "true",
    })
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

            # 解析时间段
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
                emit("🤖 AI 分析中（Claude）...")
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
            q.put(None)  # sentinel

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
    debug_info = f"filename={filename}, path={path}, exists={path.exists()}"
    if not path.exists():
        return JSONResponse({"error": debug_info}, status_code=404)
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
