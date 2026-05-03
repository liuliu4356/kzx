"""集中日志配置：RotatingFileHandler + 控制台输出。"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH: Path = Path("logs/sanssi.log")


def setup(log_dir: str = "logs", level: str = "INFO") -> None:
    global LOG_PATH
    LOG_PATH = Path(log_dir) / "sanssi.log"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)

    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_log_path() -> str:
    return str(LOG_PATH.resolve())


def tail_log(lines: int = 200) -> list[str]:
    if not LOG_PATH.exists():
        return []
    try:
        text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        return all_lines[-lines:]
    except Exception:
        return []
