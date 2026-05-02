from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

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
    template_name = "report.html.j2" if fmt == "html" else "report.md.j2"
    tmpl = env.get_template(template_name)

    now = datetime.now(timezone.utc)
    mode = site_results[0].mode if site_results else "instant"
    total_anomaly_count = sum(s.anomaly_count for s in site_results)

    period_str = ""
    if mode == "range" and period_start and period_end:
        period_str = (f"{period_start.strftime('%Y-%m-%d %H:%M')} ~ "
                      f"{period_end.strftime('%Y-%m-%d %H:%M')} UTC"
                      f"（步长 {cfg.inspection.step_minutes} 分钟）")

    # 将 faq 从 config 注入到 PromResult / PromRangeResult（按 name 匹配）
    faq_map: dict[str, str] = {q.name: q.faq for q in cfg.prometheus.queries}
    for s in site_results:
        for r in s.prom_results:
            if not getattr(r, "faq", ""):
                r.faq = faq_map.get(r.name, "")  # type: ignore[attr-defined]
        for r in s.prom_range_results:
            if not getattr(r, "faq", ""):
                r.faq = faq_map.get(r.name, "")  # type: ignore[attr-defined]

    es_faq_map: dict[str, str] = {q.name: q.faq for q in cfg.elasticsearch.queries}
    for s in site_results:
        for r in s.es_results:
            if not getattr(r, "faq", ""):
                r.faq = es_faq_map.get(r.name, "")  # type: ignore[attr-defined]

    content = tmpl.render(
        generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        model=cfg.llm.model,
        mode=mode,
        period_str=period_str,
        site_results=site_results,
        total_anomaly_count=total_anomaly_count,
        ai_analysis=ai_analysis,
    )

    output_dir = Path(cfg.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = now.strftime(cfg.report.filename_format)
    if fmt == "html":
        base_name = base_name.replace(".md", "") + ".html"
    out_path = output_dir / base_name
    out_path.write_text(content, encoding="utf-8")
    return out_path
