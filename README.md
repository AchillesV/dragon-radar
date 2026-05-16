# Dragon Radar — A股龙头雷达

A股短线龙头发现系统，实时监控涨停池、异动股与强势特征，辅助短线选股决策。

## 功能

- **市场概览**：涨跌家数、涨跌停、沪深成交额（接入乐咕乐股实时数据）
- **连板梯队**：当日涨停池按连板数分层，实时排列（akshare）
- **异动雷达**：11 种异动类型（放量、弱转强、炸板回封、缩量涨停等）
- **特征筛选**：14 种实时/历史特征组合筛选，含：
  - 15天内≥3次涨停板
  - 近3天3倍放量上涨
  - 5天连续上涨
- **AI 分析**：单股报告 + 整体市场复盘（接入 Claude API）

## 架构

```
浏览器 (5173)
    │
    ▼
API 网关 · Fastify (3000)
    ├── /api/market/*     →  行情服务  (8001)  FastAPI + akshare
    ├── /api/anomaly/*    →  策略服务  (8002)  FastAPI
    ├── /api/screening/*  →  策略服务  (8002)  FastAPI
    └── /api/analysis/*   →  AI服务   (8003)  FastAPI + Claude
                                   │
                               Redis (6379)
```

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.10 + |
| Node.js | 18 + |
| Redis | 6 + |

## 本地启动

### 1. 克隆项目

```bash
git clone git@github.com:AchillesV/dragon-radar.git
cd dragon-radar
```

### 2. 启动 Redis

```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt install redis-server
sudo systemctl start redis
```

### 3. 创建 Python 虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r services/market/requirements.txt
pip install -r services/strategy/requirements.txt
pip install -r services/ai_analysis/requirements.txt
```

### 4. 启动三个后端服务（各开一个终端）

```bash
# 终端 1 — 行情服务
PYTHONPATH=services/market .venv/bin/uvicorn main:app \
  --app-dir services/market --host 0.0.0.0 --port 8001

# 终端 2 — 策略服务
PYTHONPATH=services/strategy .venv/bin/uvicorn main:app \
  --app-dir services/strategy --host 0.0.0.0 --port 8002

# 终端 3 — AI 分析服务
ANTHROPIC_API_KEY=sk-ant-xxxx \
PYTHONPATH=services/ai_analysis .venv/bin/uvicorn main:app \
  --app-dir services/ai_analysis --host 0.0.0.0 --port 8003
```

> `ANTHROPIC_API_KEY` 不填时 AI 分析自动返回 mock 报告，其余功能不受影响。

### 5. 启动 API 网关

```bash
cd gateway
npm install
NODE_ENV=development node src/index.js
```

### 6. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 **http://localhost:5173**

---

## 数据说明

| 接口 | 数据源 | 备注 |
|------|--------|------|
| 市场概览（涨跌家数） | [乐咕乐股](https://legulegu.com/stockdata/market-activity) | 无需 Key |
| 沪深成交额 | 新浪指数接口 | 无需 Key |
| 涨停池 / 连板梯队 | akshare `stock_zt_pool_em` | 无需 Key |
| 历史日线（15天涨停/放量/连涨特征） | 腾讯 K 线接口 | 无需 Key，1小时缓存 |
| AI 分析报告 | Anthropic Claude API | 需配置 `ANTHROPIC_API_KEY` |

所有外部数据源不可达时自动 fallback 到内置 mock 数据，系统可在无网络的情况下完整演示。

## 前端环境变量

`frontend/.env.local`（首次运行需手动创建）：

```
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:3000
```

设为 `VITE_USE_MOCK=true` 则前端完全走本地 mock，无需启动任何后端。

## API 文档

服务启动后可直接访问 Swagger UI：

- 行情服务：http://localhost:8001/docs
- 策略服务：http://localhost:8002/docs
- AI 服务：http://localhost:8003/docs

## 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/market/overview` | 市场概览 |
| GET | `/api/market/lianban` | 连板梯队 |
| GET | `/api/market/sectors` | 板块热度 |
| GET | `/api/market/amount_history` | 近20日成交额 |
| GET | `/api/anomaly/cards` | 异动类型列表 |
| GET | `/api/anomaly/{type}` | 指定异动的股票列表 |
| GET | `/api/screening/candidates?feature_ids=multi_limit_15d,vol_surge_3d` | 特征筛选 |
| GET | `/api/screening/features` | 全部特征定义 |
| POST | `/api/analysis/stock/{code}` | 单股 AI 分析 |
| POST | `/api/analysis/bulk` | 整体市场分析 |
