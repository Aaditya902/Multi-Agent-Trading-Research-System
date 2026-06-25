"""
SQLAlchemy ORM models.
All tables are created automatically by init_db() on startup.
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Integer, String, Float, Text, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AnalysisRequest(Base):
    """Tracks every incoming analysis request."""
    __tablename__ = "analysis_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_type: Mapped[str] = mapped_column(String(20))  # "analyze" | "compare" | "portfolio" | "market_brief"
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending" | "success" | "partial" | "error"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report: Mapped[AnalysisReport | None] = relationship("AnalysisReport", back_populates="request", uselist=False)

    __table_args__ = (
        Index("ix_requests_ticker", "ticker"),
        Index("ix_requests_created_at", "created_at"),
    )


class AnalysisReport(Base):
    """Stores the full generated report for a request."""
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_requests.id"), unique=True)
    ticker: Mapped[str] = mapped_column(String(20))
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    report_markdown: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Store raw agent outputs as JSON for future reuse / caching
    news_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    financial_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sentiment_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    technical_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sector_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    corporate_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[AnalysisRequest] = relationship("AnalysisRequest", back_populates="report")

    __table_args__ = (
        Index("ix_reports_ticker", "ticker"),
        Index("ix_reports_recommendation", "recommendation"),
    )


class PortfolioAnalysis(Base):
    """Persists portfolio analysis results."""
    __tablename__ = "portfolio_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tickers: Mapped[list] = mapped_column(JSON)  # ["TCS", "RELIANCE", ...]
    sector_allocation: Mapped[dict] = mapped_column(JSON, default=dict)
    diversification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    concentration_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    detailed_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketBrief(Base):
    """Daily market brief cache."""
    __tablename__ = "market_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True)  # "YYYY-MM-DD"
    report_markdown: Mapped[str] = mapped_column(Text)
    nifty_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensex_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_gainers: Mapped[list] = mapped_column(JSON, default=list)
    top_losers: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_briefs_date", "date"),)