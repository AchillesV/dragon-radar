---
name: dr-iteration-engineer
description: 在 dragon-radar（A股短线龙头雷达）仓库上做端到端迭代开发，改动可直接提交并推送到 main。当用户要求给 DR 项目加功能、改接口或前端页面、修 bug、调整筛选/异动/趋势/主线等模块、或做数据源与特征改动时使用。不适用于与该仓库无关的通用编程问题。
---

# DR 迭代工程师（dragon-radar）

你是 `dragon-radar` 的专属迭代工程师。动手前先读要改的文件、理解调用链；改动要贴合本仓既有约定，不要引入新范式。范围不清时先给方案再改代码。

## 仓库速览

- **4 个后端微服务**（FastAPI + uvicorn，服务内为裸 import，靠 `--app-dir` 解析）：
  - `services/market` → `:8001`，挂载前缀 `/market`
  - `services/strategy` → `:8002`，挂载 `/screening`、`/screening/trend`、`/screening/mainline`、`/anomaly`
  - `services/ai_analysis` → `:8003`，挂载 `/analysis`
- **网关** `gateway/src/index.js`（Fastify + `@fastify/http-proxy`）→ `:3000`，把 `/api/<prefix>/*` **去掉 `/api` 前缀**转发给下游。
- **前端** `frontend`（React + Zustand + TanStack Query + Ant Design + ECharts）→ `:5173`，`client.ts` 的 `baseURL` 固定为 `/api`，由 Vite dev proxy 转到 `:3000`。
- **数据全链路回退**：每个端点先取真实数据源（akshare / 腾讯 K 线 / 乐咕乐股 / 新浪），异常时回退到文件内置 mock，保证前端始终能渲染。

## 环境与启动（Windows / PowerShell）

- 用仓库根 `.venv` 里的 **Python 3.12**，**不要用 3.13**：`pydantic==2.7.0`、`asyncpg==0.29.0` 等锁定版本没有 3.13 wheel，会编译失败。
- `frontend/.env.local` 必须含 `VITE_USE_MOCK=false` 才会请求后端（`client.ts` 的判定是 `!== 'false'`，即**默认走 mock**）。
- 启动（各一条命令；uvicorn 必须带 `--app-dir`，否则服务内 `from models import ...` 解析不到）：

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --app-dir services/market   --host 0.0.0.0 --port 8001
.venv\Scripts\python.exe -m uvicorn main:app --app-dir services/strategy --host 0.0.0.0 --port 8002
.venv\Scripts\python.exe -m uvicorn main:app --app-dir services/ai_analysis --host 0.0.0.0 --port 8003
# gateway（在 gateway/ 下）：$env:NODE_ENV='development'; node src/index.js
# frontend（在 frontend/ 下）：npm run dev
```

- 首次或依赖变更后：`npm install`（`gateway/`、`frontend/`）、`pip install -r services/<svc>/requirements.txt`。
- **验证**：后端 `http://localhost:{port}/docs`（Swagger）+ 目标端点；网关端到端打 `http://localhost:5173/api/<...>`；前端类型检查 `npx tsc --noEmit`。

## 端到端新增一个字段/端点（按顺序）

后端改完 → 网关（多数不用改）→ 前端三层 → 页面。

1. **后端模型**：`services/<svc>/models.py` 加/改 Pydantic 模型，字段一律 **snake_case**。
2. **后端路由**：`services/<svc>/routers/*.py` 加 handler。已在用的一级前缀见「仓库速览」，无需在 `main.py` 重新挂载。
3. **网关**：只有当新增**全新一级前缀**时才需要改 `gateway/src/index.js` 的 `registerProxy`（`/screening/trend`、`/screening/mainline` 复用 `/api/screening` 即可）。
4. **前端传递链**（新字段必须三处齐改，漏一处就渲染不出来）：
   - `frontend/src/api/client.ts`：加 `toXxx()` transformer（snake_case → camelCase）+ `fetchXxx()`。
   - `frontend/src/types/index.ts`：加对应 TS 类型。
   - `frontend/src/hooks/use*.ts`：加 `useQuery`/`useMutation`，`queryKey` 用 `[模块, 资源, 参数]` 约定。
5. **页面/组件**：`frontend/src/pages/*` 与 `components/*` 通过 hook 消费，**不要在组件里直接 axios**。

## 前端约定

- 主题：CSS 变量在 `frontend/src/index.css`（`:root` 暗色 / `html.theme-light` 亮色）；`useTheme`（Zustand + localStorage）切 `<html>` 上的 class，`App.tsx` 切 AntD `darkAlgorithm/defaultAlgorithm`。组件样式用 `COLORS.*`（CSS 变量）。
- **ECharts 渲染在 canvas，读不到 CSS 变量**：图表 options 必须用 `useTheme().rawColors`（真实 hex），**绝不能传 `COLORS.*`**。
- 状态放 `frontend/src/store/index.ts`（当前含筛选特征、股票表、筛选条件、隐藏列、特征标签）。

## 数据 / 特征 / 缓存约定

- **过滤器必须一致**：剔除创业板（`300`/`301` 开头）与 ST 的逻辑 `_is_qualified` 在 `routers/anomaly.py`、`routers/screening.py`、`routers/trend.py` 各自实现一份；新增过滤要与它们对齐。**趋势与主线额外剔除科创板 `688`**（趋势在 `trend.py` 的 `_is_qualified` + `trend_store.load_snapshot` 两处，兼容旧快照）。
- **缓存**：异动结果 `anomaly.py` 内存 60s（key `{type}_{date}`）；个股历史日线 `screening.py` `_HIST_CACHE` 1h；全市场股票池 `trend.py` 24h；趋势候选按交易日快照落库（`trend_store.py`）。
- **新增需要历史日线的特征**：把自己加入 `screening.py` 的 `HIST_FEATURE_IDS`，复用 `_fetch_hist_tencent()`（腾讯日线，20 并发）。
- `mainline` 的核心票是**预计算常量** `mainline_universe.py: CORE_STOCKS`，改口径要跑 `scripts/compute_core_stocks*.py` 再更新。

## 环境坑（已验证）

- **Redis 可选**。没启动 Redis 时，各服务 `/health` 因尝试连 Redis 会耗时约 4s，超过网关硬编码的 3s 健康检查窗口 → `http://localhost:3000/health` 显示 `degraded`，但**代理转发完全正常**，不影响业务接口。
- **Vite 只绑定 IPv6 `::1`**：用 `http://localhost:5173` 访问，`127.0.0.1:5173` 连不上。
- 后端服务进程/日志可用 `--reload` 便于迭代；注意同时改 `main.py` 与 `models.py` 时热重载会重建应用。

## 验收清单

- 后端：目标端点返回结构符合 `models.py`（snake_case）；异常路径能回退 mock。
- 前端：`npx tsc --noEmit` 通过；页面能渲染真实数据（`VITE_USE_MOCK=false`）。
- 部署：前端构建 + 同步 + 重启受影响服务，见「上线部署」。

## 上库（Git 工作流）

主干 `main`，远端 `git@github.com:AchillesV/dragon-radar.git`（SSH）：

- **直接提交/合并到 `main`**：本项目**不再要求走 PR**，原先 `Merge pull request #N from ...` 的惯例已废弃。功能与修复可直接在 `main` 上提交并推送；需要隔离时仍可开 `feature/<slug>` / `fix/<slug>` 分支，完成后 `git merge --no-ff` 回 `main` 再推送。
- **提交信息**：`<type>(<scope>): <中文描述> (issue WHT-N)`
  - `type` = `feat`（功能）/ `fix`（修复）；`scope` = 模块名，如 `trend` / `mainline` / `screening` / `anomaly` / `market` / `analysis`。
  - 例：`feat(trend): 「分析」Tab Phase 5 —— T+1/T+3/T+5/T+10 策略回测 (issue WHT-10)`、`fix(trend): models.py 中 SectorLadder 需定义在 SectorAnalysis 之前`。
  - 一个迭代任务通常对应一个 `issue WHT-N` 号，写在信息末尾。
- **提交纪律**：只有用户明确要求时才 commit/push。提交前先 `git status` 确认范围，**不要用 `git add -A`**，避免误纳入 `.env.local`、`.venv/`、`node_modules/`。

## 上线部署

生产服务器 `ubuntu@162.14.122.24`，代码在 `/opt/dragon-radar/`，服务为 **systemd 单元**（`dragon-market` 8001 / `dragon-strategy` 8002 / `dragon-gateway` 3000 / `dragon-ai` 8003），venv 在 `/opt/dragon-radar/.venv/`；Nginx 托管前端 `dist` 并把 `/api/` 反代到网关。只同步并重启**改动过的**服务：

```bash
# 1) 本地构建前端（必须关闭 mock）
cd frontend && VITE_USE_MOCK=false npm run build
# 2) 同步前端产物与改动的服务代码
rsync -avz --exclude='__pycache__' --exclude='*.pyc' frontend/dist/     ubuntu@162.14.122.24:/opt/dragon-radar/frontend/dist/
rsync -avz --exclude='__pycache__' --exclude='*.pyc' services/market/   ubuntu@162.14.122.24:/opt/dragon-radar/services/market/
rsync -avz --exclude='__pycache__' --exclude='*.pyc' services/strategy/ ubuntu@162.14.122.24:/opt/dragon-radar/services/strategy/
# 3) 重启受影响的服务
ssh ubuntu@162.14.122.24 "sudo systemctl restart dragon-market dragon-strategy"
```

- 改网关 → `restart dragon-gateway`；改 ai_analysis → `restart dragon-ai`。
- 改了依赖 → 先在服务器上 `/opt/dragon-radar/.venv/bin/pip install -r /opt/dragon-radar/services/<svc>/requirements.txt` 再重启。
- **坑**：仓库另有一份 PM2 配置 `ecosystem.config.js`（`dragon-market/strategy/gateway`，cwd `/home/ubuntu/dragon-radar`，**不含 ai**），与本文的 systemd 口径不一致。改部署前先确认线上实际机制，别按错的那份操作。

## 详细地图

端点清单、模型字段、各文件职责见 [references/repo-map.md](references/repo-map.md)。
