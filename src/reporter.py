from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .collectors import SiteResult
from .config import Config


def render(site_results: list[SiteResult], ai_analysis: str, cfg: Config) -> Path:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    tmpl = env.get_template("report.md.j2")

    now = datetime.now(timezone.utc)
    total_anomaly_count = sum(s.anomaly_count for s in site_results)
    total_prom_count = sum(len(s.prom_results) for s in site_results)

    content = tmpl.render(
        generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        model=cfg.llm.model,
        site_results=site_results,
        total_anomaly_count=total_anomaly_count,
        total_prom_count=total_prom_count,
        ai_analysis=ai_analysis,
    )

    output_dir = Path(cfg.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = now.strftime(cfg.report.filename_format)
    out_path = output_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path
