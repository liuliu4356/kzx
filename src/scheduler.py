from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_inspection(cfg_path: str, job_id: str) -> None:
    """巡检任务执行体，由 APScheduler 调用。"""
    from .web import config_store as cs
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        from .config import load_config, current_batch_window
        from .collectors import collect_sites
        from .analyzer import analyze
        from . import reporter
        from dotenv import load_dotenv
        import yaml

        load_dotenv()
        cfg = load_config(cfg_path)

        raw = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8")) or {}
        job_cfg = next(
            (j for j in raw.get("cron_jobs", []) if j.get("id") == job_id), {}
        )
        mode = job_cfg.get("mode", "instant")
        period_hours = int(job_cfg.get("period_hours", 24))
        fmt = job_cfg.get("fmt", "html")
        notify = bool(job_cfg.get("notify", True))
        label = job_cfg.get("label", job_id)

        period_start = period_end = None
        if mode == "range":
            period_end = datetime.now(timezone.utc)
            period_start = period_end - timedelta(hours=period_hours)

        batch_win = current_batch_window(cfg.batch_windows)
        logger.info("[cron:%s] 开始巡检 mode=%s", label, mode)

        site_results = collect_sites(
            cfg, mode=mode, period_start=period_start, period_end=period_end
        )
        anomaly_total = sum(s.anomaly_count for s in site_results)

        ai_analysis = analyze(
            site_results, cfg.llm, batch_win, period_start, period_end
        )

        out_path = reporter.render(
            site_results, ai_analysis, cfg, period_start, period_end, fmt=fmt
        )
        logger.info("[cron:%s] 报告已生成: %s，异常 %d 项", label, out_path.name, anomaly_total)

        cs.add_cron_history(job_id, {
            "started_at": started_at,
            "status": "ok",
            "report": out_path.name,
            "anomalies": anomaly_total,
        })

        if notify and cfg.notifiers:
            from .notifiers import notify_all
            notify_all(site_results, cfg, out_path)

    except Exception as exc:
        logger.exception("[cron:%s] 巡检失败: %s", job_id, exc)
        cs.add_cron_history(job_id, {
            "started_at": started_at,
            "status": "fail",
            "error": str(exc),
        })


def setup_scheduler(cfg_path: str):
    """初始化并返回 APScheduler BackgroundScheduler，加载 config.yaml 中的 cron_jobs。"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        import yaml
    except ImportError:
        logger.warning("apscheduler 未安装，定时任务功能不可用。请运行 pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="local")
    _load_jobs(scheduler, cfg_path)
    return scheduler


def _load_jobs(scheduler, cfg_path: str) -> None:
    import yaml
    raw = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8")) or {}
    for job in raw.get("cron_jobs", []):
        if not job.get("enabled", True):
            continue
        job_id = job["id"]
        cron_expr = job.get("cron_expr", "")
        parts = cron_expr.split()
        if len(parts) != 5:
            logger.warning("[cron] job %s cron_expr 格式错误: %s", job_id, cron_expr)
            continue
        minute, hour, day, month, day_of_week = parts
        try:
            scheduler.add_job(
                _run_inspection,
                trigger="cron",
                id=job_id,
                args=[cfg_path, job_id],
                minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
                replace_existing=True,
                misfire_grace_time=300,
            )
            logger.info("[cron] 已注册任务: %s  expr=%s", job["label"], cron_expr)
        except Exception as exc:
            logger.warning("[cron] 注册任务 %s 失败: %s", job_id, exc)


def reload_jobs(scheduler, cfg_path: str) -> None:
    """热更新：移除所有现有任务，重新从 config.yaml 加载。"""
    if scheduler is None:
        return
    for job in scheduler.get_jobs():
        job.remove()
    _load_jobs(scheduler, cfg_path)
    logger.info("[cron] 任务已重新加载")
