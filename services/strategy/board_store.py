"""
「打板」选股本地持久化 —— SQLite 存储每日最终快照与预选快照

设计目标：
  1. 每个交易日只在首次最终计算时落库一次，避免重复全市场扫描。
  2. 支持按日期查询历史快照，供前端「近 10 天」下拉筛选使用。
  3. 预选在收盘后（每交易日 15:30）自动计算并落库，供次日直接展示。
  4. 只保留最近 10 个交易日的快照，超出部分自动清理。
  5. 后台自动任务与接口可能并发访问，所有 DB 操作统一加线程锁。

不引入 SQLAlchemy/额外依赖，沿用 trend_store 的标准库 sqlite3 方案。
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Tuple

from models import BoardPick

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "board.db")

KEEP_DAYS = 10

_CONN: Optional[sqlite3.Connection] = None
_DB_LOCK = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS board_snapshot (
                date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                rank INTEGER NOT NULL,
                is_top INTEGER NOT NULL DEFAULT 0,
                open_pct REAL,
                price REAL,
                close REAL,
                prev_close REAL,
                change_pct REAL,
                volume REAL,
                industry TEXT,
                limit_up_date TEXT,
                description TEXT,
                PRIMARY KEY (date, code)
            )
            """
        )
        _CONN.execute(
            "CREATE TABLE IF NOT EXISTS board_day (date TEXT PRIMARY KEY)"
        )
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS board_pre (
                source_date TEXT PRIMARY KEY,
                target_date TEXT NOT NULL,
                payload TEXT NOT NULL,
                lhb_ready INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        _CONN.execute("CREATE INDEX IF NOT EXISTS idx_board_snapshot_date ON board_snapshot(date)")
        _CONN.commit()
    return _CONN


def _prune(conn: sqlite3.Connection) -> None:
    """只保留最近 KEEP_DAYS 个有快照的交易日。"""
    dates = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT date FROM board_snapshot ORDER BY date DESC"
        ).fetchall()
    ]
    if len(dates) > KEEP_DAYS:
        cutoff = dates[KEEP_DAYS - 1]
        conn.execute("DELETE FROM board_snapshot WHERE date < ?", (cutoff,))
        conn.execute("DELETE FROM board_day WHERE date < ?", (cutoff,))


def _prune_pre(conn: sqlite3.Connection) -> None:
    """预选快照同样只保留最近 KEEP_DAYS 个首板日。"""
    dates = [
        r[0]
        for r in conn.execute(
            "SELECT source_date FROM board_pre ORDER BY source_date DESC"
        ).fetchall()
    ]
    if len(dates) > KEEP_DAYS:
        conn.execute("DELETE FROM board_pre WHERE source_date < ?", (dates[KEEP_DAYS - 1],))


def save_pre(
    source_date: str,
    target_date: str,
    picks: List[BoardPick],
    lhb_ready: bool = False,
) -> None:
    """
    保存某首板日的预选结果（覆盖式），供下一交易日直接展示。

    lhb_ready 记录计算时当日龙虎榜数据是否已可用：为 False 时，
    若后续龙虎榜发布，读取时会重新计算一次以应用「换手率+净卖出」过滤。
    """
    payload = json.dumps([p.model_dump() for p in picks], ensure_ascii=False)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _DB_LOCK:
        conn = _get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO board_pre (source_date, target_date, payload, lhb_ready, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_date, target_date, payload, 1 if lhb_ready else 0, created_at),
        )
        conn.commit()
        _prune_pre(conn)


def load_pre(source_date: str) -> Optional[Tuple[str, List[BoardPick], bool]]:
    """读取某首板日的预选快照，返回 (下一交易日, 结果, 龙虎榜是否已可用)；无记录返回 None。"""
    with _DB_LOCK:
        row = _get_conn().execute(
            "SELECT target_date, payload, lhb_ready FROM board_pre WHERE source_date = ?",
            (source_date,),
        ).fetchone()
    if row is None:
        return None
    try:
        picks = [BoardPick(**d) for d in json.loads(row[1])]
    except Exception:
        return None
    return row[0], picks, bool(row[2])


def has_snapshot(date: str) -> bool:
    """当天是否已经落库（空结果也会落库，用于区分「没算过」和「算过但为空」）。"""
    with _DB_LOCK:
        conn = _get_conn()
        if conn.execute(
            "SELECT 1 FROM board_snapshot WHERE date = ? LIMIT 1", (date,)
        ).fetchone() is not None:
            return True
        return conn.execute(
            "SELECT 1 FROM board_day WHERE date = ? LIMIT 1", (date,)
        ).fetchone() is not None


def save_snapshot(date: str, picks: List[BoardPick]) -> None:
    """保存某一天的最终选股结果；同日期重复保存会先清空再写入（覆盖式刷新）。"""
    with _DB_LOCK:
        conn = _get_conn()
        conn.execute("DELETE FROM board_snapshot WHERE date = ?", (date,))
        conn.executemany(
            """
            INSERT INTO board_snapshot (
                date, code, name, rank, is_top, open_pct, price, close, prev_close,
                change_pct, volume, industry, limit_up_date, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    date, p.code, p.name, p.rank, 1 if p.is_top else 0, p.open_pct,
                    p.price, p.close, p.prev_close, p.change_pct, p.volume,
                    p.industry, p.limit_up_date, p.description,
                )
                for p in picks
            ],
        )
        conn.execute("INSERT OR IGNORE INTO board_day (date) VALUES (?)", (date,))
        conn.commit()
        _prune(conn)


def load_snapshot(date: str) -> List[BoardPick]:
    """按日期查询最终快照，按名次升序。"""
    with _DB_LOCK:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT date, code, name, rank, is_top, open_pct, price, close, prev_close,
                   change_pct, volume, industry, limit_up_date, description
            FROM board_snapshot WHERE date = ? ORDER BY rank ASC
            """,
            (date,),
        ).fetchall()
    return [
        BoardPick(
            date=r[0], stage="final", code=r[1], name=r[2], rank=r[3], is_top=bool(r[4]),
            open_pct=r[5], price=r[6], close=r[7], prev_close=r[8] or 0.0,
            change_pct=r[9] or 0.0, volume=r[10], industry=r[11],
            limit_up_date=r[12], description=r[13],
        )
        for r in rows
    ]


def list_dates(limit: int = KEEP_DAYS) -> List[str]:
    """最近 N 个有快照的交易日，倒序（供前端下拉框使用）。"""
    with _DB_LOCK:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT date FROM (
                SELECT DISTINCT date FROM board_snapshot
                UNION
                SELECT date FROM board_day
            ) ORDER BY date DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [r[0] for r in rows]
