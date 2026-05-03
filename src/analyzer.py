from __future__ import annotations

import json
import os
from datetime import datetime

import anthropic

from .collectors import SiteResult
from .config import BatchWindow, LLMConfig

SYSTEM_PROMPT = """你是一位资深 SRE 巡检助手，负责审阅基于 Prometheus 指标与 Elasticsearch 日志的系统巡检数据。
数据可能来自多个机房，支持快照（instant）和时间段审计（range）两种模式。

## GoldenDB 组件架构（用于根因判断）

GoldenDB 分布式数据库的组件依赖关系如下：
- **OMM**（主控节点）：集群大脑，负责全局协调。OMM 异常会导致 CM/PM 无法工作。
- **MDS**（元数据服务）：存储分区/副本映射。MDS 异常导致查询路由失败，影响 DBProxy 和业务连接。
- **CM**（集群管理）：负责节点心跳和故障检测。CM 异常可能引发误判 RDB 下线，导致副本数不足。
- **PM**（分区管理）：管理数据分区分配。PM 异常导致分区副本因子下降告警。
- **GTM**（全局事务管理器）：主备同步。GTM 延迟高通常是网络带宽或写入压力过大。
- **RDB**（存储节点）：实际数据存储。RDB 同步延迟高表示从节点追不上主节点写入速度。
- **DBProxy**（数据库代理）：SQL 路由层，连接池满或错误率高说明业务压力大或存在连接泄漏。
- **Backup**（备份进程）：arm_backup_mysql，备份进程不存活需立即检查 cron 配置和日志。

**根因推断规则**：
- OMM down → 所有组件可能级联异常，优先级 P0
- MDS down → DBProxy 连接失败（路由表无法更新）
- CM down → 可能触发 RDB 副本数告警
- GTM 延迟高 + 批处理窗口 → 已知现象，降级为 P2
- 副本数不足 → 排查是否有 RDB 节点下线

请严格按以下 Markdown 结构输出（不要添加其他节）：

## 健康度评分
- 给出 0-100 的总体评分，并一句话说明依据。
- 若有多机房，给出各机房子评分。

## 异常项
- 列出需要关注的指标或日志（若无异常，写"无"）。
- range 模式：注明机房、指标名、异常时间段、节点IP、峰值、阈值、持续时长。
- instant 模式：注明机房、来源（metric/log）、名称、当前值、阈值。
- 如有 GDB 组件异常，注明所属组件（component 字段）并推断级联影响。

## 建议动作
- 针对异常项给出可执行的排查或修复动作。
- 按优先级 P0 / P1 / P2 标注。
- GDB 组件存活类（severity=critical）异常一律 P0。

## 总结
- 3-5 句话结论。

规则：
1. 必须使用中文输出。
2. 不要编造数据，只基于用户提供的 JSON。
3. 如果数据全部正常，也要完整输出四节。
4. 标记为 ignorable=true 的 ES 查询为已知噪音，不计入评分，不列为异常项。
5. 如果 context.batch_window.active=true，relaxed_thresholds 中的指标异常窗口降级处理（列出但不计入评分）。
6. 不要输出任何与上述四节无关的内容，不要重复数据原文。"""


def _build_instant_payload(site_results: list[SiteResult],
                           batch_window: BatchWindow | None,
                           max_hits: int) -> dict:
    sites_data = []
    for s in site_results:
        sites_data.append({
            "site": s.label,
            "prometheus": [
                {"name": r.name, "value": r.value, "threshold": r.threshold,
                 "unit": r.unit, "is_anomaly": r.is_anomaly, "error": r.error,
                 "component": getattr(r, "component", "system"),
                 "severity": getattr(r, "severity", "warning")}
                for r in s.prom_results
            ],
            "elasticsearch": [
                {"name": r.name, "index": r.index, "total": r.total,
                 "ignorable": r.ignorable, "error": r.error,
                 "sample_hits": [
                     {"timestamp": h.timestamp, "level": h.level, "message": h.message}
                     for h in r.hits[:max_hits]
                 ]}
                for r in s.es_results
            ],
        })
    return {"mode": "instant", "sites": sites_data}


def _build_range_payload(site_results: list[SiteResult],
                         batch_window: BatchWindow | None,
                         period_start: datetime | None,
                         period_end: datetime | None,
                         max_hits: int) -> dict:
    period_str = ""
    if period_start and period_end:
        period_str = (f"{period_start.strftime('%Y-%m-%d %H:%M')} ~ "
                      f"{period_end.strftime('%Y-%m-%d %H:%M')} UTC")

    sites_data = []
    for s in site_results:
        prom_data = []
        for r in s.prom_range_results:
            item: dict = {
                "name": r.name, "threshold": r.threshold, "unit": r.unit,
                "is_anomaly": r.is_anomaly, "error": r.error,
                "stats": {
                    "min": round(r.period_min, 3) if r.period_min is not None else None,
                    "max": round(r.period_max, 3) if r.period_max is not None else None,
                    "avg": round(r.period_avg, 3) if r.period_avg is not None else None,
                },
            }
            if r.anomaly_windows:
                item["anomaly_windows"] = [
                    {"start": w.start_ts, "end": w.end_ts, "instance": w.instance,
                     "max_value": round(w.max_value, 3), "duration_minutes": w.duration_minutes}
                    for w in r.anomaly_windows
                ]
            prom_data.append(item)

        sites_data.append({
            "site": s.label,
            "prometheus": prom_data,
            "elasticsearch": [
                {"name": r.name, "index": r.index, "total": r.total,
                 "ignorable": r.ignorable, "error": r.error,
                 "sample_hits": [
                     {"timestamp": h.timestamp, "level": h.level, "message": h.message}
                     for h in r.hits[:max_hits]
                 ]}
                for r in s.es_results
            ],
        })

    return {"mode": "range", "period": period_str, "sites": sites_data}


def analyze(
    site_results: list[SiteResult],
    cfg: LLMConfig,
    batch_window: BatchWindow | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    max_hits_per_query: int = 20,
) -> str:
    api_key = os.environ.get(cfg.api_key_env)
    if not api_key:
        return f"[SKIP] 未设置环境变量 {cfg.api_key_env}，跳过 AI 分析。"

    mode = site_results[0].mode if site_results else "instant"

    context: dict = {"batch_window": {"active": False}}
    if batch_window:
        context["batch_window"] = {
            "active": True,
            "label": batch_window.label,
            "relaxed_thresholds": batch_window.relaxed_thresholds,
        }

    if mode == "range":
        data = _build_range_payload(site_results, batch_window,
                                    period_start, period_end, max_hits_per_query)
    else:
        data = _build_instant_payload(site_results, batch_window, max_hits_per_query)

    data["context"] = context
    user_text = ("以下是本次巡检采集到的数据 JSON:\n\n```json\n"
                 + json.dumps(data, ensure_ascii=False, indent=2) + "\n```")

    client = anthropic.Anthropic(api_key=api_key)
    system_blocks: list[dict] = [{"type": "text", "text": SYSTEM_PROMPT}]
    if cfg.enable_prompt_caching:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    try:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_text}],
        )
    except anthropic.APIError as exc:
        return f"[ERROR] Claude API 调用失败: {exc}"

    chunks = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "\n".join(chunks).strip() or "[WARN] AI 返回为空。"
