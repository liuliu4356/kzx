from __future__ import annotations

from dataclasses import dataclass

from ..config import Config, ESConfig, PromConfig
from .elasticsearch import ESResult, collect as es_collect
from .prometheus import PromResult, collect as prom_collect


@dataclass
class SiteResult:
    label: str
    prom_results: list[PromResult]
    es_results: list[ESResult]

    @property
    def anomaly_count(self) -> int:
        return sum(1 for r in self.prom_results if r.is_anomaly)


def collect_sites(cfg: Config) -> list[SiteResult]:
    """
    按 sites 列表逐机房采集；若未配置 sites，则用全局 URL 作为单机房采集。
    """
    if not cfg.sites:
        return [SiteResult(
            label="默认",
            prom_results=prom_collect(cfg.prometheus),
            es_results=es_collect(cfg.elasticsearch),
        )]

    results: list[SiteResult] = []
    for site in cfg.sites:
        site_prom = PromConfig(
            url=site.prometheus_url,
            timeout_sec=cfg.prometheus.timeout_sec,
            queries=cfg.prometheus.queries,
        )
        site_es = ESConfig(
            url=site.es_url or cfg.elasticsearch.url,
            username_env=cfg.elasticsearch.username_env,
            password_env=cfg.elasticsearch.password_env,
            timeout_sec=cfg.elasticsearch.timeout_sec,
            queries=cfg.elasticsearch.queries,
        )
        results.append(SiteResult(
            label=site.label,
            prom_results=prom_collect(site_prom),
            es_results=es_collect(site_es),
        ))
    return results
