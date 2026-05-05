from __future__ import annotations

import queue
import threading
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from . import config_store as cs
from . import auth as _auth
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

from ..logging_setup import get_log_path, tail_log

_WEB_DIR = Path(__file__).parent
_SRC_DIR = _WEB_DIR.parent
_PROJ_ROOT = _SRC_DIR.parent
_KB_DIR = _PROJ_ROOT / "knowledge_base"
_REPORTS_DIR = _PROJ_ROOT / "reports"
_CONFIG_PATH = str(_PROJ_ROOT / "config.yaml")

_scheduler = None

# ── 认证中间件 ─────────────────────────────────────────────────────

_AUTH_WHITELIST = {"/login", "/register", "/logout"}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (path.startswith("/static") or path in _AUTH_WHITELIST):
            return await call_next(request)
        if _auth.user_count() == 0:
            if not path.startswith("/register"):
                return RedirectResponse("/register", status_code=302)
            return await call_next(request)
        user = _auth.get_current_user(request)
        if user is None:
            return RedirectResponse(f"/login?next={path}", status_code=302)
        request.state.current_user = user
        return await call_next(request)

# ── FastAPI 主应用 ─────────────────────────────────────────────

app = FastAPI(title="三思GDB巡检平台")
app.add_middleware(AuthMiddleware)

# ── 启动和关闭事件 ─────────────────────────────────────────────

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
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

# ── 静态文件和模板 ─────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")
jinja_env = Environment(loader=FileSystemLoader(str(_WEB_DIR / "templates")))

# ── 导入路由模块 ─────────────────────────────────────────────

from .routes import router as routes_router
from .api import router as api_router
from .auth_routes import router as auth_router

app.include_router(routes_router)
app.include_router(api_router)
app.include_router(auth_router)

