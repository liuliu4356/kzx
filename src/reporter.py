from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from urllib.parse import quote as _urlquote

from jinja2 import Environment, FileSystemLoader

from .collectors import SiteResult
from .config import Config

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def render(
    site_results: list[SiteResult],
    ai_analysis: str,
    cfg: Config,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    fmt: Literal["md", "html"] = "md",
) -> Path:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    env.filters["urlencode"] = lambda s: _urlquote(str(s), safe="")
    template_name = "report.html.j2" if fmt == "html" else "report.md.j2"
    tmpl = env.get_template(template_name)

    now = datetime.now().astimezone()
    mode = site_results[0].mode if site_results else "instant"
    total_anomaly_count = sum(s.anomaly_count for s in site_results)

    period_str = ""
    if mode == "range" and period_start and period_end:
        period_str = (f"{period_start.strftime('%Y-%m-%d %H:%M')} ~ "
                      f"{period_end.strftime('%Y-%m-%d %H:%M')} UTC"
                      f"（步长 {cfg.inspection.step_minutes} 分钟）")

    # 将 faq / description / component / severity 从 config 注入到各 Result 对象（按 name 匹配）
    faq_map: dict[str, str] = {q.name: q.faq for q in cfg.prometheus.queries}
    desc_map: dict[str, str] = {q.name: q.description for q in cfg.prometheus.queries}
    comp_map: dict[str, str] = {q.name: q.component for q in cfg.prometheus.queries}
    sev_map: dict[str, str] = {q.name: q.severity for q in cfg.prometheus.queries}
    for s in site_results:
        for r in s.prom_results:
            if not getattr(r, "faq", ""):
                r.faq = faq_map.get(r.name, "")  # type: ignore[attr-defined]
            if not getattr(r, "description", ""):
                r.description = desc_map.get(r.name, "")  # type: ignore[attr-defined]
            r.component = comp_map.get(r.name, "system")  # type: ignore[attr-defined]
            r.severity = sev_map.get(r.name, "warning")  # type: ignore[attr-defined]
        for r in s.prom_range_results:
            if not getattr(r, "faq", ""):
                r.faq = faq_map.get(r.name, "")  # type: ignore[attr-defined]
            if not getattr(r, "description", ""):
                r.description = desc_map.get(r.name, "")  # type: ignore[attr-defined]
            r.component = comp_map.get(r.name, "system")  # type: ignore[attr-defined]
            r.severity = sev_map.get(r.name, "warning")  # type: ignore[attr-defined]

    es_faq_map: dict[str, str] = {q.name: q.faq for q in cfg.elasticsearch.queries}
    es_desc_map: dict[str, str] = {q.name: q.description for q in cfg.elasticsearch.queries}
    for s in site_results:
        for r in s.es_results:
            if not getattr(r, "faq", ""):
                r.faq = es_faq_map.get(r.name, "")  # type: ignore[attr-defined]
            if not getattr(r, "description", ""):
                r.description = es_desc_map.get(r.name, "")  # type: ignore[attr-defined]

    content = tmpl.render(
        generated_at=now.strftime("%Y-%m-%d %H:%M"),
        model=cfg.llm.model,
        mode=mode,
        period_str=period_str,
        site_results=site_results,
        total_anomaly_count=total_anomaly_count,
        ai_analysis=ai_analysis,
        kibana_url=cfg.elasticsearch.kibana_url.rstrip("/"),
    )

    output_dir = Path(cfg.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = now.strftime(cfg.report.filename_format)
    if fmt == "html":
        base_name = base_name.replace(".md", "") + ".html"
    out_path = output_dir / base_name
    out_path.write_text(content, encoding="utf-8")
    return out_path
