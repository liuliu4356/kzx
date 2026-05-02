from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .collectors import SiteResult
from .config import Config


def render(
    site_results: list[SiteResult],
    ai_analysis: str,
    cfg: Config,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> Path:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    tmpl = env.get_template("report.md.j2")

    now = datetime.now(timezone.utc)
    mode = site_results[0].mode if site_results else "instant"
    total_anomaly_count = sum(s.anomaly_count for s in site_results)

    period_str = ""
    if mode == "range" and period_start and period_end:
        period_str = (f"{period_start.strftime('%Y-%m-%d %H:%M')} ~ "
                      f"{period_end.strftime('%Y-%m-%d %H:%M')} UTC"
                      f"（步长 {cfg.inspection.step_minutes} 分钟）")

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
    filename = now.strftime(cfg.report.filename_format)
    out_path = output_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path
