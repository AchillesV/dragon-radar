"""
一次性数据验证脚本（issue WHT-9）：全市场（沪深主板/中小板，已剔除创业板 300/301、
科创板 688、ST）逐只拉取腾讯 K 线真实历史行情，计算 2026-04-01 ~ 2026-06-30 区间
累计涨跌幅，筛出 >=80% 的「主力核心票」候选，供人工核对后写入
services/strategy/mainline_universe.py 的 CORE_STOCKS。

候选股票池从沪深交易所官方列表现取（build_candidates），不依赖任何本地缓存文件，
跑一次即可复现完整流程；不是服务运行时代码。
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

import pandas as pd
import requests

START = "2026-04-01"
END = "2026-06-30"
FETCH_START = "2026-03-20"
FETCH_END = "2026-07-05"
GAIN_THRESHOLD = 80.0

HEADERS = {"User-Agent": "Mozilla/5.0"}
_NO_PROXY = {"http": None, "https": None}


def _is_st(name: str) -> bool:
    return "ST" in str(name).upper()


def build_candidates() -> dict[str, str]:
    """
    全市场候选股票池：沪市主板（600/601/603/605）+ 深市主板/中小板，
    剔除创业板（300/301）、科创板（688）、ST。与 anomaly.py 的
    `_is_qualified` 过滤口径一致（创业板+ST），额外剔除科创板（本次需求新增）。
    """
    sse_headers = {
        "Host": "query.sse.com.cn",
        "Referer": "https://www.sse.com.cn/assortment/stock/list/share/",
        "User-Agent": HEADERS["User-Agent"],
    }
    sse_params = {
        "STOCK_TYPE": "1", "REG_PROVINCE": "", "CSRC_CODE": "", "STOCK_CODE": "",
        "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L", "COMPANY_STATUS": "2,4,5,7,8",
        "type": "inParams", "isPagination": "true",
        "pageHelp.cacheSize": "1", "pageHelp.beginPage": "1", "pageHelp.pageSize": "10000",
        "pageHelp.pageNo": "1", "pageHelp.endPage": "1",
    }
    r = requests.get(
        "https://query.sse.com.cn/sseQuery/commonQuery.do",
        params=sse_params, headers=sse_headers, timeout=15, proxies=_NO_PROXY,
    )
    sse_rows = r.json()["pageHelp"]["data"]
    candidates = {row["A_STOCK_CODE"]: row["SEC_NAME_CN"] for row in sse_rows}

    r = requests.get(
        "https://www.szse.cn/api/report/ShowReport",
        params={"SHOWTYPE": "xlsx", "CATALOGID": "1110", "TABKEY": "tab1", "random": "0.1"},
        timeout=20, proxies=_NO_PROXY,
    )
    szse_df = pd.read_excel(BytesIO(r.content))
    szse_df["A股代码"] = szse_df["A股代码"].astype(str).str.split(".", expand=True).iloc[:, 0].str.zfill(6)
    for _, row in szse_df.iterrows():
        code = row["A股代码"]
        if not code or code.startswith(("300", "301")):
            continue
        candidates[code] = row["A股简称"]

    return {code: name for code, name in candidates.items() if not _is_st(name)}


def fetch_kline(code: str) -> pd.DataFrame | None:
    prefix = "sh" if code.startswith(("6", "9")) else ("bj" if code.startswith("8") else "sz")
    full = f"{prefix}{code}"
    url = (
        f"https://ifzq.gtimg.cn/appstock/app/kline/kline"
        f"?p=1&param={full},day,{FETCH_START},{FETCH_END},320&_var=m_{full}_day"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=6, proxies={"http": None, "https": None})
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        rows = data["data"][full]["day"]
        rows = [row[:6] for row in rows]
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
    all_codes = build_candidates()

    print(f"候选股票总数（已剔除创业板/科创板/ST）: {len(all_codes)}", flush=True)
    results = {}
    progress_f = open("scripts/core_stock_fullmarket_progress.jsonl", "w", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=30) as pool:
        futs = {pool.submit(compute_gain, code, name): code for code, name in all_codes.items()}
        done = 0
        for fut in as_completed(futs):
            code = futs[fut]
            done += 1
            try:
                r = fut.result()
                if r:
                    results[code] = r
                    progress_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    progress_f.flush()
            except Exception as e:
                print(f"  [ERR] {code}: {e}", flush=True)
            if done % 200 == 0:
                print(f"  progress {done}/{len(all_codes)}", flush=True)
    progress_f.close()

    core = {c: r for c, r in results.items() if r["gain_pct"] >= GAIN_THRESHOLD}
    print(f"\n成功获取行情: {len(results)}/{len(all_codes)}")
    print(f"核心票（4/1~6/30 累计涨幅 >= {GAIN_THRESHOLD}%）: {len(core)}")

    with open("scripts/core_stock_fullmarket_results.json", "w", encoding="utf-8") as f:
        json.dump({"all": results, "core": core}, f, ensure_ascii=False, indent=2)

    print("\n=== 核心票清单（按涨幅降序） ===")
    for r in sorted(core.values(), key=lambda x: -x["gain_pct"]):
        print(f"{r['code']} {r['name']:6s} {r['start_date']}={r['start_price']:.2f} -> "
              f"{r['end_date']}={r['end_price']:.2f}  +{r['gain_pct']}%")


if __name__ == "__main__":
    main()
