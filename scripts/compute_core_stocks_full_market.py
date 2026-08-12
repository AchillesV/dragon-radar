"""
全市场核心票扫描脚本：对沪深京全部 A 股拉取腾讯 K 线真实历史行情，
计算 2026-04-01 ~ 2026-06-30 区间累计涨跌幅，筛出累计涨幅 >= 80% 的股票。

按用户最新要求（issue WHT-8 评论）：
  - 不再限定科技子板块/候选池，全市场扫描
  - 过滤创业板（300/301/302 开头）、科创板（688/689 开头）、ST 股票
  - 结果写入 services/strategy/mainline_universe.py 的 CORE_STOCKS

跑一次即可，不是服务运行时代码。
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

START = "2026-04-01"
END = "2026-06-30"
FETCH_START = "2026-03-20"  # 留一点缓冲，确保能取到 4/1 前后最近交易日
FETCH_END = "2026-07-05"
GAIN_THRESHOLD = 80.0

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_stock_list() -> list[tuple[str, str]]:
    """Sina 沪深京 A 股全量列表（分页拉取），返回 [(code, name), ...]"""
    codes: list[tuple[str, str]] = []
    page = 1
    while True:
        url = (
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            "Market_Center.getHQNodeData"
            f"?page={page}&num=100&sort=symbol&asc=1&node=hs_a"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        items = r.json()
        if not items:
            break
        for it in items:
            codes.append((str(it["code"]), str(it["name"])))
        if len(items) < 100:
            break
        page += 1
        time.sleep(0.15)
    return codes


def is_qualified(code: str, name: str) -> bool:
    """过滤创业板（300/301/302）、科创板（688/689）和 ST 股票"""
    if code.startswith(("300", "301", "302", "688", "689")):
        return False
    if "ST" in name.upper():
        return False
    return True


def fetch_kline(code: str) -> pd.DataFrame | None:
    prefix = "sh" if code.startswith(("6", "9")) else ("bj" if code.startswith(("8", "4")) else "sz")
    full = f"{prefix}{code}"
    url = (
        f"https://ifzq.gtimg.cn/appstock/app/kline/kline"
        f"?p=1&param={full},day,{FETCH_START},{FETCH_END},320&_var=m_{full}_day"
    )
    for attempt in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            text = r.text
            data = json.loads(text[text.index("=") + 1:])
            rows = data["data"][full]["day"]
            rows = [r[:6] for r in rows]
            df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "vol"])
            for c in ["open", "close", "high", "low", "vol"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
            else:
                return None
    return None


def compute_gain(code: str, name: str) -> dict | None:
    df = fetch_kline(code)
    if df is None or df.empty:
        return None
    start_rows = df[df["date"] >= START]
    end_rows = df[df["date"] <= END]
    if start_rows.empty or end_rows.empty:
        return None
    start_price = float(start_rows.iloc[0]["close"])
    start_date = str(start_rows.iloc[0]["date"])
    end_price = float(end_rows.iloc[-1]["close"])
    end_date = str(end_rows.iloc[-1]["date"])
    if start_price <= 0:
        return None
    gain_pct = round((end_price / start_price - 1) * 100, 1)
    return {
        "code": code, "name": name,
        "start_date": start_date, "start_price": start_price,
        "end_date": end_date, "end_price": end_price,
        "gain_pct": gain_pct,
    }


def main():
    print("拉取全市场股票列表 ...")
    all_stocks = fetch_stock_list()
    print(f"全市场 A 股总数: {len(all_stocks)}")

    qualified = [(c, n) for c, n in all_stocks if is_qualified(c, n)]
    print(f"过滤创业板/科创板/ST 后剩余: {len(qualified)}")

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(compute_gain, code, name): code for code, name in qualified}
        done = 0
        for fut in as_completed(futs):
            code = futs[fut]
            done += 1
            try:
                r = fut.result()
                if r:
                    results[code] = r
            except Exception as e:
                print(f"  [ERR] {code}: {e}")
            if done % 300 == 0:
                print(f"  progress {done}/{len(qualified)}")

    core = {c: r for c, r in results.items() if r["gain_pct"] >= GAIN_THRESHOLD}
    print(f"\n成功获取行情: {len(results)}/{len(qualified)}")
    print(f"区间累计涨幅 >= {GAIN_THRESHOLD}% 的核心票: {len(core)}")

    with open("scripts/core_stock_results_full_market.json", "w", encoding="utf-8") as f:
        json.dump({"all": results, "core": core}, f, ensure_ascii=False, indent=2)

    print("\n=== 核心票清单（按涨幅降序，前 40） ===")
    for r in sorted(core.values(), key=lambda x: -x["gain_pct"])[:40]:
        print(f"{r['code']} {r['name']:8s} {r['start_date']}={r['start_price']:.2f} -> "
              f"{r['end_date']}={r['end_price']:.2f}  +{r['gain_pct']}%")


if __name__ == "__main__":
    main()
