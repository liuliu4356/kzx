from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .config import load_config, current_batch_window
from .collectors import prometheus as prom_collector
from .collectors import elasticsearch as es_collector
from .analyzer import analyze
from . import reporter
from . import notifiers


@click.group()
def cli() -> None:
    """Prometheus + ELK 自动巡检 CLI."""


@cli.command("init-config")
@click.option("--force", is_flag=True, help="覆盖已存在的 config.yaml")
def init_config(force: bool) -> None:
    src = Path("config.example.yaml")
    dst = Path("config.yaml")
    if not src.exists():
        click.echo("缺少 config.example.yaml,无法初始化", err=True)
        sys.exit(1)
    if dst.exists() and not force:
        click.echo("config.yaml 已存在,使用 --force 覆盖", err=True)
        sys.exit(1)
    shutil.copy(src, dst)
    click.echo(f"已生成 {dst}")


@cli.command("inspect")
@click.option("--config", "config_path", default="config.yaml", show_default=True)
@click.option("--output-dir", default=None, help="覆盖配置中的输出目录")
@click.option("--skip-llm", is_flag=True, help="跳过 AI 分析，直接生成原始报告")
@click.option("--notify/--no-notify", default=True, show_default=True, help="是否发送通知")
def inspect(config_path: str, output_dir: str | None,
            skip_llm: bool, notify: bool) -> None:
    load_dotenv()
    cfg = load_config(config_path)
    if output_dir:
        cfg.report.output_dir = output_dir

    click.echo(f"[OK] 配置加载: {config_path}")
    click.echo(f"  Prometheus: {cfg.prometheus.url} ({len(cfg.prometheus.queries)} 个查询)")
    click.echo(f"  ES:         {cfg.elasticsearch.url} ({len(cfg.elasticsearch.queries)} 个查询)")
    click.echo(f"  LLM:        {cfg.llm.provider} / {cfg.llm.model}")
    click.echo(f"  Report:     {cfg.report.output_dir} ({cfg.report.language})")

    click.echo("[1/4] 采集 Prometheus 指标...")
    prom_results = prom_collector.collect(cfg.prometheus)
    anomaly_count = sum(1 for r in prom_results if r.is_anomaly)
    click.echo(f"      完成: {len(prom_results)} 项, {anomaly_count} 项异常")

    click.echo("[2/4] 采集 Elasticsearch 日志...")
    es_results = es_collector.collect(cfg.elasticsearch)
    click.echo(f"      完成: {len(es_results)} 项查询")

    batch_win = current_batch_window(cfg.batch_windows)
    if batch_win:
        click.echo(f"  [批处理窗口] 当前处于「{batch_win.label}」，部分阈值放宽")

    if skip_llm:
        click.echo("[3/4] AI 分析 (跳过)")
        ai_analysis = "_已通过 --skip-llm 跳过 AI 分析。_"
    else:
        click.echo("[3/4] AI 分析 (Claude)...")
        ai_analysis = analyze(prom_results, es_results, cfg.llm, batch_win)
        click.echo("      完成")

    click.echo("[4/4] 生成报告...")
    out_path = reporter.render(prom_results, es_results, ai_analysis, cfg)
    click.echo(f"[OK] 报告已写入: {out_path}")

    if notify and cfg.notifiers:
        click.echo(f"[通知] 向 {len(cfg.notifiers)} 个渠道发送摘要...")
        errs = notifiers.notify_all(cfg, prom_results, out_path)
        for e in errs:
            click.echo(f"  [WARN] {e}", err=True)
        ok = len(cfg.notifiers) - len(errs)
        click.echo(f"      完成: {ok}/{len(cfg.notifiers)} 发送成功")


if __name__ == "__main__":
    cli()
