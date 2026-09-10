"""
「趋势 → 分析」板块聚合结果的验证脚本（issue WHT-10 / V2 Phase 1）

用途：在真实数据上跑一遍「趋势候选池 → 板块聚合 → 热度/扩散度」，人工检查排序是否
合理、有无明显误判（NaN、扩散度分母异常、板块与候选股对不上等）。

依赖：akshare（全市场股票池）、pandas、requests（已在 requirements 中）。

用法（在仓库根目录，激活 venv 后）：
    python scripts/verify_trend_analysis.py            # 真实候选池（会做一次全市场扫描，约 1~2 分钟）
    python scripts/verify_trend_analysis.py --sample 8 # 只用手工样例候选股，快速冒烟
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_DIR = os.path.join(ROOT, "services", "strategy")
sys.path.insert(0, STRATEGY_DIR)
os.chdir(STRATEGY_DIR)

import sector_analysis as sa  # noqa: E402


SAMPLE = [
    {"code": "002371", "name": "北方华创", "change_pct": 3.1},
    {"code": "600584", "name": "长电科技", "change_pct": 2.0},
    {"code": "600900", "name": "长江电力", "change_pct": 1.1},
    {"code": "603601", "name": "再升科技", "change_pct": 10.0},
    {"code": "000725", "name": "京东方Ａ", "change_pct": -0.5},
    {"code": "600460", "name": "士兰微", "change_pct": 4.2},
    {"code": "002472", "name": "双环传动", "change_pct": 5.6},
    {"code": "603667", "name": "五洲新春", "change_pct": 2.2},
]


def real_candidates():
    from routers import trend
    import trend_store

    date = trend._get_session_date()
    print(f"[verify] 最新交易日: {date}")
    t0 = time.time()
    stocks = trend._compute_trend_stocks()
    print(f"[verify] 全市场趋势扫描命中候选股 {len(stocks)} 只，用时 {time.time() - t0:.1f}s")
    if stocks:
        trend_store.save_snapshot(date, stocks)
    return date, [
        {"code": s.code, "name": s.name, "change_pct": s.change_pct} for s in stocks
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0,
                    help=">0 时只用手工样例候选股（快速冒烟），忽略真实全市场扫描")
    args = ap.parse_args()

    if args.sample:
        date = time.strftime("%Y-%m-%d")
        candidates = SAMPLE[:args.sample]
        print(f"[verify] 冒烟模式：{len(candidates)} 只样例候选股")
    else:
        date, candidates = real_candidates()

    t0 = time.time()
    res = sa.build_analysis(candidates, date)
    print(f"[verify] 板块聚合用时 {time.time() - t0:.1f}s，source={res['source']}，"
          f"板块数={len(res['sectors'])}")

    # ---- 断言：结构完整、无 NaN ----
    problems = []
    for s in res["sectors"]:
        if s["total_count"] <= 0:
            problems.append(f"{s['name']}: 扩散度分母为 0")
        for k in ("score", "breadth_score", "up_ratio"):
            v = s.get(k)
            if v is None or v != v:  # NaN 检查
                problems.append(f"{s['name']}: {k} 异常 {v}")

    with_cand = sum(1 for s in res["sectors"] if s["candidate_count"] > 0)
    print(f"\n[verify] {len(res['sectors'])} 个重点板块中，{with_cand} 个含趋势候选股")

    print("\n[verify] 板块热度 TOP：")
    print(f"  {'分数':>6} {'类型':<6} {'板块':<12} {'候选':>4} {'今日%':>7} "
          f"{'5日%':>7} {'20日%':>7} {'量比':>5} {'资金%':>6} {'扩散':>5} {'上涨%':>6} {'并集数':>6}")
    for s in res["sectors"]:
        print(f"  {s['score']:>6.1f} {s['type']:<6} {s['name']:<12} {s['candidate_count']:>4} "
              f"{s['change_pct']:>7.2f} {str(s['change5_pct']):>7} {str(s['change20_pct']):>7} "
              f"{str(s['lb']):>5} {str(s['net_inflow_pct']):>6} "
              f"{str(s['breadth_score']):>5} {str(s['up_ratio']):>6} {s['total_count']:>6}")

    print("\n[verify] 抽样明细（第 1 个板块）：")
    if res["sectors"]:
        print(json.dumps(res["sectors"][0], ensure_ascii=False, indent=2))

    if problems:
        print("\n[verify] 发现问题：")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\n[verify] 通过：结构完整、无 NaN、扩散度分母正常。")


if __name__ == "__main__":
    main()
