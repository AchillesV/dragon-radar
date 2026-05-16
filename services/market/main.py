import os
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import market as market_router

load_dotenv()

app = FastAPI(
    title="Dragon Radar Market Service",
    description="行情数据服务",
    version="1.0.0",
)

# CORS 配置（开发用，允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis 连接池
_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


@app.on_event("startup")
async def startup_event():
    # 预先尝试连接 Redis（失败则忽略，服务依然启动）
    await get_redis()


@app.on_event("shutdown")
async def shutdown_event():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


# 将 redis getter 挂到 app.state，方便路由访问
app.state.get_redis = get_redis

# 挂载路由
app.include_router(market_router.router, prefix="/market", tags=["market"])


@app.get("/health")
async def health():
    redis_ok = False
    try:
        r = await get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass
    return {"status": "ok", "redis": redis_ok}
