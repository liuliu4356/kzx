"""认证路由"""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import auth as _auth
from .helpers import render_template

router = APIRouter()


# ── 认证路由 ─────────────────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def page_login(request: Request, next: str = "/"):
    if _auth.get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return render_template("login.html", {
        "error": "",
        "allow_register": _auth.user_count() == 0,
    }, request)


@router.post("/login", response_class=HTMLResponse)
async def do_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    token = _auth.login(username, password)
    if token is None:
        return render_template("login.html", {
            "error": "用户名或密码错误",
            "allow_register": _auth.user_count() == 0,
        }, request)
    resp = RedirectResponse(next if next.startswith("/") else "/", status_code=302)
    resp.set_cookie(_auth.COOKIE_NAME, token, httponly=True, max_age=7 * 24 * 3600, samesite="lax")
    return resp


@router.post("/logout")
async def do_logout(request: Request):
    token = request.cookies.get(_auth.COOKIE_NAME, "")
    if token:
        _auth.logout(token)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(_auth.COOKIE_NAME)
    return resp


@router.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    user = _auth.get_current_user(request)
    first_user = _auth.user_count() == 0
    if not first_user and (user is None or user.get("role") != "admin"):
        return RedirectResponse("/login", status_code=302)
    return render_template("register.html", {
        "error": "",
        "first_user": first_user,
    }, request)


@router.post("/register", response_class=HTMLResponse)
async def do_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    role: str = Form("viewer"),
):
    user = _auth.get_current_user(request)
    first_user = _auth.user_count() == 0
    if not first_user and (user is None or user.get("role") != "admin"):
        return RedirectResponse("/login", status_code=302)
    
    if password != password2:
        return render_template("register.html", {
            "error": "两次密码不一致",
            "first_user": first_user,
        }, request)
    if len(password) < 6:
        return render_template("register.html", {
            "error": "密码至少6位",
            "first_user": first_user,
        }, request)
    
    actual_role = "admin" if first_user else role
    ok = _auth.create_user(username, password, actual_role)
    if not ok:
        return render_template("register.html", {
            "error": "用户名已存在",
            "first_user": first_user,
        }, request)
    
    if first_user:
        token = _auth.login(username, password)
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie(_auth.COOKIE_NAME, token, httponly=True, max_age=7 * 24 * 3600, samesite="lax")
        return resp
    return RedirectResponse("/users", status_code=302)


@router.get("/users", response_class=HTMLResponse)
async def page_users(request: Request):
    user = _auth.get_current_user(request)
    if user is None or user.get("role") != "admin":
        raise HTTPException(403, "仅管理员可访问")
    return render_template("users.html", {
        "users": _auth.list_users(),
        "current_user": user.get("username"),
        "active": "settings",
    }, request)


@router.delete("/api/users/{username}")
async def api_delete_user(username: str, request: Request):
    user = _auth.get_current_user(request)
    if user is None or user.get("role") != "admin":
        raise HTTPException(403, "权限不足")
    if username == user.get("username"):
        raise HTTPException(400, "不能删除自己")
    ok = _auth.delete_user(username)
    if not ok:
        raise HTTPException(404, "用户不存在")
    return JSONResponse({"ok": True})


@router.post("/api/users/{username}/password")
async def api_change_password(
    username: str,
    request: Request,
    new_password: str = Form(...),
    new_password2: str = Form(...),
):
    current = _auth.get_current_user(request)
    if current is None:
        raise HTTPException(401, "未登录")
    if current.get("role") != "admin" and current.get("username") != username:
        raise HTTPException(403, "权限不足")
    if new_password != new_password2:
        raise HTTPException(400, "两次密码不一致")
    if len(new_password) < 6:
        raise HTTPException(400, "密码至少6位")
    ok = _auth.change_password(username, new_password)
    if not ok:
        raise HTTPException(404, "用户不存在")
    return JSONResponse({"ok": True})
