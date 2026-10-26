# dragon-radar 仓库地图（详细参考）

供「DR 迭代工程师」按需加载。字段一律后端 snake_case，前端 camelCase，转换点在 `frontend/src/api/client.ts`。

## 网关路由（`gateway/src/index.js`）

`registerProxy(prefix, upstream, rewritePrefix)` 去掉 `/api` 前缀转发：

| 外部路径 | 下游 |
|---|---|
| `/api/market/*` | market:8001 → `/market` |
| `/api/anomaly/*` | strategy:8002 → `/anomaly` |
| `/api/screening/*` | strategy:8002 → `/screening`（含 `/trend`、`/mainline` 子路径） |
| `/api/analysis/*` | ai:8003 → `/analysis` |
| `/api/stock/*` | market:8001 → `/stock`（预留，未实现） |

`GET /health`：探测三个上游 + Redis；下游地址由 `MARKET_SERVICE_URL` / `STRATEGY_SERVICE_URL` / `AI_SERVICE_URL` 覆盖（dev 默认 `localhost:800x`）。

## market 服务（:8001，`services/market`）

- `main.py`：挂载 `market.router` 到 `/market`，`/health`。
- `routers/market.py` 端点：
  - `GET /market/overview` → `MarketOverview`。数据：乐咕乐股 `market-activity`（涨跌/涨跌停家数）+ 新浪指数成交额；Redis 缓存 60s（key `market:overview:{date}`）。
  - `GET /market/sectors?type=industry|concept&top_n=1..50` → `List[SectorRank]`。基于 `ak.stock_zt_pool_em` 按行业聚合。
  - `GET /market/fund_flow?top_n=1..50` → `List[FundFlowItem]`。`ak.stock_sector_fund_flow_rank`。
  - `GET /market/amount_history` → `List[DailyAmount]`。`ak.stock_market_activity_legu`（近 20 日）。
  - `GET /market/lianban` → `List[LianbanTier]`。`ak.stock_zt_pool_em` 按「连板数」分层。
- `models.py`：`MarketOverview(date, rise_count, fall_count, flat_count, limit_up_count, limit_down_count, total_amount, average_turnover, sentiment_index, market_status)`、`SectorRank(name, change_pct, leading_stock, leading_change, total_amount, rise_count, fall_count)`、`FundFlowItem(name, net_inflow, main_inflow, retail_inflow, leading_stock)`、`DailyAmount(date, amount, change_pct)`、`LianbanTier(count, stocks)`、`LianbanStock(code, name, count, reason, first_limit_time, amount)`。

## strategy 服务（:8002，`services/strategy`）

- `main.py`：`/screening`、`/screening/trend`、`/screening/mainline`、`/anomaly`，`/health`。
- `routers/anomaly.py`（11 种异动，`CARD_META` 为准）：
  - `GET /anomaly/cards` → 卡片摘要（含实时数量、`dataSource: 实时|演示`）。
  - `GET /anomaly/{anomaly_type}` → `List[AnomalyStock]`。
  - 类型：`volume_surge, high_turnover, weak_to_strong, reverse_limit, rebound_limit, eod_rush, gap_down_fade, quiet_limit, lianban_upgrade, dragon_separate, sector_resonance`。
  - 数据源：`ak.stock_zt_pool_em`（涨停池）、`stock_zt_pool_strong_em`（强势池）、`stock_zt_pool_previous_em`（昨涨停池）；内存缓存 60s；`_MOCK_FALLBACK` 兜底。
- `routers/screening.py`：
  - `GET /screening/candidates?feature_ids=a,b` → `List[CandidateStock]`（按特征并集，评分 `score`）。
  - `POST /screening/filter`（`FilterRequest{codes, filters}`）→ `List[CandidateStock]`。
  - `GET /screening/features` → `List[FeatureInfo]`（`ALL_FEATURES`，共 17 个）。
  - 历史特征走腾讯日线 `_fetch_hist_tencent`（`HIST_FEATURE_IDS = {multi_limit_15d, vol_surge_3d, five_day_rally}`，`_HIST_CACHE` 1h，20 并发）。
- `routers/trend.py`（趋势信号，规则 v0.4）：
  - `GET /screening/trend/candidates?date=` → `List[TrendStock]`（不传 date 走最新交易日懒加载 + 落库）。
  - `POST /screening/trend/sync` → 强制重扫并覆盖当天快照。
  - `GET /screening/trend/dates` → 有快照的交易日列表。
  - `GET /screening/trend/backtest?sessions=` → `TrendBacktest`（只读快照 + 腾讯日线）。
  - `GET /screening/trend/analysis?date=` → `TrendAnalysis`（`sector_analysis.build_analysis`）。
  - 规则参数：`BREAKOUT_BASELINE_DAYS=5 / BREAKOUT_MULTIPLIER=2.5 / SUSTAIN_MULTIPLIER=1.5 / LOOKBACK_TRADING_DAYS=10 / RANGE_WINDOWS=(3,5,10) / CHANGE_PCT_MIN,MAX=±10`。
- `routers/mainline.py`：
  - `GET /screening/mainline/stocks` → `List[MainlineStock]`（预计算核心票 + 腾讯批量实时行情，30s 缓存）。
- 支撑模块：`trend_store.py`（快照 `load_snapshot/save_snapshot/list_dates/compute_hit_counts`）、`sector_analysis.py`（`build_analysis`, `_MOCK_ANALYSIS`）、`backtest.py`（`run_backtest`, `_MOCK_BACKTEST`）、`features/base.py`、`features/calculator.py`、`stock_scores.py`、`mainline_universe.py`（`CORE_STOCKS`）。
- `models.py`：`AnomalyStock, CandidateStock, FeatureInfo, FilterRequest, TrendStock, TrendAnalysis, TrendBacktest, MainlineStock`（新增字段在此扩展）。

## ai_analysis 服务（:8003，`services/ai_analysis`）

- `routers/analysis.py`：
  - `POST /analysis/stock/{code}`（body `StockData`）→ `StockReport`。先查 PG 当日缓存表 `analysis_reports`；有 `ANTHROPIC_API_KEY` 调 Claude（`claude-opus-4-5`），否则/失败返回 mock 报告（`model: mock|mock-fallback`）。
  - `POST /analysis/bulk`（`BulkAnalysisRequest`）→ `BulkAnalysisResult`（整体市场复盘）。
- `prompts.py`：系统提示词与报告模板（含 mock 模板）。
- `main.py`：Redis + asyncpg(PG) 均**可选**（连不上不影响启动）；`/health` 返回 `redis/db` 状态。

## frontend（`frontend/src`）

- 路由（`App.tsx`）：`/` Dashboard、`/anomaly` AnomalyMonitor、`/anomaly/:type` AnomalyDetail、`/screening` Screening、`/trend` Trend、`/mainline` Mainline；移动端底部 `BottomTabBar`。
- `api/client.ts`：
  - `USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'`（默认 mock）。
  - transformers：`toMarketOverview, toSectorRank, toFundFlowItem, toLianbanTier, toStockRow, toAnomalyCard, toTrendStock, toTrendAnalysis, toBacktestStats, toBacktestGroup, toTrendBacktest, toMainlineStock`。
  - fetch：`fetchMarketOverview, fetchAmountHistory, fetchIndustrySectors, fetchConceptSectors, fetchFundFlow, fetchLianbanTiers, fetchAnomalyCards, fetchAnomalyStocks, fetchScreeningStocks, filterScreeningStocks, generateStockReport, fetchBulkAnalysis, fetchTrendStocks, syncTrendStocks, fetchTrendDates, fetchTrendAnalysis, fetchTrendBacktest, fetchMainlineStocks`。
- `hooks/`：`useMarketData, useAnomalyData, useScreeningData, useTrendData, useMainlineData, useTheme, useIsMobile`。
- `store/index.ts`：`selectedFeatures / stocks / filters / hiddenColumns / featureTags`。
- `types/index.ts`：前端类型总汇（与 transformer 输出对应）。
- `mock/data.ts`：mock 数据源。
- `components/`：`dashboard/、anomaly/、screening/、trend/、mainline/、common/、layout/`。

## 部署与运维

- `Dockerfile`：各服务 + `frontend/` + `gateway/`；`docker-compose.yml`（dev）、`docker-compose.prod.yml`。
- `ecosystem.config.js`：PM2 定义 `dragon-market / dragon-strategy / dragon-gateway`（cwd `/home/ubuntu/dragon-radar`，`REDIS_URL` 等环境变量；**注意未含 dragon-ai**）。
- `frontend/nginx.prod.conf`：静态 `dist` + `location /api/ → gateway:3000` + SPA `try_files → index.html`。
- `init-db/`：`postgres-init.sql`、`clickhouse-init.sql`。
- `scripts/`：`compute_core_stocks.py`、`compute_core_stocks_fullmarket.py`、`mainline_universe_candidates.py`、`verify_trend_analysis.py`（生成/校验主线核心票与趋势分析）。
- `CLAUDE.md` 描述生产为 systemd 单元 `dragon-market/strategy/gateway/ai`（8001/8002/3000/8003），venv 在 `/opt/dragon-radar/.venv/`，nginx 托管 dist 并反代 `/api/` → gateway。
  - **不一致点**：PM2 配置无 ai 服务、路径为 `/home/ubuntu/dragon-radar`，而 CLAUDE.md 写 systemd + `/opt/dragon-radar`。改部署前先确认线上实际使用的机制。
