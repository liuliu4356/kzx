from __future__ import annotations

import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from dotenv import load_dotenv

from .config import load_config, current_batch_window
from .collectors import collect_sites
from .analyzer import analyze
from . import reporter
from . import notifiers
from .logging_setup import setup as setup_logging

_PERIOD_CHOICES = click.Choice(["instant", "1d", "1w"])


def _resolve_period(period: str, start: str | None,
                    end: str | None) -> tuple[str, datetime | None, datetime | None]:
    """返回 (mode, period_start, period_end)。"""
    if start or end:
        fmt = "%Y-%m-%dT%H:%M"
        try:
            ps = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc) if start else None
            pe = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc) if end else None
        except ValueError:
            click.echo("--start/--end 格式须为 YYYY-MM-DDTHH:MM，如 2026-05-01T00:00", err=True)
            sys.exit(1)
        return "range", ps, pe

    if period == "instant":
        return "instant", None, None

    now = datetime.now(timezone.utc)
    days = 1 if period == "1d" else 7
    return "range", now - timedelta(days=days), now


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
@click.option("--period", type=_PERIOD_CHOICES, default="instant", show_default=True,
              help="巡检模式：instant 快照 / 1d 过去24小时 / 1w 过去7天")
@click.option("--start", default=None, metavar="YYYY-MM-DDTHH:MM",
              help="自定义时间段起始（UTC），与 --end 配合使用")
@click.option("--end", default=None, metavar="YYYY-MM-DDTHH:MM",
              help="自定义时间段结束（UTC）")
@click.option("--skip-llm", is_flag=True, help="跳过 AI 分析")
@click.option("--notify/--no-notify", default=True, show_default=True, help="是否发送通知")
@click.option("--format", "fmt", type=click.Choice(["md", "html"]), default="md",
              show_default=True, help="报告格式")
def inspect(config_path: str, output_dir: str | None, period: str,
            start: str | None, end: str | None,
            skip_llm: bool, notify: bool, fmt: str) -> None:
    setup_logging()
    load_dotenv()
    cfg = load_config(config_path)
    if output_dir:
        cfg.report.output_dir = output_dir

    mode, period_start, period_end = _resolve_period(period, start, end)

    site_labels = [s.label for s in cfg.sites] if cfg.sites else ["默认"]
    click.echo(f"[OK] 配置加载: {config_path}")
    click.echo(f"  机房: {', '.join(site_labels)}")
    click.echo(f"  模式: {mode}" + (
        f" · {period_start.strftime('%Y-%m-%d %H:%M')} ~ {period_end.strftime('%Y-%m-%d %H:%M')} UTC"
        if mode == "range" else ""
    ))
    if mode == "range":
        click.echo(f"  步长: {cfg.inspection.step_minutes} 分钟")

    batch_win = current_batch_window(cfg.batch_windows)
    if batch_win:
        click.echo(f"  [批处理窗口] 当前处于「{batch_win.label}」，部分阈值放宽")

    click.echo(f"[1/4] 采集各机房指标（{len(site_labels)} 个机房，并发执行）...")
    site_results = collect_sites(cfg, mode=mode,
                                 period_start=period_start, period_end=period_end)
    for s in site_results:
        if mode == "range":
            total_wins = s.total_anomaly_windows
            click.echo(f"      {s.label}: {len(s.prom_range_results)} 指标, "
                       f"{s.anomaly_count} 异常指标, {total_wins} 异常窗口")
        else:
            click.echo(f"      {s.label}: {len(s.prom_results)} 指标, {s.anomaly_count} 异常")

    click.echo("[2/4] ES 日志采集（已含各机房）完成")

    if skip_llm:
        click.echo("[3/4] AI 分析 (跳过)")
        ai_analysis = "_已通过 --skip-llm 跳过 AI 分析。_"
    else:
        click.echo("[3/4] AI 分析 (Claude)...")
        ai_analysis = analyze(site_results, cfg.llm, batch_win, period_start, period_end)
        click.echo("      完成")

    click.echo("[4/4] 生成报告...")
    out_path = reporter.render(site_results, ai_analysis, cfg, period_start, period_end, fmt=fmt)
    click.echo(f"[OK] 报告已写入: {out_path}")

    if notify and cfg.notifiers:
        click.echo(f"[通知] 向 {len(cfg.notifiers)} 个渠道发送摘要...")
        errs = notifiers.notify_all(cfg, site_results, out_path)
        for e in errs:
            click.echo(f"  [WARN] {e}", err=True)
        ok = len(cfg.notifiers) - len(errs)
        click.echo(f"      完成: {ok}/{len(cfg.notifiers)} 发送成功")


@cli.command("web")
@click.option("--host", default=None, help="监听地址（默认从 config.yaml 读取，未配置则为 127.0.0.1）")
@click.option("--port", default=None, type=int, help="监听端口（默认从 config.yaml 读取，未配置则为 8000）")
@click.option("--reload", is_flag=True, help="开发模式热重载")
def web(host: str | None, port: int | None, reload: bool) -> None:
    """启动 Web 可视化管理界面。"""
    setup_logging()
    try:
        import uvicorn
        import yaml
    except ImportError:
        click.echo("请先安装 web 依赖: pip install fastapi uvicorn[standard] python-multipart", err=True)
        sys.exit(1)

    # 从 config.yaml 读取 web 配置
    config_path = Path("config.yaml")
    web_host = host or "0.0.0.0"
    web_port = port or 8000

    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            web_cfg = cfg.get("web", {})
            if host is None:
                web_host = web_cfg.get("host", "127.0.0.1")
            if port is None:
                web_port = web_cfg.get("port", 8000)
        except Exception as e:
            click.echo(f"[WARN] 读取 config.yaml 失败: {e}，使用默认配置", err=True)

    click.echo(f"Web 界面启动: http://{web_host}:{web_port}")
    uvicorn.run("src.web.app:app", host=web_host, port=web_port, reload=reload)


if __name__ == "__main__":
    cli()
