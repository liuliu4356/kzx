from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from ..config import PromConfig, PromQuery


@dataclass
class AnomalyWindow:
    start_ts: str       # ISO 格式时间字符串
    end_ts: str
    instance: str       # 节点 IP（已去除端口）
    max_value: float
    threshold: float
    unit: str
    duration_minutes: int


@dataclass
class PromRangeResult:
    name: str
    promql: str
    threshold: float
    unit: str
    anomaly_when: str
    period_min: float | None
    period_max: float | None
    period_avg: float | None
    anomaly_windows: list[AnomalyWindow] = field(default_factory=list)
    error: str | None = None
    faq: str = ""
    description: str = ""
    component: str = "system"
    severity: str = "warning"

    @property
    def is_anomaly(self) -> bool:
        return bool(self.anomaly_windows)


def _is_anomaly(value: float, threshold: float, anomaly_when: str) -> bool:
    return value < threshold if anomaly_when == "lt" else value > threshold


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _extract_anomaly_windows(
    values: list[tuple[float, float]],
    threshold: float,
    anomaly_when: str,
    unit: str,
    step_minutes: int,
    instance: str,
) -> list[AnomalyWindow]:
    violations = [(ts, val) for ts, val in values if _is_anomaly(val, threshold, anomaly_when)]
    if not violations:
        return []

    gap_tolerance_sec = step_minutes * 2 * 60
    windows: list[AnomalyWindow] = []
    w_start, w_end, w_max = violations[0][0], violations[0][0], violations[0][1]

    for ts, val in violations[1:]:
        if ts - w_end <= gap_tolerance_sec:
            w_end = ts
            w_max = max(w_max, val)
        else:
            windows.append(AnomalyWindow(
                start_ts=_fmt_ts(w_start), end_ts=_fmt_ts(w_end),
                instance=instance, max_value=w_max,
                threshold=threshold, unit=unit,
                duration_minutes=max(step_minutes, int((w_end - w_start) / 60) + step_minutes),
            ))
            w_start, w_end, w_max = ts, ts, val

    windows.append(AnomalyWindow(
        start_ts=_fmt_ts(w_start), end_ts=_fmt_ts(w_end),
        instance=instance, max_value=w_max,
        threshold=threshold, unit=unit,
        duration_minutes=max(step_minutes, int((w_end - w_start) / 60) + step_minutes),
    ))
    return windows


def _query_range_one(
    client: httpx.Client,
    base_url: str,
    q: PromQuery,
    start: datetime,
    end: datetime,
    step_minutes: int,
) -> PromRangeResult:
    empty = PromRangeResult(
        name=q.name, promql=q.promql, threshold=q.threshold,
        unit=q.unit, anomaly_when=q.anomaly_when,
        period_min=None, period_max=None, period_avg=None,
    )
    try:
        resp = client.get(
            f"{base_url.rstrip('/')}/api/v1/query_range",
            params={
                "query": q.promql,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": f"{step_minutes}m",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            empty.error = f"Prometheus 返回非 success: {data.get('error', data)}"
            return empty

        matrix = data.get("data", {}).get("result", [])
        if not matrix:
            empty.error = "无数据"
            return empty

        all_values: list[float] = []
        anomaly_windows: list[AnomalyWindow] = []

        for series in matrix:
            raw_instance = series.get("metric", {}).get("instance", "unknown")
            instance_ip = raw_instance.split(":")[0]  # 去除端口号

            pts: list[tuple[float, float]] = [
                (float(ts), float(val))
                for ts, val in series.get("values", [])
                if val != "NaN"
            ]
            if not pts:
                continue

            vals = [v for _, v in pts]
            all_values.extend(vals)
            anomaly_windows.extend(
                _extract_anomaly_windows(pts, q.threshold, q.anomaly_when,
                                         q.unit, step_minutes, instance_ip)
            )

        if not all_values:
            empty.error = "结果无有效值"
            return empty

        return PromRangeResult(
            name=q.name, promql=q.promql, threshold=q.threshold,
            unit=q.unit, anomaly_when=q.anomaly_when,
            period_min=min(all_values),
            period_max=max(all_values),
            period_avg=sum(all_values) / len(all_values),
            anomaly_windows=anomaly_windows,
            error=None,
        )

    except httpx.HTTPError as exc:
        empty.error = str(exc)
        return empty


def collect_range(
    cfg: PromConfig,
    start: datetime,
    end: datetime,
    step_minutes: int = 5,
) -> list[PromRangeResult]:
    with httpx.Client(timeout=max(cfg.timeout_sec, 30)) as client:
        return [
            _query_range_one(client, cfg.url, q, start, end, step_minutes)
            for q in cfg.queries
        ]
