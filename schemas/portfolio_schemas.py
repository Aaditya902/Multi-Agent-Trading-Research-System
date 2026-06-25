"""
Pydantic schemas for the Portfolio Intelligence module.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class StockWeight(BaseModel):
    ticker: str
    weight_pct: float = Field(ge=0.0, le=100.0)
    sector: str | None = None
    current_price: float | None = None
    recommendation: str | None = None
    confidence_score: float | None = None


class SectorAllocation(BaseModel):
    sector: str
    weight_pct: float
    tickers: list[str] = Field(default_factory=list)


class ConcentrationRisk(BaseModel):
    level: str  # "Low" | "Medium" | "High" | "Very High"
    top_holding_pct: float
    top_sector_pct: float
    herfindahl_index: float  # Portfolio concentration metric


class PortfolioDiversification(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    sector_count: int
    stock_count: int
    interpretation: str


class PortfolioRisk(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    level: str  # "Low" | "Moderate" | "High" | "Very High"
    avg_beta: float | None = None
    interpretation: str


class PortfolioInsight(BaseModel):
    """Complete portfolio intelligence output."""
    stocks: list[StockWeight] = Field(default_factory=list)
    sector_allocation: list[SectorAllocation] = Field(default_factory=list)
    diversification: PortfolioDiversification
    risk: PortfolioRisk
    concentration: ConcentrationRisk
    suggestions: list[str] = Field(default_factory=list)
    overall_recommendation: str
    detailed_report: str | None = None