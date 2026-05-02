from __future__ import annotations

import os
from pathlib import Path

from ..collectors import SiteResult
from ..config import Config
from . import dingtalk, feishu


def _build_summary(site_results: list[SiteResult],
                   report_path: Path) -> tuple[str, str]:
    mode = site_results[0].mode if site_results else "instant"
    total_anomaly = sum(s.anomaly_count for s in site_results)
    status = "⚠️ 发现异常" if total_anomaly else "✅ 一切正常"
    title = f"系统巡检报告 — {status}"

    lines: list[str] = []

    if mode == "range":
        total_windows = sum(s.total_anomaly_windows for s in site_results)
        lines.append(f"**模式**: 时间段审计 | **异常指标**: {total_anomaly} | **异常窗口**: {total_windows} 段")
        for s in site_results:
            if not s.prom_range_results:
                continue
            anomaly_items = [
                f"  - {r.name}：{len(r.anomaly_windows)} 个窗口，峰值 "
                f"{max(w.max_value for w in r.anomaly_windows):.2f}{r.unit}"
                for r in s.prom_range_results if r.is_anomaly
            ]
            if anomaly_items:
                lines.append(f"\n**{s.label}**")
                lines.extend(anomaly_items)
    else:
        total_prom = sum(len(s.prom_results) for s in site_results)
        lines.append(f"**模式**: 快照 | **异常指标**: {total_anomaly} / {total_prom}")
        for s in site_results:
            anomaly_items = [
                f"  - {r.name}: {r.value:.2f}{r.unit} (阈值 {r.threshold}{r.unit})"
                for r in s.prom_results
                if r.is_anomaly and r.value is not None
            ]
            error_items = [
                f"  - {r.name}: 采集失败 ({r.error})"
                for r in s.prom_results if r.error
            ]
            if anomaly_items or error_items:
                lines.append(f"\n**{s.label}**")
                lines.extend(anomaly_items)
                lines.extend(error_items)

    lines.append(f"\n**报告文件**: `{report_path}`")
    return title, "\n".join(lines)


def notify_all(cfg: Config, site_results: list[SiteResult],
               report_path: Path) -> list[str]:
    if not cfg.notifiers:
        return []

    title, body = _build_summary(site_results, report_path)
    errors: list[str] = []

    for item in cfg.notifiers:
        webhook_url = os.environ.get(item.webhook_env, "")
        if not webhook_url:
            errors.append(f"[{item.type}] 未设置环境变量 {item.webhook_env}，跳过")
            continue
        try:
            if item.type == "dingtalk":
                dingtalk.send(webhook_url, title, body, item.mention_all)
            elif item.type == "feishu":
                feishu.send(webhook_url, title, body)
            else:
                errors.append(f"未知通知类型: {item.type}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"[{item.type}] 发送失败: {exc}")

    return errors
