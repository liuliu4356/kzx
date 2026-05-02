from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from ..config import PromConfig, PromQuery


@dataclass
class PromResult:
    name: str
    promql: str
    value: float | None
    threshold: float
    unit: str
    is_anomaly: bool
    error: str | None
    timestamp: str
    faq: str = ""
    description: str = ""


def _is_anomaly(value: float, threshold: float, anomaly_when: str) -> bool:
    if anomaly_when == "lt":
        return value < threshold
    return value > threshold


def _query_one(client: httpx.Client, base_url: str, q: PromQuery) -> PromResult:
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        resp = client.get(
            f"{base_url.rstrip('/')}/api/v1/query",
            params={"query": q.promql},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            return PromResult(
                name=q.name, promql=q.promql, value=None, threshold=q.threshold,
                unit=q.unit, is_anomaly=False,
                error=f"prometheus 返回非 success: {data.get('error', data)}",
                timestamp=now_iso,
            )
        results = data.get("data", {}).get("result", [])
        if not results:
            return PromResult(
                name=q.name, promql=q.promql, value=None, threshold=q.threshold,
                unit=q.unit, is_anomaly=False, error="无数据",
                timestamp=now_iso,
            )
        # 处理两种格式：1.时间序列 [{"metric":{}, "value":[t,v]},...] 2.标量 [t,v]
        values = []
        for r in results:
            if isinstance(r, list) and len(r) == 2:
                values.append(float(r[1]))
            elif isinstance(r, dict) and "value" in r:
                values.append(float(r["value"][1]))
        if not values:
            return PromResult(
                name=q.name, promql=q.promql, value=None, threshold=q.threshold,
                unit=q.unit, is_anomaly=False, error="结果无 value 字段",
                timestamp=now_iso,
            )
        v = max(values) if q.anomaly_when == "gt" else min(values)
        return PromResult(
            name=q.name, promql=q.promql, value=v, threshold=q.threshold,
            unit=q.unit,
            is_anomaly=_is_anomaly(v, q.threshold, q.anomaly_when),
            error=None,
            timestamp=now_iso,
        )
    except httpx.HTTPError as exc:
        return PromResult(
            name=q.name, promql=q.promql, value=None, threshold=q.threshold,
            unit=q.unit, is_anomaly=False, error=str(exc),
            timestamp=now_iso,
        )


def collect(cfg: PromConfig) -> list[PromResult]:
    with httpx.Client(timeout=cfg.timeout_sec) as client:
        return [_query_one(client, cfg.url, q) for q in cfg.queries]
