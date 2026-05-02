from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .config import load_config, current_batch_window
from .collectors import collect_sites
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
        click.echo("缺少 config.example.yaml，无法初始化", err=True)
        sys.exit(1)
    if dst.exists() and not force:
        click.echo("config.yaml 已存在，使用 --force 覆盖", err=True)
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

    site_labels = [s.label for s in cfg.sites] if cfg.sites else ["默认"]
    click.echo(f"[OK] 配置加载: {config_path}")
    click.echo(f"  机房: {', '.join(site_labels)}")
    click.echo(f"  Prometheus 查询: {len(cfg.prometheus.queries)} 条")
    click.echo(f"  ES 查询: {len(cfg.elasticsearch.queries)} 条")
    click.echo(f"  LLM: {cfg.llm.provider} / {cfg.llm.model}")
    click.echo(f"  Report: {cfg.report.output_dir} ({cfg.report.language})")

    batch_win = current_batch_window(cfg.batch_windows)
    if batch_win:
        click.echo(f"  [批处理窗口] 当前处于「{batch_win.label}」，部分阈值放宽")

    click.echo(f"[1/4] 采集各机房指标 ({len(site_labels)} 个机房)...")
    site_results = collect_sites(cfg)
    total_anomaly = sum(s.anomaly_count for s in site_results)
    total_prom = sum(len(s.prom_results) for s in site_results)
    for s in site_results:
        click.echo(f"      {s.label}: {len(s.prom_results)} 指标, {s.anomaly_count} 异常")
    click.echo(f"      合计: {total_prom} 指标, {total_anomaly} 异常")

    click.echo("[2/4] 采集 ES 日志 (已含各机房)...")
    total_es = sum(len(s.es_results) for s in site_results)
    click.echo(f"      完成: {total_es} 条查询结果")

    if skip_llm:
        click.echo("[3/4] AI 分析 (跳过)")
        ai_analysis = "_已通过 --skip-llm 跳过 AI 分析。_"
    else:
        click.echo("[3/4] AI 分析 (Claude)...")
        ai_analysis = analyze(site_results, cfg.llm, batch_win)
        click.echo("      完成")

    click.echo("[4/4] 生成报告...")
    out_path = reporter.render(site_results, ai_analysis, cfg)
    click.echo(f"[OK] 报告已写入: {out_path}")

    if notify and cfg.notifiers:
        click.echo(f"[通知] 向 {len(cfg.notifiers)} 个渠道发送摘要...")
        errs = notifiers.notify_all(cfg, site_results, out_path)
        for e in errs:
            click.echo(f"  [WARN] {e}", err=True)
        ok = len(cfg.notifiers) - len(errs)
        click.echo(f"      完成: {ok}/{len(cfg.notifiers)} 发送成功")


if __name__ == "__main__":
    cli()
