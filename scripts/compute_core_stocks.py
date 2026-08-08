"""
一次性数据验证脚本：对候选股票池逐只拉取腾讯 K 线真实历史行情，
计算 2026-04-01 ~ 2026-06-30 区间的累计涨跌幅，筛出翻倍（>=100%）的
「科技主线核心票」，并打印结果供人工核对后写入
services/strategy/mainline_universe.py 的 CORE_STOCKS。

跑一次即可，不是服务运行时代码。
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

sys.path.insert(0, "scripts")
from mainline_universe_candidates import CANDIDATES  # noqa: E402

START = "2026-04-01"
END = "2026-06-30"
FETCH_START = "2026-03-20"  # 留一点缓冲，确保能取到 4/1 前后最近交易日
FETCH_END = "2026-07-05"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_kline(code: str) -> pd.DataFrame | None:
    prefix = "sh" if code.startswith(("6", "9")) else ("bj" if code.startswith("8") else "sz")
    full = f"{prefix}{code}"
    url = (
        f"https://ifzq.gtimg.cn/appstock/app/kline/kline"
        f"?p=1&param={full},day,{FETCH_START},{FETCH_END},320&_var=m_{full}_day"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        rows = data["data"][full]["day"]
        # 复权/分红日腾讯会在行尾多塞一个 dict 字段，只取前 6 列
        rows = [r[:6] for r in rows]
        df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "vol"])
        for c in ["open", "close", "high", "low", "vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        print(f"  [FAIL] {code}: {e}")
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
    all_codes = {}
    for subsector, stocks in CANDIDATES.items():
        for code, name in stocks:
            all_codes.setdefault(code, name)

    print(f"候选股票总数（去重）: {len(all_codes)}")
    results = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(compute_gain, code, name): code for code, name in all_codes.items()}
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
            if done % 20 == 0:
                print(f"  progress {done}/{len(all_codes)}")

    core = {c: r for c, r in results.items() if r["gain_pct"] >= 100}
    print(f"\n成功获取行情: {len(results)}/{len(all_codes)}")
    print(f"翻倍核心票（4/1~6/30 累计涨幅 >= 100%）: {len(core)}")

    with open("scripts/core_stock_results.json", "w", encoding="utf-8") as f:
        json.dump({"all": results, "core": core}, f, ensure_ascii=False, indent=2)

    print("\n=== 核心票清单（按涨幅降序） ===")
    for r in sorted(core.values(), key=lambda x: -x["gain_pct"]):
        print(f"{r['code']} {r['name']:6s} {r['start_date']}={r['start_price']:.2f} -> "
              f"{r['end_date']}={r['end_price']:.2f}  +{r['gain_pct']}%")


if __name__ == "__main__":
    main()
