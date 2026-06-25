"""
FastAPI route definitions for all four API endpoints.

POST /analyze          — Full single-stock analysis
POST /compare          — Side-by-side two-stock comparison
POST /portfolio/analyze — Portfolio intelligence
GET  /market-brief     — Daily Indian market summary
GET  /history          — Recent analysis history
GET  /history/{ticker} — History for a specific ticker
"""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from logging_config import logger
from api.dependencies import get_db, get_gemini_client, get_gemini_model_name
from schemas.api_schemas import (
    AnalyzeRequest, CompareRequest, PortfolioRequest,
    AnalysisResponse, CompareResponse, PortfolioResponse,
    MarketBriefResponse, HistoryItem, ErrorResponse,
)
from graph.workflow import run_analysis
from agents.report_agent import run_comparison_report
from services.portfolio_service import analyse_portfolio
from services.market_brief_service import generate_market_brief
from services.ticker_resolver import resolve_ticker, get_company_name
from database import crud

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# POST /analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse a single Indian stock",
    description=(
        "Runs all 6 specialist agents in parallel (news, financial, sentiment, "
        "technical, sector, corporate) then generates a full research report via Gemini."
    ),
    tags=["Analysis"],
)
async def analyze_stock(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    ticker = request.ticker
    logger.info(f"[API /analyze] Received request for ticker='{ticker}'")

    # ── Persist the incoming request ──────────────────────────────────────────
    db_request = await crud.create_request(
        db,
        request_type="analyze",
        ticker=ticker,
        payload=request.model_dump(),
    )
    request_id = db_request.id
    start_time = time.time()

    try:
        # ── Run LangGraph pipeline ────────────────────────────────────────────
        final_state = await run_analysis(ticker)

        duration = round(time.time() - start_time, 2)
        status   = "partial" if final_state.errors else "success"

        # ── Persist the report ────────────────────────────────────────────────
        from schemas.analysis_schemas import StockAnalysisResult
        result_obj = StockAnalysisResult(
            ticker=resolve_ticker(ticker),
            company_name=get_company_name(resolve_ticker(ticker)),
            news=final_state.news,
            financial=final_state.financial,
            sentiment=final_state.sentiment,
            technical=final_state.technical,
            sector=final_state.sector,
            corporate=final_state.corporate,
            report=final_state.report,
            errors=final_state.errors,
            analysis_duration_seconds=duration,
        )
        await crud.save_report(db, request_id, result_obj)
        await crud.update_request_status(db, request_id, status, duration)

        report    = final_state.report
        rec       = report.recommendation   if report else None
        conf      = report.confidence_score if report else None
        exec_sum  = report.executive_summary if report else None
        report_md = report.report_markdown   if report else "Report generation failed."

        logger.info(
            f"[API /analyze] Completed '{ticker}' in {duration}s — "
            f"status={status}, recommendation={rec}"
        )

        return AnalysisResponse(
            request_id=request_id,
            ticker=ticker,
            status=status,
            report_markdown=report_md,
            recommendation=rec,
            confidence_score=conf,
            executive_summary=exec_sum,
            errors=final_state.errors,
            created_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"[API /analyze] Unhandled error for '{ticker}': {e}", exc_info=True)
        await crud.update_request_status(
            db, request_id, "error",
            duration_seconds=duration,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /compare
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare two Indian stocks side-by-side",
    description=(
        "Runs full analysis on both stocks in parallel, then generates a "
        "Gemini-powered head-to-head comparison report."
    ),
    tags=["Analysis"],
)
async def compare_stocks(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
) -> CompareResponse:
    ticker1 = request.stock1
    ticker2 = request.stock2
    logger.info(f"[API /compare] {ticker1} vs {ticker2}")

    if ticker1 == ticker2:
        raise HTTPException(status_code=400, detail="stock1 and stock2 must be different tickers.")

    # ── Persist request ────────────────────────────────────────────────────────
    db_req = await crud.create_request(
        db,
        request_type="compare",
        payload=request.model_dump(),
    )
    start_time = time.time()

    try:
        # ── Run both analyses in parallel ─────────────────────────────────────
        state1, state2 = await asyncio.gather(
            run_analysis(ticker1),
            run_analysis(ticker2),
            return_exceptions=False,
        )

        report_md1 = state1.report.report_markdown if state1.report else ""
        report_md2 = state2.report.report_markdown if state2.report else ""

        # ── Generate comparison report ────────────────────────────────────────
        comparison_md = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_comparison_report(ticker1, report_md1, ticker2, report_md2),
        )

        rec1 = state1.report.recommendation if state1.report else None
        rec2 = state2.report.recommendation if state2.report else None

        duration = round(time.time() - start_time, 2)
        await crud.update_request_status(db, db_req.id, "success", duration)

        logger.info(
            f"[API /compare] Completed {ticker1} vs {ticker2} in {duration}s — "
            f"rec1={rec1}, rec2={rec2}"
        )

        return CompareResponse(
            stock1=ticker1,
            stock2=ticker2,
            comparison_report=comparison_md,
            recommendation_stock1=rec1,
            recommendation_stock2=rec2,
            created_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"[API /compare] Error comparing {ticker1} vs {ticker2}: {e}", exc_info=True)
        await crud.update_request_status(db, db_req.id, "error", duration, str(e))
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /portfolio/analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/portfolio/analyze",
    response_model=PortfolioResponse,
    summary="Analyse a portfolio of Indian stocks",
    description=(
        "Computes sector allocation, diversification score, risk score, "
        "concentration risk, and actionable suggestions for a list of tickers."
    ),
    tags=["Portfolio"],
)
async def analyze_portfolio(
    request: PortfolioRequest,
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    tickers = request.stocks
    logger.info(f"[API /portfolio] Received {len(tickers)} tickers: {tickers}")

    if len(tickers) < 1:
        raise HTTPException(status_code=400, detail="At least 1 stock required.")
    if len(tickers) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 stocks per portfolio request.")

    db_req = await crud.create_request(
        db,
        request_type="portfolio",
        payload=request.model_dump(),
    )
    start_time = time.time()

    try:
        # Portfolio analysis is CPU-bound (yfinance calls) — run in executor
        loop    = asyncio.get_event_loop()
        insight = await loop.run_in_executor(None, analyse_portfolio, tickers)

        # Build sector allocation dict for response
        sector_alloc_dict = {
            sa.sector: sa.weight_pct
            for sa in insight.sector_allocation
        }

        # Persist
        await crud.save_portfolio_analysis(
            db,
            tickers=tickers,
            sector_allocation=sector_alloc_dict,
            diversification_score=insight.diversification.score,
            risk_score=insight.risk.score,
            concentration_risk=insight.concentration.level,
            suggestions=insight.suggestions,
            detailed_report=insight.overall_recommendation,
        )

        duration = round(time.time() - start_time, 2)
        await crud.update_request_status(db, db_req.id, "success", duration)

        logger.info(
            f"[API /portfolio] Completed {len(tickers)} stocks in {duration}s — "
            f"div_score={insight.diversification.score}, risk={insight.risk.level}"
        )

        return PortfolioResponse(
            stocks=tickers,
            sector_allocation=sector_alloc_dict,
            diversification_score=insight.diversification.score,
            risk_score=insight.risk.score,
            concentration_risk=insight.concentration.level,
            suggestions=insight.suggestions,
            detailed_report=insight.overall_recommendation,
            created_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"[API /portfolio] Error: {e}", exc_info=True)
        await crud.update_request_status(db, db_req.id, "error", duration, str(e))
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /market-brief
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/market-brief",
    response_model=MarketBriefResponse,
    summary="Get today's Indian market brief",
    description=(
        "Returns a Gemini-generated daily brief covering NIFTY 50, SENSEX, "
        "top gainers/losers, and sector highlights. Cached once per day."
    ),
    tags=["Market"],
)
async def get_market_brief(
    db: AsyncSession = Depends(get_db),
    gemini_client=Depends(get_gemini_client),
    model_name: str = Depends(get_gemini_model_name),
) -> MarketBriefResponse:
    logger.info("[API /market-brief] Request received")

    # ── Check cache (one per calendar day) ───────────────────────────────────
    cached = await crud.get_today_brief(db)
    if cached:
        logger.info(f"[API /market-brief] Returning cached brief for {cached.date}")
        return MarketBriefResponse(
            date=cached.date,
            report_markdown=cached.report_markdown,
            nifty_change_pct=cached.nifty_change_pct,
            sensex_change_pct=cached.sensex_change_pct,
            top_gainers=cached.top_gainers,
            top_losers=cached.top_losers,
            created_at=cached.created_at,
        )

    # ── Generate fresh brief ──────────────────────────────────────────────────
    try:
        # Build a thin model-like object that market_brief_service expects
        class _GeminiShim:
            def __init__(self, client, model):
                self._client = client
                self._model  = model
            def generate_content(self, prompt: str):
                return self._client.models.generate_content(
                    model=self._model, contents=prompt
                )

        shim   = _GeminiShim(gemini_client, model_name)
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, generate_market_brief, shim)

        # Persist
        brief = await crud.save_market_brief(
            db,
            report_markdown=result["report_markdown"],
            nifty_change_pct=result.get("nifty_change_pct"),
            sensex_change_pct=result.get("sensex_change_pct"),
            top_gainers=result.get("top_gainers", []),
            top_losers=result.get("top_losers", []),
        )

        logger.info(f"[API /market-brief] Generated and cached brief for {result['date']}")

        return MarketBriefResponse(
            date=result["date"],
            report_markdown=result["report_markdown"],
            nifty_change_pct=result.get("nifty_change_pct"),
            sensex_change_pct=result.get("sensex_change_pct"),
            top_gainers=result.get("top_gainers", []),
            top_losers=result.get("top_losers", []),
            created_at=brief.created_at,
        )

    except Exception as e:
        logger.error(f"[API /market-brief] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Market brief generation failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=list[HistoryItem],
    summary="List recent stock analysis requests",
    tags=["History"],
)
async def get_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[HistoryItem]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100.")

    reports = await crud.list_reports(db, limit=limit)
    return [
        HistoryItem(
            id=r.id,
            ticker=r.ticker,
            recommendation=r.recommendation,
            confidence_score=r.confidence_score,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get(
    "/history/{ticker}",
    response_model=list[HistoryItem],
    summary="Get analysis history for a specific ticker",
    tags=["History"],
)
async def get_ticker_history(
    ticker: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[HistoryItem]:
    ticker = ticker.upper()
    requests = await crud.list_requests(db, ticker=ticker, limit=limit)
    items: list[HistoryItem] = []
    for req in requests:
        report = await crud.get_report_by_request(db, req.id)
        items.append(HistoryItem(
            id=req.id,
            ticker=ticker,
            recommendation=report.recommendation if report else None,
            confidence_score=report.confidence_score if report else None,
            created_at=req.created_at,
        ))
    return items


# ─────────────────────────────────────────────────────────────────────────────
# GET /report/{request_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/report/{request_id}",
    response_model=AnalysisResponse,
    summary="Retrieve a previously generated report by request ID",
    tags=["History"],
)
async def get_report(
    request_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    report = await crud.get_report_by_request(db, request_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No report found for request_id={request_id}")

    req = await crud.get_request(db, request_id)

    return AnalysisResponse(
        request_id=request_id,
        ticker=report.ticker,
        status=req.status if req else "unknown",
        report_markdown=report.report_markdown,
        recommendation=report.recommendation,
        confidence_score=report.confidence_score,
        executive_summary=report.executive_summary,
        errors={},
        created_at=report.created_at,
    )