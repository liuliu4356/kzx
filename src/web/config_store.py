"""读写 config.yaml 的辅助层，供 Web 路由使用。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path("config.yaml")


def _load_raw() -> dict:
    if not CONFIG_PATH.exists():
        example = Path("config.example.yaml")
        if example.exists():
            import shutil
            shutil.copy(example, CONFIG_PATH)
        else:
            return {}
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def _save_raw(data: dict) -> None:
    CONFIG_PATH.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def get_all() -> dict:
    return _load_raw()


# ── Sites ──────────────────────────────────────────────────────────────────

def list_sites() -> list[dict]:
    return _load_raw().get("sites", [])


def save_site(site: dict) -> None:
    raw = _load_raw()
    sites: list[dict] = raw.setdefault("sites", [])
    for i, s in enumerate(sites):
        if s["label"] == site["label"]:
            sites[i] = site
            _save_raw(raw)
            return
    sites.append(site)
    _save_raw(raw)


def delete_site(label: str) -> bool:
    raw = _load_raw()
    before = len(raw.get("sites", []))
    raw["sites"] = [s for s in raw.get("sites", []) if s["label"] != label]
    if len(raw["sites"]) < before:
        _save_raw(raw)
        return True
    return False


# ── Prometheus queries ─────────────────────────────────────────────────────

def list_prom_queries() -> list[dict]:
    return _load_raw().get("prometheus", {}).get("queries", [])


def save_prom_query(q: dict) -> None:
    raw = _load_raw()
    queries: list[dict] = raw.setdefault("prometheus", {}).setdefault("queries", [])
    for i, existing in enumerate(queries):
        if existing["name"] == q["name"]:
            queries[i] = q
            _save_raw(raw)
            return
    queries.append(q)
    _save_raw(raw)


def delete_prom_query(name: str) -> bool:
    raw = _load_raw()
    qs = raw.get("prometheus", {}).get("queries", [])
    before = len(qs)
    raw["prometheus"]["queries"] = [q for q in qs if q["name"] != name]
    if len(raw["prometheus"]["queries"]) < before:
        _save_raw(raw)
        return True
    return False


# ── ES queries ─────────────────────────────────────────────────────────────

def list_es_queries() -> list[dict]:
    return _load_raw().get("elasticsearch", {}).get("queries", [])


def save_es_query(q: dict) -> None:
    raw = _load_raw()
    queries: list[dict] = raw.setdefault("elasticsearch", {}).setdefault("queries", [])
    for i, existing in enumerate(queries):
        if existing["name"] == q["name"]:
            queries[i] = q
            _save_raw(raw)
            return
    queries.append(q)
    _save_raw(raw)


def delete_es_query(name: str) -> bool:
    raw = _load_raw()
    qs = raw.get("elasticsearch", {}).get("queries", [])
    before = len(qs)
    raw["elasticsearch"]["queries"] = [q for q in qs if q["name"] != name]
    if len(raw["elasticsearch"]["queries"]) < before:
        _save_raw(raw)
        return True
    return False


# ── Settings (LLM / Report / Notifiers / Batch / Inspection) ──────────────

def save_settings(section: str, data: dict) -> None:
    raw = _load_raw()
    raw[section] = {**raw.get(section, {}), **data}
    _save_raw(raw)


def save_prometheus_url(url: str, timeout_sec: int) -> None:
    raw = _load_raw()
    raw.setdefault("prometheus", {})["url"] = url
    raw["prometheus"]["timeout_sec"] = timeout_sec
    _save_raw(raw)


def save_es_url(url: str, username_env: str, password_env: str, timeout_sec: int,
                kibana_url: str = "") -> None:
    raw = _load_raw()
    raw.setdefault("elasticsearch", {}).update({
        "url": url,
        "username_env": username_env,
        "password_env": password_env,
        "timeout_sec": timeout_sec,
        "kibana_url": kibana_url,
    })
    _save_raw(raw)
