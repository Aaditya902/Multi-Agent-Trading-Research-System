"""
Pydantic schemas for FastAPI request/response bodies.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ─── Requests ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, description="NSE/BSE ticker symbol e.g. TCS, RELIANCE")

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class CompareRequest(BaseModel):
    stock1: str = Field(..., min_length=1, max_length=20)
    stock2: str = Field(..., min_length=1, max_length=20)

    @field_validator("stock1", "stock2")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class PortfolioRequest(BaseModel):
    stocks: list[str] = Field(..., min_length=1, max_length=20)

    @field_validator("stocks")
    @classmethod
    def uppercase_tickers(cls, v: list[str]) -> list[str]:
        return [t.strip().upper() for t in v]


# ─── Responses ────────────────────────────────────────────────────────────────

class AnalysisResponse(BaseModel):
    request_id: int
    ticker: str
    status: str  # "success" | "partial" | "error"
    report_markdown: str | None = None
    recommendation: str | None = None
    confidence_score: float | None = None
    executive_summary: str | None = None
    errors: dict[str, str] = Field(default_factory=dict)
    created_at: datetime


class CompareResponse(BaseModel):
    stock1: str
    stock2: str
    comparison_report: str
    recommendation_stock1: str | None = None
    recommendation_stock2: str | None = None
    created_at: datetime


class PortfolioResponse(BaseModel):
    stocks: list[str]
    sector_allocation: dict[str, float] = Field(default_factory=dict)
    diversification_score: float = Field(ge=0.0, le=100.0)
    risk_score: float = Field(ge=0.0, le=100.0)
    concentration_risk: str
    suggestions: list[str] = Field(default_factory=list)
    detailed_report: str | None = None
    created_at: datetime


class MarketBriefResponse(BaseModel):
    date: str
    report_markdown: str
    nifty_change_pct: float | None = None
    sensex_change_pct: float | None = None
    top_gainers: list[dict] = Field(default_factory=list)
    top_losers: list[dict] = Field(default_factory=list)
    created_at: datetime


class HistoryItem(BaseModel):
    id: int
    ticker: str
    recommendation: str | None
    confidence_score: float | None
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None