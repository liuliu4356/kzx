from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class PromQuery:
    name: str
    promql: str
    threshold: float
    unit: str = ""
    anomaly_when: Literal["gt", "lt"] = "gt"


@dataclass
class PromConfig:
    url: str
    timeout_sec: int
    queries: list[PromQuery]


@dataclass
class ESQuery:
    name: str
    index: str
    query_string: str
    time_range_hours: int
    size: int


@dataclass
class ESConfig:
    url: str
    username_env: str | None
    password_env: str | None
    timeout_sec: int
    queries: list[ESQuery]


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key_env: str
    max_tokens: int
    enable_prompt_caching: bool


@dataclass
class ReportConfig:
    output_dir: str
    language: str
    filename_format: str


@dataclass
class NotifierItem:
    type: str          # "dingtalk" | "feishu"
    webhook_env: str   # 环境变量名，值为完整 webhook URL
    mention_all: bool = False  # 仅钉钉支持


@dataclass
class BatchWindow:
    label: str                              # 窗口说明，如"日终批处理"
    start_hour: int                         # 开始小时（本地时间，0-23）
    end_hour: int                           # 结束小时（本地时间，0-23，可跨零点）
    relaxed_thresholds: dict[str, float] = field(default_factory=dict)
    # key 为 PromQuery.name，value 为批处理期间放宽的阈值


@dataclass
class Config:
    prometheus: PromConfig
    elasticsearch: ESConfig
    llm: LLMConfig
    report: ReportConfig
    notifiers: list[NotifierItem] = field(default_factory=list)
    batch_windows: list[BatchWindow] = field(default_factory=list)


def current_batch_window(windows: list[BatchWindow]) -> BatchWindow | None:
    """返回当前时刻所处的批处理窗口，无则返回 None。"""
    hour = datetime.now(timezone.utc).hour  # 统一用 UTC，配置也需对齐
    for w in windows:
        if w.start_hour <= w.end_hour:
            if w.start_hour <= hour < w.end_hour:
                return w
        else:
            # 跨零点，如 22:00–04:00
            if hour >= w.start_hour or hour < w.end_hour:
                return w
    return None


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    p = raw["prometheus"]
    prom = PromConfig(
        url=p["url"],
        timeout_sec=int(p.get("timeout_sec", 10)),
        queries=[
            PromQuery(
                name=q["name"],
                promql=q["promql"],
                threshold=float(q["threshold"]),
                unit=q.get("unit", ""),
                anomaly_when=q.get("anomaly_when", "gt"),
            )
            for q in p.get("queries", [])
        ],
    )

    e = raw["elasticsearch"]
    es = ESConfig(
        url=e["url"],
        username_env=e.get("username_env"),
        password_env=e.get("password_env"),
        timeout_sec=int(e.get("timeout_sec", 10)),
        queries=[
            ESQuery(
                name=q["name"],
                index=q["index"],
                query_string=q["query_string"],
                time_range_hours=int(q["time_range_hours"]),
                size=int(q["size"]),
            )
            for q in e.get("queries", [])
        ],
    )

    l = raw["llm"]
    llm = LLMConfig(
        provider=l["provider"],
        model=l["model"],
        api_key_env=l["api_key_env"],
        max_tokens=int(l.get("max_tokens", 2048)),
        enable_prompt_caching=bool(l.get("enable_prompt_caching", True)),
    )

    r = raw["report"]
    report = ReportConfig(
        output_dir=r.get("output_dir", "reports"),
        language=r.get("language", "zh-CN"),
        filename_format=r.get("filename_format", "%Y-%m-%d-%H%M.md"),
    )

    notifiers = [
        NotifierItem(
            type=n["type"],
            webhook_env=n["webhook_env"],
            mention_all=bool(n.get("mention_all", False)),
        )
        for n in raw.get("notifiers", [])
    ]

    batch_windows = [
        BatchWindow(
            label=bw["label"],
            start_hour=int(bw["start_hour"]),
            end_hour=int(bw["end_hour"]),
            relaxed_thresholds={
                k: float(v) for k, v in bw.get("relaxed_thresholds", {}).items()
            },
        )
        for bw in raw.get("batch_windows", [])
    ]

    return Config(prometheus=prom, elasticsearch=es, llm=llm, report=report,
                  notifiers=notifiers, batch_windows=batch_windows)


def get_es_auth(cfg: ESConfig) -> tuple[str, str] | None:
    if not cfg.username_env or not cfg.password_env:
        return None
    user = os.environ.get(cfg.username_env)
    pw = os.environ.get(cfg.password_env)
    if user and pw:
        return (user, pw)
    return None
