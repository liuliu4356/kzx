from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .collectors.elasticsearch import ESResult
from .collectors.prometheus import PromResult
from .config import Config


def render(
    prom_results: list[PromResult],
    es_results: list[ESResult],
    ai_analysis: str,
    cfg: Config,
) -> Path:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    tmpl = env.get_template("report.md.j2")

    now = datetime.now(timezone.utc)
    anomaly_count = sum(1 for r in prom_results if r.is_anomaly)

    content = tmpl.render(
        generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        model=cfg.llm.model,
        prom_url=cfg.prometheus.url,
        es_url=cfg.elasticsearch.url,
        anomaly_count=anomaly_count,
        prom_results=prom_results,
        es_results=es_results,
        ai_analysis=ai_analysis,
    )

    output_dir = Path(cfg.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = now.strftime(cfg.report.filename_format)
    out_path = output_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path
