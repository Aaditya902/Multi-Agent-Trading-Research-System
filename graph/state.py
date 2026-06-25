"""
LangGraph typed state definition.
StockResearchState is the single shared state object that flows
through the entire graph — from START through all agents to END.
"""

from __future__ import annotations
from typing import Annotated
import operator
from pydantic import BaseModel, Field

from schemas.analysis_schemas import (
    NewsOutput, FinancialOutput, SentimentOutput,
    TechnicalOutput, SectorOutput, CorporateOutput,
    ReportOutput,
)


class StockResearchState(BaseModel):
    """
    Shared state for the stock research LangGraph workflow.

    Fields set by the orchestrator (input):
        ticker          — raw user ticker e.g. "TCS"

    Fields populated by parallel specialist agents:
        news, financial, sentiment, technical, sector, corporate

    Fields populated by the report agent (final):
        report

    Error tracking:
        errors          — dict mapping agent_name → error message
                          uses operator.or_ to merge dicts from parallel branches

    Timing:
        start_time      — epoch float, set at graph entry
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    ticker: str

    # ── Agent outputs (None until each agent runs) ────────────────────────────
    news:      NewsOutput      | None = None
    financial: FinancialOutput | None = None
    sentiment: SentimentOutput | None = None
    technical: TechnicalOutput | None = None
    sector:    SectorOutput    | None = None
    corporate: CorporateOutput | None = None
    report:    ReportOutput    | None = None

    # ── Error map — merged with dict union across parallel branches ───────────
    # Annotated with operator.or_ so LangGraph merges dicts instead of overwriting
    errors: Annotated[dict[str, str], operator.or_] = Field(default_factory=dict)

    # ── Metadata ──────────────────────────────────────────────────────────────
    start_time: float | None = None

    class Config:
        arbitrary_types_allowed = True


class CompareState(BaseModel):
    """State for the stock comparison workflow."""
    ticker1: str
    ticker2: str
    result1: StockResearchState | None = None
    result2: StockResearchState | None = None
    comparison_report: str | None = None
    errors: Annotated[dict[str, str], operator.or_] = Field(default_factory=dict)


class PortfolioState(BaseModel):
    """State for the portfolio analysis workflow."""
    tickers: list[str]
    individual_results: list[StockResearchState] = Field(default_factory=list)
    portfolio_report: str | None = None
    errors: Annotated[dict[str, str], operator.or_] = Field(default_factory=dict)