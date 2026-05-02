from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from ..config import Config, ESConfig, PromConfig
from .elasticsearch import ESResult, collect as es_collect
from .prometheus import PromResult, collect as prom_collect
from .prometheus_range import PromRangeResult, collect_range


@dataclass
class SiteResult:
    label: str
    mode: str                                          # "instant" | "range"
    prom_results: list[PromResult] = field(default_factory=list)
    prom_range_results: list[PromRangeResult] = field(default_factory=list)
    es_results: list[ESResult] = field(default_factory=list)

    @property
    def anomaly_count(self) -> int:
        if self.mode == "range":
            return sum(1 for r in self.prom_range_results if r.is_anomaly)
        return sum(1 for r in self.prom_results if r.is_anomaly)

    @property
    def total_anomaly_windows(self) -> int:
        """仅 range 模式有效：跨所有指标的异常窗口总数。"""
        return sum(len(r.anomaly_windows) for r in self.prom_range_results)


def _make_site_prom(cfg: Config, site_url: str) -> PromConfig:
    return PromConfig(
        url=site_url,
        timeout_sec=cfg.prometheus.timeout_sec,
        queries=cfg.prometheus.queries,
    )


def _make_site_es(cfg: Config, site_es_url: str | None,
                  override_hours: int | None = None) -> ESConfig:
    queries = cfg.elasticsearch.queries
    if override_hours is not None:
        from ..config import ESQuery
        queries = [
            ESQuery(
                name=q.name, index=q.index, query_string=q.query_string,
                time_range_hours=override_hours, size=q.size, ignorable=q.ignorable,
            )
            for q in queries
        ]
    return ESConfig(
        url=site_es_url or cfg.elasticsearch.url,
        username_env=cfg.elasticsearch.username_env,
        password_env=cfg.elasticsearch.password_env,
        timeout_sec=cfg.elasticsearch.timeout_sec,
        queries=queries,
    )


def _collect_one_instant(cfg: Config, label: str,
                         prom_url: str, es_url: str | None) -> SiteResult:
    site_prom = _make_site_prom(cfg, prom_url)
    site_es = _make_site_es(cfg, es_url)
    return SiteResult(
        label=label, mode="instant",
        prom_results=prom_collect(site_prom),
        es_results=es_collect(site_es),
    )


def _collect_one_range(cfg: Config, label: str, prom_url: str, es_url: str | None,
                       start: datetime, end: datetime) -> SiteResult:
    step = cfg.inspection.step_minutes
    override_hours = max(1, int((end - start).total_seconds() / 3600) + 1)
    site_prom = _make_site_prom(cfg, prom_url)
    site_es = _make_site_es(cfg, es_url, override_hours)
    return SiteResult(
        label=label, mode="range",
        prom_range_results=collect_range(site_prom, start, end, step),
        es_results=es_collect(site_es),
    )


def collect_sites(
    cfg: Config,
    mode: str = "instant",
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> list[SiteResult]:
    """
    按 sites 列表并发采集各机房数据。
    - mode="instant"：快照（默认）
    - mode="range"：时间段审计，需传入 period_start / period_end
    未配置 sites 时，用全局 URL 作单机房降级运行。
    """
    site_list = cfg.sites if cfg.sites else [
        type("_S", (), {
            "label": "默认",
            "prometheus_url": cfg.prometheus.url,
            "es_url": None,
        })()
    ]

    def collect_one(site) -> SiteResult:
        if mode == "range":
            assert period_start and period_end
            return _collect_one_range(cfg, site.label, site.prometheus_url,
                                      site.es_url, period_start, period_end)
        return _collect_one_instant(cfg, site.label, site.prometheus_url, site.es_url)

    max_workers = min(len(site_list), 8)
    if max_workers <= 1:
        return [collect_one(site_list[0])]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(collect_one, s): i for i, s in enumerate(site_list)}
        ordered: dict[int, SiteResult] = {}
        for future in as_completed(futures):
            ordered[futures[future]] = future.result()
    return [ordered[i] for i in range(len(site_list))]
