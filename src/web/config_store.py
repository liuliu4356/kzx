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
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except UnicodeDecodeError:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="gbk")) or {}


def _save_raw(data: dict) -> None:
    CONFIG_PATH.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def get_all() -> dict:
    return _load_raw()


# ── Sites ──────────────────────────────────────────────────────────────────

def list_sites() -> list[dict]:
    raw = _load_raw()
    # 兼容 datacenters 和 sites 两种字段名
    return raw.get("sites") or raw.get("datacenters", [])


def save_site(site: dict) -> None:
    raw = _load_raw()
    # 兼容 datacenters 和 sites
    key = "datacenters" if "datacenters" in raw else "sites"
    sites: list[dict] = raw.setdefault(key, [])
    for i, s in enumerate(sites):
        if s.get("label") == site.get("label") or s.get("name") == site.get("name"):
            sites[i] = site
            _save_raw(raw)
            return
    sites.append(site)
    _save_raw(raw)


def delete_site(label: str) -> bool:
    raw = _load_raw()
    key = "datacenters" if "datacenters" in raw else "sites"
    sites = raw.get(key, [])
    before = len(sites)
    raw[key] = [s for s in sites if s.get("label") != label and s.get("name") != label]
    if len(raw[key]) < before:
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


# ── Datasources ────────────────────────────────────────────────────────────

def list_datasources() -> list[dict]:
    return _load_raw().get("datasources", [])


def save_datasource(ds: dict) -> None:
    raw = _load_raw()
    sources: list[dict] = raw.setdefault("datasources", [])
    for i, s in enumerate(sources):
        if s.get("id") == ds.get("id"):
            sources[i] = ds
            _save_raw(raw)
            return
    sources.append(ds)
    _save_raw(raw)


def delete_datasource(ds_id: str) -> bool:
    raw = _load_raw()
    sources = raw.get("datasources", [])
    before = len(sources)
    raw["datasources"] = [s for s in sources if s.get("id") != ds_id]
    if len(raw["datasources"]) < before:
        _save_raw(raw)
        return True
    return False


# ── LLM Models ─────────────────────────────────────────────────────────────

def list_llm_models() -> list[dict]:
    return _load_raw().get("llm", {}).get("models", [])


def get_llm_config() -> dict:
    return _load_raw().get("llm", {})


def save_llm_model(model: dict) -> None:
    raw = _load_raw()
    llm = raw.setdefault("llm", {})
    models: list[dict] = llm.setdefault("models", [])
    for i, m in enumerate(models):
        if m.get("id") == model.get("id"):
            models[i] = model
            _save_raw(raw)
            return
    models.append(model)
    _save_raw(raw)


def delete_llm_model(model_id: str) -> bool:
    raw = _load_raw()
    llm = raw.get("llm", {})
    models = llm.get("models", [])
    before = len(models)
    llm["models"] = [m for m in models if m.get("id") != model_id]
    if len(llm["models"]) < before:
        raw["llm"] = llm
        _save_raw(raw)
        return True
    return False


def set_active_llm(model_id: str) -> None:
    raw = _load_raw()
    raw.setdefault("llm", {})["active_model"] = model_id
    _save_raw(raw)


# ── Notifiers ──────────────────────────────────────────────────────────────

def get_notifier(ntype: str) -> dict:
    for n in _load_raw().get("notifiers", []):
        if n.get("type") == ntype:
            return n
    return {}


def save_notifier(notifier: dict) -> None:
    raw = _load_raw()
    notifiers: list[dict] = raw.setdefault("notifiers", [])
    ntype = notifier.get("type")
    for i, n in enumerate(notifiers):
        if n.get("type") == ntype:
            notifiers[i] = notifier
            _save_raw(raw)
            return
    notifiers.append(notifier)
    _save_raw(raw)


# ── Table Monitor ──────────────────────────────────────────────────────────

def get_table_monitor() -> dict:
    return _load_raw().get("table_monitor", {})


def save_table_monitor_settings(settings: dict) -> None:
    raw = _load_raw()
    tm = raw.setdefault("table_monitor", {})
    tm.update(settings)
    _save_raw(raw)


def save_table_query(q: dict) -> None:
    raw = _load_raw()
    queries: list[dict] = raw.setdefault("table_monitor", {}).setdefault("queries", [])
    for i, existing in enumerate(queries):
        if existing["name"] == q["name"]:
            queries[i] = q
            _save_raw(raw)
            return
    queries.append(q)
    _save_raw(raw)


def delete_table_query(name: str) -> bool:
    raw = _load_raw()
    queries = raw.get("table_monitor", {}).get("queries", [])
    before = len(queries)
    raw.setdefault("table_monitor", {})["queries"] = [q for q in queries if q["name"] != name]
    if len(raw["table_monitor"]["queries"]) < before:
        _save_raw(raw)
        return True
    return False


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
