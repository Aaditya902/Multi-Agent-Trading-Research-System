"""
Entry point — Multi-Agent Indian Stock Research & Portfolio Intelligence Platform.

Start the server:
    python app.py
    uvicorn app:create_app --factory --host 0.0.0.0 --port 8000 --reload

API docs:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

from __future__ import annotations
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from logging_config import logger  # noqa: E402


@asynccontextmanager
async def lifespan(app):
    """Startup and shutdown lifecycle handler."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("=== Indian Stock Research Platform — starting up ===")

    from database.session import init_db
    await init_db()
    logger.info("Database initialised.")

    # Pre-compile the LangGraph — avoids cold-start latency on first request
    from graph.workflow import build_graph
    build_graph()
    logger.info("LangGraph compiled and cached.")

    # Validate Gemini key early so we fail fast
    from api.dependencies import get_gemini_client
    try:
        get_gemini_client()
        logger.info("Gemini client ready.")
    except Exception as e:
        logger.error(f"Gemini client init failed: {e} — check GEMINI_API_KEY in .env")

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("=== Indian Stock Research Platform — shutting down ===")


def create_app():
    """
    Application factory.
    Called by uvicorn when launched with --factory flag.
    """
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from api.routes import router

    app = FastAPI(
        title="Multi-Agent Indian Stock Research Platform",
        description=(
            "AI-powered institutional-grade equity research for Indian stocks (NSE/BSE). "
            "Powered by Gemini, LangGraph, FinBERT, and yfinance. **100% free to run.**\n\n"
            "### Endpoints\n"
            "- `POST /api/v1/analyze` — Full stock analysis\n"
            "- `POST /api/v1/compare` — Head-to-head stock comparison\n"
            "- `POST /api/v1/portfolio/analyze` — Portfolio intelligence\n"
            "- `GET  /api/v1/market-brief` — Daily Indian market brief\n"
            "- `GET  /api/v1/history` — Recent analysis history\n"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check server logs."},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Service health check")
    async def health():
        return {
            "status": "ok",
            "service": "indian-stock-platform",
            "version": "1.0.0",
        }

    return app


if __name__ == "__main__":
    host   = os.getenv("APP_HOST", "0.0.0.0")
    port   = int(os.getenv("APP_PORT", "8000"))
    reload = os.getenv("APP_ENV", "development") == "development"

    logger.info(f"Launching uvicorn on {host}:{port} | reload={reload}")
    uvicorn.run(
        "app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )