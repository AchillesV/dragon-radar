"""
「趋势 → 分析」策略回测（V2 Phase 5）

用本地每日候选快照（trend_store）+ 腾讯日线，对「趋势 → 分析」的价量信号做
T+1 / T+3 / T+5 / T+10 前向收益回测。

方法（避免未来函数）：
  1. 取本地最近 N 个交易日快照（每日趋势候选池，含当日算出的放量启动日 D / D 日量 / 基准均量）；
  2. 对每个交易日 T，只用「截至 T」的日线 + 快照自带的字段（均为 T 时点信息）计算每只候选股的
     SmartMoney / RS / 生命周期 / 买点状态；
  3. 取买点状态 ∈ {突破确认, 缩量回踩, 二次启动, 趋势运行} 的综合分前 10 只作为当日「交易信号」；
  4. 用 T 之后的真实日线计算 T+1/T+3/T+5/T+10 收益（T 收盘买入 → T+h 收盘卖出），汇总
     胜率、平均收益、盈亏比、Profit Factor、期望收益、最大回撤；并按买点状态 / 生命周期分组统计。

口径与局限（会写进接口返回的 note，前端展示）：
  * 板块与资金维度（板块热度、主力净额）无法回溯到历史时点，回测中按中性处理 —— 因此回测验证的是
    「价量部分」的信号（放量启动 / 量能保持 / RS / 生命周期 / 买点），不是完整 FinalScore 排名；
  * 收益不含手续费与滑点；T+h 需要 T 之后 h 个交易日的数据，越近的日期样本越少（T+10 最少）。
"""
import datetime
import json
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

import stock_scores
import trend_store

logger = logging.getLogger(__name__)

HORIZONS: Tuple[int, ...] = (1, 3, 5, 10)
DEFAULT_SESSIONS = 30        # 默认回测最近 30 个有快照的交易日
MAX_SIGNALS = 10             # 每个交易日取前 N 只交易信号
BT_TTL = 7200                # 回测结果缓存 2 小时
HIST_TTL = 3600

_KLINE_URL = "https://ifzq.gtimg.cn/appstock/app/kline/kline"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
_HIST: Dict[str, Tuple[float, Optional[pd.DataFrame]]] = {}
_IDX: Dict[str, Tuple[float, List[Tuple[str, float]]]] = {}
_RESULT_CACHE: Dict[str, Tuple[float, dict]] = {}
_HIST_FILE = os.path.join(os.path.dirname(__file__), "data", "backtest_hist.pkl")
_REQUEST_TIMEOUT = 6
MAX_WORKERS = 16


def _load_hist_cache() -> Dict[str, pd.DataFrame]:
    """当日已落盘的回测日线缓存（跨进程复用，避免每次重启重拉数百只）。"""
    try:
        with open(_HIST_FILE, "rb") as f:
            blob = pickle.load(f)
        if blob.get("date") == datetime.date.today().strftime("%Y-%m-%d"):
            return blob.get("hist") or {}
    except Exception:
        pass
    return {}


def _save_hist_cache(hist: Dict[str, pd.DataFrame]) -> None:
    try:
        os.makedirs(os.path.dirname(_HIST_FILE), exist_ok=True)
        with open(_HIST_FILE, "wb") as f:
            pickle.dump({"date": datetime.date.today().strftime("%Y-%m-%d"), "hist": hist}, f)
    except Exception as e:
        logger.debug(f"回测日线缓存写入失败: {e}")

BUY_LABELS = stock_scores.BUY_LABELS


def _fetch_daily(code: str, days: int = 180) -> Optional[pd.DataFrame]:
    """拉取个股日线（带 1 小时缓存，保留完整历史以便按日期切片）。列同 _fetch_hist_tencent。"""
    now = time.time()
    cached = _HIST.get(code)
    if cached and now - cached[0] < HIST_TTL:
        return cached[1]

    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    full = f"{prefix}{code}"
    end_d = datetime.date.today().strftime("%Y-%m-%d")
    start_d = (datetime.date.today() - datetime.timedelta(days=260)).strftime("%Y-%m-%d")
    url = f"{_KLINE_URL}?p=1&param={full},day,{start_d},{end_d},{days}&_var=m_{full}_day"
    df: Optional[pd.DataFrame] = None
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        rows = data["data"][full]["day"]
        # 腾讯有时返回 7 列（多一个字段），只取前 6 列，避免 DataFrame 列数不匹配
        df = pd.DataFrame([r[:6] for r in rows],
                          columns=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
        for col in ["开盘", "收盘", "最高", "最低", "成交量"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["涨跌幅"] = df["收盘"].pct_change() * 100
        df = df.dropna(subset=["涨跌幅"]).reset_index(drop=True)
    except Exception as e:
        logger.debug(f"回测日线获取失败 {code}: {e}")

    _HIST[code] = (now, df)
    return df


def _index_series(code_full: str) -> List[Tuple[str, float]]:
    """指数日线 [(日期, 收盘)]，带 1 小时缓存。"""
    now = time.time()
    cached = _IDX.get(code_full)
    if cached and now - cached[0] < HIST_TTL:
        return cached[1]

    end_d = datetime.date.today().strftime("%Y-%m-%d")
    start_d = (datetime.date.today() - datetime.timedelta(days=260)).strftime("%Y-%m-%d")
    series: List[Tuple[str, float]] = []
    try:
        r = requests.get(_KLINE_URL, headers=_HEADERS, timeout=_REQUEST_TIMEOUT, params={
            "p": "1", "param": f"{code_full},day,{start_d},{end_d},180", "_var": "x",
        })
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        day = (data.get("data") or {}).get(code_full, {}).get("day") or []
        series = [(str(x[0]), float(x[2])) for x in day]
    except Exception as e:
        logger.debug(f"回测指数 K 线获取失败 {code_full}: {e}")

    _IDX[code_full] = (now, series)
    return series


def _ret5_asof(series: List[Tuple[str, float]], asof: str) -> Optional[float]:
    """指数在 asof 日（含）的近 5 个交易日累计涨跌幅 %。"""
    idx = -1
    for i, (d, _) in enumerate(series):
        if d <= asof:
            idx = i
        else:
            break
    if idx >= 5:
        prev, cur = series[idx - 5][1], series[idx][1]
        if prev > 0:
            return (cur / prev - 1) * 100
    return None


def _asof(df: pd.DataFrame, date: str) -> pd.DataFrame:
    """截取截至 date（含）的日线，避免未来函数。"""
    return df[df["日期"].astype(str) <= date].reset_index(drop=True)


def _entry_from(s) -> dict:
    return {
        "code": s.code,
        "name": s.name,
        "change_pct": s.change_pct,
        "breakout_date": s.breakout_date,
        "breakout_volume": s.breakout_volume,
        "baseline_avg_volume": s.baseline_avg_volume,
        "range_change_pct": s.range_change_pct,
        "hit_count": s.hit_count,
    }


def _forward(df: pd.DataFrame, date: str) -> Dict[int, Optional[float]]:
    """T 日收盘买入，T+h 日收盘卖出的收益（%）；同时给出区间内最大浮亏（%）。"""
    dates = [str(x) for x in df["日期"].tolist()]
    try:
        i = dates.index(date)
    except ValueError:
        return {}
    closes = [float(x) for x in df["收盘"].tolist()]
    base = closes[i]
    out: Dict[int, Optional[float]] = {}
    for h in HORIZONS:
        j = i + h
        out[h] = ((closes[j] / base - 1) * 100) if (j < len(closes) and base > 0) else None
    worst: Optional[float] = None
    for k in range(1, max(HORIZONS) + 1):
        j = i + k
        if j >= len(closes):
            break
        r = (closes[j] / base - 1) * 100
        worst = r if worst is None else min(worst, r)
    out[0] = worst        # key 0 → 区间最大浮亏（内部用）
    return out


def _agg(rets: List[float], worsts: List[float], horizon: int) -> dict:
    n = len(rets)
    if n == 0:
        return {"horizon": horizon, "samples": 0}
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    avg_win = mean(wins) if wins else None
    avg_loss = mean(losses) if losses else None
    win_rate = len(wins) / n * 100
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    payoff = (avg_win / abs(avg_loss)) if (avg_win is not None and avg_loss) else None
    expectancy = ((win_rate / 100) * (avg_win or 0.0)
                  + (1 - win_rate / 100) * (avg_loss or 0.0))
    return {
        "horizon": horizon,
        "samples": n,
        "win_rate": round(win_rate, 1),
        "avg_ret": round(mean(rets), 2),
        "median_ret": round(median(rets), 2),
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "payoff_ratio": round(payoff, 2) if payoff is not None else None,
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(mean(worsts), 2) if worsts else None,
        "best": round(max(rets), 2),
        "worst": round(min(rets), 2),
    }


def _group(trades: List[dict], key_field: str, label_map: Optional[dict] = None) -> List[dict]:
    """按字段分组，输出 T+5 的样本数/胜率/平均收益。"""
    buckets: Dict[str, List[dict]] = {}
    for t in trades:
        buckets.setdefault(str(t.get(key_field) or "—"), []).append(t)
    out = []
    for key, items in buckets.items():
        rets = [x[5] for x in items if x.get(5) is not None]
        if not rets:
            continue
        out.append({
            "key": key,
            "label": (label_map or {}).get(key, key),
            "samples": len(rets),
            "win_rate": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1),
            "avg_ret5": round(mean(rets), 2),
        })
    out.sort(key=lambda x: x["samples"], reverse=True)
    return out


def run_backtest(sessions: int = DEFAULT_SESSIONS, max_signals: int = MAX_SIGNALS) -> dict:
    """跑一次回测。返回聚合结果（dict，供 Pydantic 模型序列化）。"""
    cache_key = f"{sessions}|{max_signals}"
    now = time.time()
    cached = _RESULT_CACHE.get(cache_key)
    if cached and now - cached[0] < BT_TTL:
        return cached[1]

    dates = sorted(trend_store.list_dates(limit=500))[-sessions:]
    if not dates:
        return _empty_result("本地暂无趋势候选快照，无法回测")

    snapshots: Dict[str, List] = {}
    codes: set = set()
    for d in dates:
        stocks = trend_store.load_snapshot(d)
        if not stocks:
            continue
        snapshots[d] = stocks
        codes.update(s.code for s in stocks)
    dates = [d for d in dates if d in snapshots]
    if not dates:
        return _empty_result("本地快照为空，无法回测")

    # 一次性并发拉取所有需要的日线（每只股票只拉一次，多个日期复用）；先读当日落盘缓存
    disk = _load_hist_cache()
    for c in codes:
        df = disk.get(c)
        if df is not None and len(df) > 0:
            _HIST[c] = (time.time(), df)
    todo = [c for c in codes if _HIST.get(c) is None]
    if todo:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futs = {pool.submit(_fetch_daily, c): c for c in todo}
            for _ in as_completed(futs):
                pass
        _save_hist_cache({**disk, **{c: _HIST[c][1] for c in codes if _HIST.get(c) and _HIST[c][1] is not None}})
    hist = {c: _HIST.get(c, (0, None))[1] for c in codes}

    hs300 = _index_series(stock_scores.INDEX_HS300)
    zz1000 = _index_series(stock_scores.INDEX_ZZ1000)

    trades: List[dict] = []
    date_rows: List[dict] = []
    for d in dates:
        idx_ret = {
            stock_scores.INDEX_HS300: _ret5_asof(hs300, d),
            stock_scores.INDEX_ZZ1000: _ret5_asof(zz1000, d),
        }
        scored: List[Tuple[dict, object]] = []
        for s in snapshots[d]:
            df = hist.get(s.code)
            if df is None or len(df) < 8:
                continue
            df_asof = _asof(df, d)
            if len(df_asof) < 8:
                continue
            try:
                row = stock_scores._score_one(_entry_from(s), df_asof, None, [], idx_ret, None)
            except Exception as e:
                logger.debug(f"回测评分异常 {s.code}@{d}: {e}")
                row = None
            if row:
                scored.append((row, s))
        scored.sort(key=lambda x: x[0]["score"], reverse=True)
        picks = [x for x in scored if x[0].get("buy_status") in stock_scores.PICK_BUY_STATUS][:max_signals]

        day_rets: List[float] = []
        for row, s in picks:
            df = hist[s.code]
            fwd = _forward(df, d)
            if not fwd:
                continue
            trade = {
                "date": d, "code": s.code, "name": s.name,
                "buy_status": row.get("buy_status"),
                "lifecycle_label": row.get("lifecycle_label"),
                "score": row.get("score"),
            }
            for h in HORIZONS:
                trade[h] = fwd.get(h)
            trade["worst"] = fwd.get(0)
            if trade.get(5) is not None:
                day_rets.append(trade[5])
            trades.append(trade)

        date_rows.append({
            "date": d,
            "candidates": len(scored),
            "signals": len([x for x in picks]),
            "avg_ret5": round(mean(day_rets), 2) if day_rets else None,
            "win_rate5": round(sum(1 for r in day_rets if r > 0) / len(day_rets) * 100, 1) if day_rets else None,
        })

    stats = []
    for h in HORIZONS:
        rets = [t[h] for t in trades if t.get(h) is not None]
        worsts = [t["worst"] for t in trades if t.get(h) is not None and t.get("worst") is not None]
        stats.append(_agg(rets, worsts, h))

    result = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "date_from": dates[0],
        "date_to": dates[-1],
        "sessions": len(dates),
        "universe_size": len(codes),
        "signal_total": len(trades),
        "horizons": list(HORIZONS),
        "stats": stats,
        "by_buy_status": _group(trades, "buy_status", BUY_LABELS),
        "by_lifecycle": _group(trades, "lifecycle_label"),
        "dates": date_rows,
        "source": "tencent",
        "note": (
            "回测基于本地每日候选快照 + 腾讯日线：对每个交易日 T，仅用截至 T 的量价数据算信号，"
            "取买点可关注（突破/回踩/二次启动/趋势运行）的前 10 只，统计 T 收盘买入后 T+1/3/5/10 的收益。"
            "板块与资金维度无法回溯历史，回测按中性处理，验证的是价量信号部分；收益未计手续费与滑点。"
        ),
    }
    _RESULT_CACHE[cache_key] = (now, result)
    return result


def _empty_result(note: str) -> dict:
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "date_from": "", "date_to": "", "sessions": 0,
        "universe_size": 0, "signal_total": 0,
        "horizons": list(HORIZONS), "stats": [],
        "by_buy_status": [], "by_lifecycle": [], "dates": [],
        "source": "tencent", "note": note,
    }


# 数据源整体异常时的降级结构（保持前端可渲染）
_MOCK_BACKTEST = {
    "generated_at": "",
    "date_from": "2026-08-05", "date_to": "2026-09-10", "sessions": 12,
    "universe_size": 0, "signal_total": 0,
    "horizons": [1, 3, 5, 10],
    "stats": [
        {"horizon": 1, "samples": 0},
        {"horizon": 3, "samples": 0},
        {"horizon": 5, "samples": 0},
        {"horizon": 10, "samples": 0},
    ],
    "by_buy_status": [], "by_lifecycle": [], "dates": [],
    "source": "mock", "note": "示例数据（回测数据源异常）",
}
