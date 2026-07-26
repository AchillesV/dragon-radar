# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Dragon Radar — A-stock short-line leader detection system. Real-time monitoring of limit-up pools, anomaly stocks, and sector heat. 4 microservices + Fastify gateway + React frontend.

## Commands

### Frontend (`frontend/`)

```bash
npm run dev        # Vite dev server on :5173
npm run build      # tsc + vite build → dist/
npx tsc --noEmit   # type-check only
```

### Backend services (each in `services/{market,strategy,ai_analysis}/`)

```bash
# from repo root, with venv active
uvicorn main:app --host 0.0.0.0 --port 8001 --reload --app-dir services/market
uvicorn main:app --host 0.0.0.0 --port 8002 --reload --app-dir services/strategy
uvicorn main:app --host 0.0.0.0 --port 8003 --reload --app-dir services/ai_analysis
# Swagger UI auto-available at http://localhost:{port}/docs
```

### Gateway (`gateway/`)

```bash
NODE_ENV=development node src/index.js   # port 3000
```

### Full stack locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r services/market/requirements.txt -r services/strategy/requirements.txt
cd gateway && npm install
cd frontend && npm install
# Then start each service in a separate terminal as above
```

### Production (server at 162.14.122.24)

Services run as systemd units from `/opt/dragon-radar/`. Sync + restart:

```bash
# Build frontend locally, rsync dist + changed service code, restart affected services
VITE_USE_MOCK=false npm run build          # in frontend/
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
  frontend/dist/ ubuntu@162.14.122.24:/opt/dragon-radar/frontend/dist/
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
  services/market/ ubuntu@162.14.122.24:/opt/dragon-radar/services/market/
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
  services/strategy/ ubuntu@162.14.122.24:/opt/dragon-radar/services/strategy/
ssh ubuntu@162.14.122.24 "sudo systemctl restart dragon-market dragon-strategy"
```

Systemd units: `dragon-market` (8001), `dragon-strategy` (8002), `dragon-gateway` (3000), `dragon-ai` (8003). Venv at `/opt/dragon-radar/.venv/`. Nginx serves frontend dist and proxies `/api/` → gateway.

## Architecture

```
Browser :5173 (dev) / :80 (prod)
  └── React + Zustand + TanStack Query + Ant Design + ECharts
        │ /api/*
  Gateway :3000  (Fastify + @fastify/http-proxy)
    ├── /api/market/*     → Market Service  :8001  (akshare data)
    ├── /api/anomaly/*    → Strategy Service :8002  (akshare + detection logic)
    ├── /api/screening/*  → Strategy Service :8002  (feature filters)
    └── /api/analysis/*   → AI Service       :8003  (Anthropic Claude)
```

Gateway strips `/api` prefix before forwarding. All services share an optional Redis (:6379) for caching; they start fine without it.

## Key Patterns

**snake_case ↔ camelCase**: All backends return snake_case. `frontend/src/api/client.ts` has transformer functions (e.g. `toMarketOverview`, `toStockRow`) that convert to camelCase before React state. When adding new fields: add to the Pydantic model → update the transformer in `client.ts` → update the TypeScript type in `src/types/index.ts`.

**Mock fallback (frontend)**: `VITE_USE_MOCK=false` in `frontend/.env.local`. When `true`, `client.ts` skips all HTTP calls and returns data from `src/mock/data.ts`. Useful for UI-only work with no backend running.

**Mock fallback (backend)**: Every endpoint tries the real akshare/external source first, falls back to in-file mock data on any exception. Market overview, lianban, anomaly detection all have this pattern.

**ECharts theming**: ECharts renders on canvas and cannot read CSS variables. Components like `AmountChart`, `SectorRankChart`, `FundFlowChart` use `const { rawColors } = useTheme()` (from `src/hooks/useTheme.ts`) to get actual hex values. Never pass `COLORS.*` (CSS var references) to ECharts options.

**Light/dark theme**: CSS variables defined in `src/index.css` (`:root` = dark, `html.theme-light` = light). `useTheme` (Zustand, localStorage-persisted) toggles the class on `<html>`. Ant Design algorithm switches between `theme.darkAlgorithm` / `theme.defaultAlgorithm` in `App.tsx`.

**Filtering**: Both anomaly and screening results filter out 创业板 (codes starting `300`/`301`) and ST stocks (name contains `ST`). This happens server-side via `_is_qualified(code, name)` in `anomaly.py` and inside `register()` in `screening.py`.

**60-second cache**: `anomaly.py` uses an in-memory `_CACHE` dict to avoid hammering akshare on each card-refresh. Cache key is `{type}_{date}`.

## Environment Variables

| Variable | Where | Purpose |
|---|---|---|
| `VITE_USE_MOCK` | frontend `.env.local` | `false` = real API, `true` = mock data only |
| `REDIS_URL` | all services + gateway | defaults to `redis://localhost:6379`; optional |
| `DATABASE_URL` | market, strategy, ai | PostgreSQL; optional for core features |
| `ANTHROPIC_API_KEY` | ai_analysis service | if unset, returns mock AI reports (no error) |
