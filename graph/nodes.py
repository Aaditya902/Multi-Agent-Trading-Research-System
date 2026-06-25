"""
LangGraph node functions.
Each node wraps one agent call and updates the shared StockResearchState.
Errors are caught and stored in state.errors — never raised — so one
failing agent never stops the rest of the pipeline.
"""

from __future__ import annotations
import time

from logging_config import logger
from graph.state import StockResearchState


# ── Entry node ────────────────────────────────────────────────────────────────

def node_init(state: StockResearchState) -> dict:
    """Record start time at graph entry."""
    logger.info(f"[Graph] Starting analysis for ticker='{state.ticker}'")
    return {"start_time": time.time()}


# ── Specialist agent nodes (run in parallel) ──────────────────────────────────

def node_news(state: StockResearchState) -> dict:
    """Run the News Agent."""
    try:
        from agents.news_agent import run_news_agent
        logger.info(f"[Graph:NewsNode] Running for {state.ticker}")
        result = run_news_agent(state.ticker)
        return {"news": result}
    except Exception as e:
        logger.error(f"[Graph:NewsNode] Failed: {e}")
        return {"errors": {"news_agent": str(e)}}


def node_financial(state: StockResearchState) -> dict:
    """Run the Financial Agent."""
    try:
        from agents.financial_agent import run_financial_agent
        logger.info(f"[Graph:FinancialNode] Running for {state.ticker}")
        result = run_financial_agent(state.ticker)
        return {"financial": result}
    except Exception as e:
        logger.error(f"[Graph:FinancialNode] Failed: {e}")
        return {"errors": {"financial_agent": str(e)}}


def node_sentiment(state: StockResearchState) -> dict:
    """
    Run the Sentiment Agent.
    Passes headlines from the News Agent output if already available in state,
    otherwise the sentiment agent fetches its own text.
    """
    try:
        from agents.sentiment_agent import run_sentiment_agent
        logger.info(f"[Graph:SentimentNode] Running for {state.ticker}")

        headlines = []
        if state.news and state.news.headlines:
            headlines = state.news.headlines

        result = run_sentiment_agent(state.ticker, headlines=headlines)
        return {"sentiment": result}
    except Exception as e:
        logger.error(f"[Graph:SentimentNode] Failed: {e}")
        return {"errors": {"sentiment_agent": str(e)}}


def node_technical(state: StockResearchState) -> dict:
    """Run the Technical Analysis Agent."""
    try:
        from agents.technical_agent import run_technical_agent
        logger.info(f"[Graph:TechnicalNode] Running for {state.ticker}")
        result = run_technical_agent(state.ticker)
        return {"technical": result}
    except Exception as e:
        logger.error(f"[Graph:TechnicalNode] Failed: {e}")
        return {"errors": {"technical_agent": str(e)}}


def node_sector(state: StockResearchState) -> dict:
    """Run the Sector Analysis Agent."""
    try:
        from agents.sector_agent import run_sector_agent
        logger.info(f"[Graph:SectorNode] Running for {state.ticker}")
        result = run_sector_agent(state.ticker)
        return {"sector": result}
    except Exception as e:
        logger.error(f"[Graph:SectorNode] Failed: {e}")
        return {"errors": {"sector_agent": str(e)}}


def node_corporate(state: StockResearchState) -> dict:
    """Run the Corporate Actions Agent."""
    try:
        from agents.corporate_agent import run_corporate_agent
        logger.info(f"[Graph:CorporateNode] Running for {state.ticker}")
        result = run_corporate_agent(state.ticker)
        return {"corporate": result}
    except Exception as e:
        logger.error(f"[Graph:CorporateNode] Failed: {e}")
        return {"errors": {"corporate_agent": str(e)}}


# ── Report node (runs after all parallel agents complete) ─────────────────────

def node_report(state: StockResearchState) -> dict:
    """
    Run the Report Agent.
    All specialist agent outputs from state are passed in.
    Partial results are accepted — agent failures produce None fields,
    and the report agent handles missing data gracefully.
    """
    try:
        from agents.report_agent import run_report_agent
        logger.info(
            f"[Graph:ReportNode] Generating report for {state.ticker} "
            f"(available agents: news={state.news is not None}, "
            f"financial={state.financial is not None}, "
            f"sentiment={state.sentiment is not None}, "
            f"technical={state.technical is not None}, "
            f"sector={state.sector is not None}, "
            f"corporate={state.corporate is not None})"
        )
        result = run_report_agent(
            ticker=state.ticker,
            news=state.news,
            financial=state.financial,
            sentiment=state.sentiment,
            technical=state.technical,
            sector=state.sector,
            corporate=state.corporate,
        )
        elapsed = round(time.time() - (state.start_time or time.time()), 2)
        logger.info(f"[Graph:ReportNode] Done for {state.ticker} in {elapsed}s")
        return {"report": result}
    except Exception as e:
        logger.error(f"[Graph:ReportNode] Failed: {e}")
        return {"errors": {"report_agent": str(e)}}