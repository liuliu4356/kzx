from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from ..config import ESConfig, ESQuery, get_es_auth


@dataclass
class ESHit:
    timestamp: str | None
    level: str | None
    message: str
    raw: dict


@dataclass
class ESResult:
    name: str
    index: str
    query_string: str
    total: int
    hits: list[ESHit]
    error: str | None
    ignorable: bool = False
    faq: str = ""
    time_range_hours: int = 24  # 用于构造 Kibana 跳转链接的时间范围


def _build_body(q: ESQuery) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(hours=q.time_range_hours)).isoformat()
    return {
        "size": q.size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"query_string": {"query": q.query_string}},
                    {"range": {"@timestamp": {"gte": since}}},
                ]
            }
        },
        "_source": ["@timestamp", "level", "message", "log.level", "log.message"],
    }


def _extract_hit(doc: dict) -> ESHit:
    src = doc.get("_source", {})
    msg = src.get("message") or src.get("log", {}).get("message") or ""
    lvl = src.get("level") or src.get("log", {}).get("level")
    return ESHit(
        timestamp=src.get("@timestamp"),
        level=lvl,
        message=str(msg)[:500],
        raw=src,
    )


def _query_one(client: httpx.Client, base_url: str, q: ESQuery,
               auth: tuple[str, str] | None) -> ESResult:
    try:
        resp = client.post(
            f"{base_url.rstrip('/')}/{q.index}/_search",
            json=_build_body(q),
            auth=auth,
        )
        if resp.status_code == 404:
            return ESResult(name=q.name, index=q.index, query_string=q.query_string,
                            total=0, hits=[], error=f"index 不存在: {q.index}")
        resp.raise_for_status()
        data = resp.json()
        total_obj = data.get("hits", {}).get("total", 0)
        total = total_obj["value"] if isinstance(total_obj, dict) else int(total_obj)
        hits = [_extract_hit(h) for h in data.get("hits", {}).get("hits", [])]
        return ESResult(name=q.name, index=q.index, query_string=q.query_string,
                        total=total, hits=hits, error=None)
    except httpx.HTTPError as exc:
        return ESResult(name=q.name, index=q.index, query_string=q.query_string,
                        total=0, hits=[], error=str(exc))


def collect(cfg: ESConfig) -> list[ESResult]:
    auth = get_es_auth(cfg)
    with httpx.Client(timeout=cfg.timeout_sec) as client:
        results = [_query_one(client, cfg.url, q, auth) for q in cfg.queries]
    for result, query in zip(results, cfg.queries):
        result.ignorable = query.ignorable
        result.time_range_hours = query.time_range_hours
    return results
