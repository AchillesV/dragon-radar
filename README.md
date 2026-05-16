# Dragon Radar — A股雷达系统

Dragon Radar 是一套面向 A 股短线交易的智能监控与分析平台，由 React 前端 + 微服务后端构成。

## 架构总览

```
前端 (React/Vite:5173)
       │
       ▼
  API 网关 (Fastify:3000)
  ├── /api/market/*     → market-service:8001   行情服务 (FastAPI + akshare)
  ├── /api/anomaly/*    → strategy-service:8002  异动筛选 (FastAPI)
  ├── /api/screening/*  → strategy-service:8002  特征筛选 (FastAPI)
  └── /api/analysis/*   → ai-analysis-service:8003  AI分析 (FastAPI + Claude)
         │                       │
         ▼                       ▼
      Redis:6379          PostgreSQL:5432
                          ClickHouse:8123
```

## 快速启动（Docker Compose）

```bash
# 克隆项目
git clone <repo-url>
cd dragon-radar

# （可选）配置 Anthropic API Key
export ANTHROPIC_API_KEY=sk-ant-xxxx

# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止所有服务
docker-compose down
```

服务启动后访问：
- 前端：http://localhost:5173（需单独启动，见下方）
- API 网关：http://localhost:3000
- 行情服务 API 文档：http://localhost:8001/docs
- 策略服务 API 文档：http://localhost:8002/docs
- AI 分析服务 API 文档：http://localhost:8003/docs

## 本地开发启动

### 1. 启动基础设施（数据库+缓存）

```bash
docker-compose up -d postgres redis clickhouse
```

### 2. 启动行情服务

```bash
cd services/market
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 3. 启动策略服务

```bash
cd services/strategy
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

### 4. 启动 AI 分析服务

```bash
cd services/ai_analysis
pip install -r requirements.txt
uvicorn main:app --reload --port 8003
```

### 5. 启动 API 网关（开发模式）

```bash
cd gateway
npm install
NODE_ENV=development node src/index.js
# 或使用 watch 模式
NODE_ENV=development node --watch src/index.js
```

### 6. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | `""` | Claude API 密钥；留空则使用 mock 数据 |
| `REDIS_URL` | `redis://redis:6379` | Redis 连接地址 |
| `DATABASE_URL` | `postgresql://dragonradar:dragonradar@postgres:5432/dragonradar` | PostgreSQL 连接串 |
| `CLICKHOUSE_URL` | `http://clickhouse:8123` | ClickHouse HTTP 接口地址 |
| `MARKET_SERVICE_URL` | `http://market-service:8001` | 网关→行情服务地址 |
| `STRATEGY_SERVICE_URL` | `http://strategy-service:8002` | 网关→策略服务地址 |
| `AI_SERVICE_URL` | `http://ai-analysis-service:8003` | 网关→AI分析服务地址 |
| `PORT` | `3000` | 网关监听端口 |
| `NODE_ENV` | `production` | 运行模式；`development` 时服务地址默认为 localhost |

## 数据源配置说明

### akshare（行情数据）
行情服务使用 [akshare](https://akshare.akfamily.xyz/) 获取 A 股实时和历史数据。
- 无需 API Key，直接从公开接口获取
- 若网络不可达，所有接口自动 fallback 到 mock 数据
- 数据更新频率受交易所限制，非交易时间部分接口返回上一交易日数据

### mootdx（Level2 数据）
策略服务引入 mootdx 获取分时/成交明细数据，用于：
- 尾盘冲量特征检测
- 炸板回封特征检测
- mootdx 需要通达信客户端或代理节点，未配置时自动 fallback

### Claude API（AI 分析）
AI 分析服务使用 [Anthropic Claude](https://anthropic.com) 生成报告。
- 配置 `ANTHROPIC_API_KEY` 环境变量后启用真实 AI 分析
- 未配置时返回预设的详细 mock 报告（内容真实、格式完整）
- 推荐使用 `claude-opus-4-5` 模型，支持中文专业金融分析

## Mock 数据说明

系统在以下情况自动使用 mock 数据：
1. 外部数据源（akshare/mootdx）不可访问
2. `ANTHROPIC_API_KEY` 未配置
3. Redis/PostgreSQL 连接失败

所有 mock 数据贴近真实市场情况，可在无任何外部依赖的情况下完整演示系统功能。

## API 接口一览

### 行情服务（:8001）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/market/overview` | 市场概览（上涨/下跌/涨停家数等） |
| GET | `/market/sectors` | 板块涨跌排名 |
| GET | `/market/fund_flow` | 板块资金流向 |
| GET | `/market/amount_history` | 近20日成交额历史 |
| GET | `/market/lianban` | 连板梯队 |

### 策略服务（:8002）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/anomaly/{type}` | 指定类型的异动股 |
| GET | `/screening/candidates` | 候选股筛选 |
| POST | `/screening/filter` | 条件过滤 |
| GET | `/screening/features` | 特征列表 |

### AI 分析服务（:8003）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/analysis/stock/{code}` | 单股 AI 分析 |
| POST | `/analysis/bulk` | 市场整体分析（复盘） |
