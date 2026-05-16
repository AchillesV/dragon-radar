import os
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import anomaly as anomaly_router
from routers import screening as screening_router

load_dotenv()

app = FastAPI(
    title="Dragon Radar Strategy Service",
    description="策略与特征筛选服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

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
    await get_redis()


@app.on_event("shutdown")
async def shutdown_event():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


app.state.get_redis = get_redis

app.include_router(anomaly_router.router, tags=["anomaly"])
app.include_router(screening_router.router, prefix="/screening", tags=["screening"])


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
