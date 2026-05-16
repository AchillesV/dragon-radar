import os
import redis.asyncio as aioredis
try:
    import asyncpg
    _has_asyncpg = True
except ImportError:
    asyncpg = None  # type: ignore
    _has_asyncpg = False
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import analysis as analysis_router

load_dotenv()

app = FastAPI(
    title="Dragon Radar AI Analysis Service",
    description="AI 智能分析服务",
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dragonradar:dragonradar@localhost:5432/dragonradar")

_redis_client = None
_db_pool = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


async def get_db():
    global _db_pool
    if not _has_asyncpg:
        return None
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        except Exception:
            _db_pool = None
    return _db_pool


@app.on_event("startup")
async def startup_event():
    await get_redis()
    await get_db()


@app.on_event("shutdown")
async def shutdown_event():
    global _redis_client, _db_pool
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    if _db_pool:
        await _db_pool.close()
        _db_pool = None


app.state.get_redis = get_redis
app.state.get_db = get_db

app.include_router(analysis_router.router, prefix="/analysis", tags=["analysis"])


@app.get("/health")
async def health():
    redis_ok = False
    db_ok = False
    try:
        r = await get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass
    try:
        pool = await get_db()
        if pool:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
    except Exception:
        pass
    return {"status": "ok", "redis": redis_ok, "db": db_ok}
