"""内部辅助函数"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.responses import HTMLResponse

from . import config_store as cs

_WEB_DIR = Path(__file__).parent
_SRC_DIR = _WEB_DIR.parent
_PROJ_ROOT = _SRC_DIR.parent
_KB_DIR = _PROJ_ROOT / "knowledge_base"
_REPORTS_DIR = _PROJ_ROOT / "reports"


def _list_reports(report_dir: Path | None = None, days: int = 7) -> list[dict]:
    if report_dir is None:
        raw = cs.get_all()
        report_dir = Path(raw.get("report", {}).get("output_dir", "reports"))
        if not report_dir.is_absolute():
            report_dir = _PROJ_ROOT / report_dir
    if not report_dir.exists():
        return []

    cutoff = datetime.now().timestamp() - days * 86400
    for f in list(report_dir.iterdir()):
        if f.suffix in (".html", ".md") and f.stat().st_mtime < cutoff:
            f.unlink()

    files = sorted(
        [f for f in report_dir.iterdir() if f.suffix in (".html", ".md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for f in files
    ]


def _list_kb_files() -> list[dict]:
    if not _KB_DIR.exists():
        return []

    files = sorted(
        [f for f in _KB_DIR.iterdir() if f.suffix.lower() in (".xlsx", ".xls", ".pdf", ".md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for f in files
    ]


def _get_current_user(request) -> dict | None:
    return getattr(request.state, "current_user", None)


def render_template(name: str, context: dict, request=None) -> HTMLResponse:
    from .app import jinja_env
    if request is not None and "current_user" not in context:
        context["current_user"] = _get_current_user(request)
    user = context.get("current_user")
    if "is_admin" not in context:
        context["is_admin"] = user is not None and user.get("role") == "admin"
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))
