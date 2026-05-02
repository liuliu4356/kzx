from __future__ import annotations

import os
from pathlib import Path

from ..collectors.prometheus import PromResult
from ..config import Config
from . import dingtalk, feishu


def _build_summary(prom_results: list[PromResult], anomaly_count: int,
                   report_path: Path) -> tuple[str, str]:
    """返回 (title, body)。"""
    status = "⚠️ 发现异常" if anomaly_count else "✅ 一切正常"
    title = f"系统巡检报告 — {status}"

    anomaly_lines = [
        f"- {r.name}: {r.value:.2f}{r.unit} (阈值 {r.threshold}{r.unit})"
        for r in prom_results
        if r.is_anomaly and r.value is not None
    ]
    error_lines = [
        f"- {r.name}: 采集失败 ({r.error})"
        for r in prom_results
        if r.error
    ]

    body_parts = [f"**异常指标**: {anomaly_count} / {len(prom_results)}"]
    if anomaly_lines:
        body_parts.append("\n**异常详情**:")
        body_parts.extend(anomaly_lines)
    if error_lines:
        body_parts.append("\n**采集错误**:")
        body_parts.extend(error_lines)
    body_parts.append(f"\n**报告文件**: `{report_path}`")

    return title, "\n".join(body_parts)


def notify_all(cfg: Config, prom_results: list[PromResult],
               report_path: Path) -> list[str]:
    """
    向所有配置的通知渠道发送巡检摘要。
    返回错误信息列表（空列表表示全部成功）。
    """
    if not cfg.notifiers:
        return []

    anomaly_count = sum(1 for r in prom_results if r.is_anomaly)
    title, body = _build_summary(prom_results, anomaly_count, report_path)
    errors: list[str] = []

    for item in cfg.notifiers:
        webhook_url = os.environ.get(item.webhook_env, "")
        if not webhook_url:
            errors.append(f"[{item.type}] 未设置环境变量 {item.webhook_env},跳过")
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
