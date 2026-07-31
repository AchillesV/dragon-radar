"""
「趋势」信号本地持久化 —— SQLite 存储每日扫描快照

设计目标（对应 issue 需求）：
  1. 扫描结果落库，同一交易日内不重复全市场扫描，只有当天没有数据时才扫描。
  2. 按日期查询历史快照，供前端「近10天」下拉筛选使用。
  3. 基于历史快照计算「连续入选天数」，供前端标注 + 排序使用。

不引入 SQLAlchemy/额外依赖，用标准库 sqlite3 即可满足单机小数据量场景。
"""
import os
import sqlite3
from typing import Dict, List, Optional

from models import TrendStock

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "trend.db")

_CONN: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS trend_snapshot (
                date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL,
                change REAL,
                change_pct REAL,
                industry TEXT,
                breakout_date TEXT,
                breakout_volume REAL,
                baseline_avg_volume REAL,
                range_window TEXT,
                range_change_pct REAL,
                description TEXT,
                PRIMARY KEY (date, code)
            )
            """
        )
        _CONN.execute("CREATE INDEX IF NOT EXISTS idx_trend_snapshot_date ON trend_snapshot(date)")
        _CONN.commit()
    return _CONN


def save_snapshot(date: str, stocks: List[TrendStock]) -> None:
    """保存某一天的扫描结果；同日期重复保存会先清空再写入（覆盖式刷新）"""
    conn = _get_conn()
    conn.execute("DELETE FROM trend_snapshot WHERE date = ?", (date,))
    conn.executemany(
        """
        INSERT INTO trend_snapshot (
            date, code, name, price, change, change_pct, industry,
            breakout_date, breakout_volume, baseline_avg_volume,
            range_window, range_change_pct, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                date, s.code, s.name, s.price, s.change, s.change_pct, s.industry,
                s.breakout_date, s.breakout_volume, s.baseline_avg_volume,
                s.range_window, s.range_change_pct, s.description,
            )
            for s in stocks
        ],
    )
    conn.commit()


def load_snapshot(date: str) -> List[TrendStock]:
    """按日期查询快照，按放量日倒序（与全市场扫描的默认排序一致）"""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT code, name, price, change, change_pct, industry,
               breakout_date, breakout_volume, baseline_avg_volume,
               range_window, range_change_pct, description
        FROM trend_snapshot WHERE date = ? ORDER BY breakout_date DESC
        """,
        (date,),
    ).fetchall()
    return [
        TrendStock(
            code=r[0], name=r[1], price=r[2], change=r[3], change_pct=r[4] or 0.0,
            industry=r[5], breakout_date=r[6], breakout_volume=r[7] or 0.0,
            baseline_avg_volume=r[8] or 0.0, range_window=r[9] or "",
            range_change_pct=r[10] or 0.0, description=r[11],
        )
        for r in rows
    ]


def list_dates(limit: int = 10) -> List[str]:
    """最近 N 个有快照的交易日，倒序（供前端下拉框使用）"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT date FROM trend_snapshot ORDER BY date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [r[0] for r in rows]


def compute_streaks(target_date: str, lookback: int = 10) -> Dict[str, int]:
    """
    计算 target_date 当天每只入选股票「从当天往前连续入选」的天数。
    只统计数据库里实际有快照的交易日（跳过没跑过扫描的日子），
    从 target_date 开始往前数，一旦某天不再包含该股票即停止累加。
    """
    conn = _get_conn()
    dates = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT date FROM trend_snapshot WHERE date <= ? ORDER BY date DESC LIMIT ?",
            (target_date, lookback),
        ).fetchall()
    ]
    if not dates or dates[0] != target_date:
        return {}

    code_sets = [
        {r[0] for r in conn.execute("SELECT code FROM trend_snapshot WHERE date = ?", (d,)).fetchall()}
        for d in dates
    ]

    streak: Dict[str, int] = {}
    for code in code_sets[0]:
        n = 0
        for codes in code_sets:
            if code in codes:
                n += 1
            else:
                break
        streak[code] = n
    return streak
