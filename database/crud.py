"""
CRUD operations for all database models.
All functions are async and accept an AsyncSession from the FastAPI dependency.
"""

from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AnalysisRequest, AnalysisReport, PortfolioAnalysis, MarketBrief
from schemas.analysis_schemas import StockAnalysisResult
from logging_config import logger


# ─── AnalysisRequest ──────────────────────────────────────────────────────────

async def create_request(
    db: AsyncSession,
    request_type: str,
    ticker: str | None = None,
    payload: dict | None = None,
) -> AnalysisRequest:
    req = AnalysisRequest(
        request_type=request_type,
        ticker=ticker,
        payload=payload or {},
        status="pending",
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    logger.debug(f"Created request id={req.id} type={request_type} ticker={ticker}")
    return req


async def update_request_status(
    db: AsyncSession,
    request_id: int,
    status: str,
    duration_seconds: float | None = None,
    error_message: str | None = None,
) -> None:
    result = await db.get(AnalysisRequest, request_id)
    if result:
        result.status = status
        result.updated_at = datetime.utcnow()
        if duration_seconds is not None:
            result.duration_seconds = duration_seconds
        if error_message is not None:
            result.error_message = error_message
    await db.flush()


async def get_request(db: AsyncSession, request_id: int) -> AnalysisRequest | None:
    return await db.get(AnalysisRequest, request_id)


async def list_requests(
    db: AsyncSession,
    ticker: str | None = None,
    limit: int = 50,
) -> list[AnalysisRequest]:
    stmt = select(AnalysisRequest).order_by(desc(AnalysisRequest.created_at)).limit(limit)
    if ticker:
        stmt = stmt.where(AnalysisRequest.ticker == ticker.upper())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── AnalysisReport ───────────────────────────────────────────────────────────

async def save_report(
    db: AsyncSession,
    request_id: int,
    result: StockAnalysisResult,
) -> AnalysisReport:
    """Persist the full analysis result from LangGraph."""
    report = AnalysisReport(
        request_id=request_id,
        ticker=result.ticker,
        company_name=result.company_name,
        report_markdown=result.report.report_markdown if result.report else "",
        recommendation=result.report.recommendation if result.report else None,
        confidence_score=result.report.confidence_score if result.report else None,
        executive_summary=result.report.executive_summary if result.report else None,
        news_output=result.news.model_dump() if result.news else None,
        financial_output=result.financial.model_dump() if result.financial else None,
        sentiment_output=result.sentiment.model_dump() if result.sentiment else None,
        technical_output=result.technical.model_dump() if result.technical else None,
        sector_output=result.sector.model_dump() if result.sector else None,
        corporate_output=result.corporate.model_dump() if result.corporate else None,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    logger.info(f"Saved report id={report.id} ticker={result.ticker} recommendation={report.recommendation}")
    return report


async def get_report_by_request(
    db: AsyncSession, request_id: int
) -> AnalysisReport | None:
    stmt = select(AnalysisReport).where(AnalysisReport.request_id == request_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_report_for_ticker(
    db: AsyncSession, ticker: str
) -> AnalysisReport | None:
    stmt = (
        select(AnalysisReport)
        .where(AnalysisReport.ticker == ticker.upper())
        .order_by(desc(AnalysisReport.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_reports(
    db: AsyncSession, limit: int = 50
) -> list[AnalysisReport]:
    stmt = select(AnalysisReport).order_by(desc(AnalysisReport.created_at)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── PortfolioAnalysis ────────────────────────────────────────────────────────

async def save_portfolio_analysis(
    db: AsyncSession,
    tickers: list[str],
    sector_allocation: dict,
    diversification_score: float,
    risk_score: float,
    concentration_risk: str,
    suggestions: list[str],
    detailed_report: str | None = None,
) -> PortfolioAnalysis:
    pa = PortfolioAnalysis(
        tickers=tickers,
        sector_allocation=sector_allocation,
        diversification_score=diversification_score,
        risk_score=risk_score,
        concentration_risk=concentration_risk,
        suggestions=suggestions,
        detailed_report=detailed_report,
    )
    db.add(pa)
    await db.flush()
    await db.refresh(pa)
    return pa


# ─── MarketBrief ──────────────────────────────────────────────────────────────

async def get_today_brief(db: AsyncSession) -> MarketBrief | None:
    today = date.today().isoformat()
    stmt = select(MarketBrief).where(MarketBrief.date == today)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def save_market_brief(
    db: AsyncSession,
    report_markdown: str,
    nifty_change_pct: float | None = None,
    sensex_change_pct: float | None = None,
    top_gainers: list | None = None,
    top_losers: list | None = None,
) -> MarketBrief:
    today = date.today().isoformat()
    # Upsert: delete stale entry if exists
    existing = await get_today_brief(db)
    if existing:
        await db.delete(existing)
        await db.flush()

    brief = MarketBrief(
        date=today,
        report_markdown=report_markdown,
        nifty_change_pct=nifty_change_pct,
        sensex_change_pct=sensex_change_pct,
        top_gainers=top_gainers or [],
        top_losers=top_losers or [],
    )
    db.add(brief)
    await db.flush()
    await db.refresh(brief)
    logger.info(f"Saved market brief for {today}")
    return brief