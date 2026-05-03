from __future__ import annotations

import os
from dataclasses import dataclass

from ..config import TableMonitorConfig


@dataclass
class TableSizeResult:
    name: str
    database: str
    table: str
    size_gb: float | None
    rows: int | None
    size_threshold_gb: float
    row_threshold: int
    is_anomaly: bool
    error: str = ""
    description: str = ""
    faq: str = ""


def collect(cfg: TableMonitorConfig) -> list[TableSizeResult]:
    if not cfg.enabled or not cfg.queries:
        return []

    try:
        import pymysql
    except ImportError:
        return [
            TableSizeResult(
                name=q.name, database=q.database, table=q.table,
                size_gb=None, rows=None,
                size_threshold_gb=q.size_threshold_gb, row_threshold=q.row_threshold,
                is_anomaly=False, error="pymysql 未安装，请运行 pip install pymysql",
                description=q.description, faq=q.faq,
            )
            for q in cfg.queries
        ]

    password = os.environ.get(cfg.password_env, "")
    try:
        conn = pymysql.connect(
            host=cfg.host, port=cfg.port, user=cfg.user, password=password,
            database="information_schema", connect_timeout=cfg.timeout_sec,
            charset="utf8mb4",
        )
    except Exception as exc:
        return [
            TableSizeResult(
                name=q.name, database=q.database, table=q.table,
                size_gb=None, rows=None,
                size_threshold_gb=q.size_threshold_gb, row_threshold=q.row_threshold,
                is_anomaly=False, error=str(exc),
                description=q.description, faq=q.faq,
            )
            for q in cfg.queries
        ]

    try:
        with conn.cursor() as cur:
            placeholders = ", ".join(["(%s, %s)"] * len(cfg.queries))
            params = [v for q in cfg.queries for v in (q.database, q.table)]
            sql = f"""
                SELECT TABLE_SCHEMA, TABLE_NAME,
                    ROUND((data_length + index_length) / 1024 / 1024 / 1024, 3) AS size_gb,
                    TABLE_ROWS AS rows
                FROM TABLES
                WHERE (TABLE_SCHEMA, TABLE_NAME) IN ({placeholders})
            """
            cur.execute(sql, params)
            row_map = {(r[0], r[1]): (r[2], r[3]) for r in cur.fetchall()}

        results: list[TableSizeResult] = []
        for q in cfg.queries:
            key = (q.database, q.table)
            if key in row_map:
                size_gb_raw, rows_raw = row_map[key]
                size_gb = float(size_gb_raw) if size_gb_raw is not None else 0.0
                rows = int(rows_raw) if rows_raw is not None else 0
                size_anomaly = size_gb > q.size_threshold_gb
                row_anomaly = q.row_threshold > 0 and rows > q.row_threshold
                results.append(TableSizeResult(
                    name=q.name, database=q.database, table=q.table,
                    size_gb=size_gb, rows=rows,
                    size_threshold_gb=q.size_threshold_gb, row_threshold=q.row_threshold,
                    is_anomaly=size_anomaly or row_anomaly,
                    description=q.description, faq=q.faq,
                ))
            else:
                results.append(TableSizeResult(
                    name=q.name, database=q.database, table=q.table,
                    size_gb=None, rows=None,
                    size_threshold_gb=q.size_threshold_gb, row_threshold=q.row_threshold,
                    is_anomaly=False, error="表不存在或无权限",
                    description=q.description, faq=q.faq,
                ))
        return results
    finally:
        conn.close()
