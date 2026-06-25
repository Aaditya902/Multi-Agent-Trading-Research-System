"""
Pydantic schemas for all agent outputs.
Every agent returns one of these typed models — no raw dicts.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ─── News Agent ───────────────────────────────────────────────────────────────

class NewsOutput(BaseModel):
    stock: str
    news_summary: str
    bullish_news: list[str] = Field(default_factory=list)
    bearish_news: list[str] = Field(default_factory=list)
    overall_news_impact: str  # "Positive" | "Negative" | "Neutral"
    headlines: list[str] = Field(default_factory=list)


# ─── Financial Agent ──────────────────────────────────────────────────────────

class FinancialMetrics(BaseModel):
    current_price: float | None = None
    market_cap: float | None = None
    revenue: float | None = None
    revenue_growth: float | None = None
    eps: float | None = None
    pe_ratio: float | None = None
    roe: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    free_cash_flow: float | None = None
    dividend_yield: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    beta: float | None = None


class FinancialOutput(BaseModel):
    stock: str
    financial_health: str  # "Strong" | "Moderate" | "Weak"
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation: str  # "Overvalued" | "Fairly Valued" | "Undervalued"
    metrics: FinancialMetrics = Field(default_factory=FinancialMetrics)


# ─── Sentiment Agent ──────────────────────────────────────────────────────────

class SentimentOutput(BaseModel):
    stock: str
    sentiment: str  # "Bullish" | "Neutral" | "Bearish"
    score: float = Field(ge=-1.0, le=1.0)
    explanation: str
    positive_score: float = Field(default=0.0, ge=0.0, le=1.0)
    negative_score: float = Field(default=0.0, ge=0.0, le=1.0)
    neutral_score: float = Field(default=0.0, ge=0.0, le=1.0)


# ─── Technical Agent ──────────────────────────────────────────────────────────

class TechnicalOutput(BaseModel):
    stock: str
    trend: str  # "Uptrend" | "Downtrend" | "Sideways"
    rsi: float | None = None
    macd_signal: str  # "Bullish" | "Bearish" | "Neutral"
    moving_average_signal: str  # "Bullish" | "Bearish" | "Neutral"
    bollinger_signal: str  # "Overbought" | "Oversold" | "Normal"
    technical_summary: str
    sma_50: float | None = None
    sma_200: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    bb_middle: float | None = None
    current_price: float | None = None


# ─── Sector Agent ─────────────────────────────────────────────────────────────

class PeerData(BaseModel):
    ticker: str
    name: str
    pe_ratio: float | None = None
    market_cap: float | None = None
    revenue_growth: float | None = None
    roe: float | None = None
    profit_margin: float | None = None


class SectorOutput(BaseModel):
    stock: str
    sector: str
    peers: list[PeerData] = Field(default_factory=list)
    peer_comparison: list[dict[str, Any]] = Field(default_factory=list)
    sector_strength: str  # "Strong" | "Average" | "Weak"
    relative_position: str  # "Leader" | "Average" | "Laggard"
    sector_pe_avg: float | None = None
    sector_growth_avg: float | None = None


# ─── Corporate Actions Agent ──────────────────────────────────────────────────

class CorporateAction(BaseModel):
    action_type: str  # "Dividend" | "Split" | "Bonus" | "Buyback" | "Announcement"
    date: str | None = None
    details: str
    impact: str  # "Positive" | "Negative" | "Neutral"


class CorporateOutput(BaseModel):
    stock: str
    corporate_actions: list[CorporateAction] = Field(default_factory=list)
    impact: str  # "Positive" | "Negative" | "Neutral"
    summary: str


# ─── Report Agent ─────────────────────────────────────────────────────────────

class ReportOutput(BaseModel):
    stock: str
    ticker: str
    report_markdown: str
    recommendation: str  # "Strong Buy" | "Buy" | "Hold" | "Sell" | "Strong Sell"
    confidence_score: float = Field(ge=0.0, le=100.0)
    executive_summary: str
    generated_at: str


# ─── Aggregated Analysis State ────────────────────────────────────────────────

class StockAnalysisResult(BaseModel):
    """Complete result after all agents have run."""
    ticker: str
    company_name: str | None = None
    news: NewsOutput | None = None
    financial: FinancialOutput | None = None
    sentiment: SentimentOutput | None = None
    technical: TechnicalOutput | None = None
    sector: SectorOutput | None = None
    corporate: CorporateOutput | None = None
    report: ReportOutput | None = None
    errors: dict[str, str] = Field(default_factory=dict)
    analysis_duration_seconds: float | None = None