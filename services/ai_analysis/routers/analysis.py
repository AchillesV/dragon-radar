"""
AI 分析路由
"""
import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from models import StockData, StockReport, BulkAnalysisRequest, BulkAnalysisResult
from prompts import (
    STOCK_ANALYSIS_SYSTEM,
    STOCK_ANALYSIS_TEMPLATE,
    BULK_ANALYSIS_TEMPLATE,
    MOCK_STOCK_REPORT_TEMPLATE,
    MOCK_BULK_REPORT_TEMPLATE,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _build_mock_stock_report(stock: StockData) -> str:
    lianban_info_text = (
        f"目前已连续涨停{stock.lianban_count}板，" if stock.lianban_count and stock.lianban_count > 0
        else "非连板状态，"
    )
    change_abs = abs(stock.change_pct)
    strength = min(10, max(1, round(change_abs * 0.7 + (stock.lianban_count or 0) * 0.5 + stock.turnover * 0.1)))
    certainty = min(10, max(1, round(strength * 0.85)))
    risk = min(10, max(1, round(10 - strength * 0.6)))

    return MOCK_STOCK_REPORT_TEMPLATE.format(
        name=stock.name,
        code=stock.code,
        change_pct=stock.change_pct,
        amount=stock.amount,
        turnover=stock.turnover,
        lianban_info_text=lianban_info_text,
        strength=strength,
        certainty=certainty,
        risk=risk,
    ).strip()


def _build_mock_bulk_report(request: BulkAnalysisRequest) -> str:
    md = request.market_data
    date = md.date if md and md.date else _today_str()
    rise = md.rise_count if md else 2341
    fall = md.fall_count if md else 985
    limit_up = md.limit_up_count if md else 87
    amount = md.total_amount if md else 2.87
    max_lianban = md.max_lianban if md else 11
    max_stock = md.max_lianban_stock if md else "某科技"
    sectors = "、".join(md.sectors[:5]) if md and md.sectors else "人工智能、低空经济、量子通信"

    return MOCK_BULK_REPORT_TEMPLATE.format(
        date=date,
        rise=rise,
        fall=fall,
        limit_up=limit_up,
        amount=amount,
        max_lianban=max_lianban,
        max_stock=max_stock,
        sectors=sectors,
    ).strip()


@router.post("/stock/{code}", response_model=StockReport)
async def analyze_stock(code: str, stock: StockData, request: Request):
    """
    分析单只股票，生成 AI 分析报告。
    - 优先查询 PostgreSQL 当日缓存
    - 无缓存时调用 Claude API 生成（若 API Key 未配置则返回详细 mock 报告）
    """
    today = _today_str()

    # 查询 PostgreSQL 缓存
    try:
        pool = await request.app.state.get_db()
        if pool:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT content, model FROM analysis_reports "
                    "WHERE report_type='stock' AND target_id=$1 AND date=$2 "
                    "ORDER BY generated_at DESC LIMIT 1",
                    code, today,
                )
                if row:
                    return StockReport(
                        code=code,
                        name=stock.name,
                        date=today,
                        content=row["content"],
                        model=row["model"],
                        from_cache=True,
                    )
    except Exception as e:
        logger.warning(f"DB cache read error: {e}")

    # 生成报告内容
    content: str
    model_name: str

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            lianban_info = (
                f"已连续涨停{stock.lianban_count}板"
                if stock.lianban_count and stock.lianban_count > 0
                else "非连板"
            )
            sectors_str = "、".join(stock.sectors) if stock.sectors else "未知板块"
            prompt = STOCK_ANALYSIS_TEMPLATE.format(
                name=stock.name,
                code=code,
                change_pct=stock.change_pct,
                amount=stock.amount,
                turnover=stock.turnover,
                lianban_info=lianban_info,
                sectors=sectors_str,
                recent_trend=stock.recent_trend or "震荡上行",
            )
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=2048,
                system=STOCK_ANALYSIS_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text
            model_name = message.model
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            content = _build_mock_stock_report(stock)
            model_name = "mock-fallback"
    else:
        content = _build_mock_stock_report(stock)
        model_name = "mock"

    # 写入 PostgreSQL 缓存
    try:
        pool = await request.app.state.get_db()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO analysis_reports (report_type, target_id, date, content, model) "
                    "VALUES ($1, $2, $3, $4, $5) "
                    "ON CONFLICT DO NOTHING",
                    "stock", code, today, content, model_name,
                )
    except Exception as e:
        logger.warning(f"DB cache write error: {e}")

    return StockReport(
        code=code,
        name=stock.name,
        date=today,
        content=content,
        model=model_name,
        from_cache=False,
    )


@router.post("/bulk", response_model=BulkAnalysisResult)
async def analyze_bulk(body: BulkAnalysisRequest, request: Request):
    """
    生成整体市场分析报告（复盘+策略建议）
    """
    today = _today_str()
    stock_count = len(body.stock_codes)

    content: str
    model_name: str

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            md = body.market_data
            sectors_str = "、".join(md.sectors[:5]) if md and md.sectors else "人工智能、低空经济"
            prompt = BULK_ANALYSIS_TEMPLATE.format(
                date=today,
                rise=md.rise_count if md else 2341,
                fall=md.fall_count if md else 985,
                limit_up=md.limit_up_count if md else 87,
                amount=md.total_amount if md else 2.87,
                max_lianban=md.max_lianban if md else 11,
                max_stock=md.max_lianban_stock if md else "某科技",
                total=stock_count,
                sectors=sectors_str,
            )
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=3000,
                system=STOCK_ANALYSIS_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text
            model_name = message.model
        except Exception as e:
            logger.error(f"Claude API bulk error: {e}")
            content = _build_mock_bulk_report(body)
            model_name = "mock-fallback"
    else:
        content = _build_mock_bulk_report(body)
        model_name = "mock"

    return BulkAnalysisResult(
        date=today,
        content=content,
        stock_count=stock_count,
        model=model_name,
    )
