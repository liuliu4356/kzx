from __future__ import annotations

import json
import os

import anthropic

from .collectors import SiteResult
from .config import BatchWindow, LLMConfig

SYSTEM_PROMPT = """你是一位资深 SRE 巡检助手，负责审阅基于 Prometheus 指标与 Elasticsearch 日志的系统巡检数据。
数据可能来自多个机房，请分机房分析后给出整体结论。

请严格按以下 Markdown 结构输出（不要添加其他节）：

## 健康度评分
- 给出 0-100 的总体评分，并一句话说明依据。
- 若有多机房，给出各机房子评分。

## 异常项
- 列出需要关注的指标或日志（若无异常，写"无"）。
- 每项注明机房、来源（metric/log）、名称、当前值/片段、阈值或异常原因。

## 建议动作
- 针对异常项给出可执行的排查或修复动作。
- 按优先级 P0 / P1 / P2 标注。

## 总结
- 3-5 句话结论。

规则：
1. 必须使用中文输出。
2. 不要编造数据，只基于用户提供的 JSON。
3. 如果数据全部正常，也要完整输出四节。
4. 标记为 ignorable=true 的 ES 查询为已知噪音，不计入评分，不列为异常项。
5. 如果 context.batch_window.active=true，则 relaxed_thresholds 中的指标不视为异常。
6. 不要输出任何与上述四节无关的内容，不要重复数据原文。"""


def _build_user_payload(site_results: list[SiteResult],
                        batch_window: BatchWindow | None = None,
                        max_hits_per_query: int = 20) -> str:
    context: dict = {}
    if batch_window:
        context["batch_window"] = {
            "active": True,
            "label": batch_window.label,
            "note": f"当前处于【{batch_window.label}】时间窗口，以下指标在此期间属已知正常波动",
            "relaxed_thresholds": batch_window.relaxed_thresholds,
        }
    else:
        context["batch_window"] = {"active": False}

    sites_payload = []
    for s in site_results:
        prom_compact = [
            {
                "name": r.name,
                "value": r.value,
                "threshold": r.threshold,
                "unit": r.unit,
                "is_anomaly": r.is_anomaly,
                "error": r.error,
            }
            for r in s.prom_results
        ]
        es_compact = [
            {
                "name": r.name,
                "index": r.index,
                "query": r.query_string,
                "total": r.total,
                "ignorable": r.ignorable,
                "error": r.error,
                "sample_hits": [
                    {"timestamp": h.timestamp, "level": h.level, "message": h.message}
                    for h in r.hits[:max_hits_per_query]
                ],
            }
            for r in s.es_results
        ]
        sites_payload.append({
            "site": s.label,
            "prometheus": prom_compact,
            "elasticsearch": es_compact,
        })

    payload = {"context": context, "sites": sites_payload}
    return "以下是本次巡检采集到的数据 JSON:\n\n```json\n" + \
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"


def analyze(site_results: list[SiteResult],
            cfg: LLMConfig,
            batch_window: BatchWindow | None = None) -> str:
    api_key = os.environ.get(cfg.api_key_env)
    if not api_key:
        return f"[SKIP] 未设置环境变量 {cfg.api_key_env}，跳过 AI 分析。"

    client = anthropic.Anthropic(api_key=api_key)

    system_blocks: list[dict] = [{"type": "text", "text": SYSTEM_PROMPT}]
    if cfg.enable_prompt_caching:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    user_text = _build_user_payload(site_results, batch_window)

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
