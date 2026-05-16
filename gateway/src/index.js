'use strict'

const Fastify = require('fastify')
const cors = require('@fastify/cors')
const httpProxy = require('@fastify/http-proxy')

// ---------------------------------------------------------------------------
// 服务地址配置（开发环境可通过环境变量覆盖）
// ---------------------------------------------------------------------------
const isDev = process.env.NODE_ENV === 'development'

const MARKET_SERVICE_URL = process.env.MARKET_SERVICE_URL ||
  (isDev ? 'http://localhost:8001' : 'http://market-service:8001')

const STRATEGY_SERVICE_URL = process.env.STRATEGY_SERVICE_URL ||
  (isDev ? 'http://localhost:8002' : 'http://strategy-service:8002')

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ||
  (isDev ? 'http://localhost:8003' : 'http://ai-analysis-service:8003')

const PORT = parseInt(process.env.PORT || '3000', 10)
const HOST = process.env.HOST || '0.0.0.0'

// ---------------------------------------------------------------------------
// Redis（可选，用于网关层缓存/限流等扩展）
// ---------------------------------------------------------------------------
let redis = null
const REDIS_URL = process.env.REDIS_URL || (isDev ? 'redis://localhost:6379' : 'redis://redis:6379')

async function initRedis () {
  try {
    const Redis = require('ioredis')
    redis = new Redis(REDIS_URL, { lazyConnect: true, connectTimeout: 3000 })
    await redis.connect()
    console.log('[gateway] Redis connected')
  } catch (err) {
    console.warn('[gateway] Redis unavailable, skipping:', err.message)
    redis = null
  }
}

// ---------------------------------------------------------------------------
// 创建 Fastify 实例
// ---------------------------------------------------------------------------
const app = Fastify({
  logger: {
    level: isDev ? 'info' : 'warn',
    transport: isDev ? { target: 'pino-pretty' } : undefined,
  },
})

// CORS
app.register(cors, {
  origin: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
})

// ---------------------------------------------------------------------------
// 代理路由注册
// ---------------------------------------------------------------------------

/**
 * 注册一个代理：将 /api/<prefix>/* 转发到 upstream/<prefix>/*
 * rewritePrefix 去掉 /api，保留后续路径原样传给下游服务
 */
function registerProxy (prefix, upstream, rewritePrefix) {
  app.register(httpProxy, {
    upstream,
    prefix,
    rewritePrefix: rewritePrefix || prefix.replace(/^\/api/, ''),
    http2: false,
  })
}

// /api/market/*  →  market-service/market/*
registerProxy('/api/market', MARKET_SERVICE_URL, '/market')

// /api/anomaly/* →  strategy-service/anomaly/*
registerProxy('/api/anomaly', STRATEGY_SERVICE_URL, '/anomaly')

// /api/screening/* → strategy-service/screening/*
registerProxy('/api/screening', STRATEGY_SERVICE_URL, '/screening')

// /api/analysis/* → ai-analysis-service/analysis/*
registerProxy('/api/analysis', AI_SERVICE_URL, '/analysis')

// /api/stock/*   →  market-service/stock/*（预留）
registerProxy('/api/stock', MARKET_SERVICE_URL, '/stock')

// ---------------------------------------------------------------------------
// 健康检查
// ---------------------------------------------------------------------------
app.get('/health', async (req, reply) => {
  const services = {
    market: false,
    strategy: false,
    ai_analysis: false,
    redis: redis !== null,
  }

  const checkService = async (url, key) => {
    try {
      const response = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) })
      services[key] = response.ok
    } catch {
      services[key] = false
    }
  }

  await Promise.allSettled([
    checkService(MARKET_SERVICE_URL, 'market'),
    checkService(STRATEGY_SERVICE_URL, 'strategy'),
    checkService(AI_SERVICE_URL, 'ai_analysis'),
  ])

  const allOk = Object.values(services).every(Boolean)
  reply.code(allOk ? 200 : 206).send({
    status: allOk ? 'ok' : 'degraded',
    services,
    upstreams: {
      market: MARKET_SERVICE_URL,
      strategy: STRATEGY_SERVICE_URL,
      ai: AI_SERVICE_URL,
    },
  })
})

// 根路径
app.get('/', async () => ({
  name: 'Dragon Radar API Gateway',
  version: '1.0.0',
  routes: [
    '/api/market/*  → market-service:8001',
    '/api/anomaly/* → strategy-service:8002',
    '/api/screening/* → strategy-service:8002',
    '/api/analysis/* → ai-analysis-service:8003',
    '/api/stock/*   → market-service:8001',
  ],
}))

// ---------------------------------------------------------------------------
// 启动
// ---------------------------------------------------------------------------
async function start () {
  await initRedis()

  try {
    await app.listen({ port: PORT, host: HOST })
    console.log(`[gateway] Listening on ${HOST}:${PORT}`)
    console.log(`[gateway] Market service:   ${MARKET_SERVICE_URL}`)
    console.log(`[gateway] Strategy service: ${STRATEGY_SERVICE_URL}`)
    console.log(`[gateway] AI service:       ${AI_SERVICE_URL}`)
  } catch (err) {
    app.log.error(err)
    process.exit(1)
  }
}

start()
