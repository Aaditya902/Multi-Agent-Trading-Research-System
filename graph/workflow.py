"""
LangGraph StateGraph workflow definition.

Topology
--------

                    START
                      │
                   node_init
                      │
        ┌─────────────┼──────────────┐
        │             │              │
   node_news    node_financial  node_sentiment
   node_technical node_sector  node_corporate
        │             │              │
        └─────────────┼──────────────┘
                      │  (fan-in / state merge)
                  node_report
                      │
                     END

All six specialist nodes run in parallel via LangGraph's
Send API / fan-out pattern. The graph merges their partial
state dicts before forwarding to node_report.
"""

from __future__ import annotations
from functools import lru_cache

from langgraph.graph import StateGraph, START, END

from graph.state import StockResearchState
from graph.nodes import (
    node_init,
    node_news,
    node_financial,
    node_sentiment,
    node_technical,
    node_sector,
    node_corporate,
    node_report,
)
from logging_config import logger


@lru_cache(maxsize=1)
def build_graph():
    """
    Compile and cache the LangGraph StateGraph.

    The graph is compiled once at startup and reused for every request.
    lru_cache(maxsize=1) ensures a single compiled instance.

    Returns:
        CompiledStateGraph ready for ainvoke / invoke calls.
    """
    logger.info("[Graph] Building StateGraph …")

    builder = StateGraph(StockResearchState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("init",      node_init)
    builder.add_node("news",      node_news)
    builder.add_node("financial", node_financial)
    builder.add_node("sentiment", node_sentiment)
    builder.add_node("technical", node_technical)
    builder.add_node("sector",    node_sector)
    builder.add_node("corporate", node_corporate)
    builder.add_node("report",    node_report)

    # ── Entry edge ────────────────────────────────────────────────────────────
    builder.add_edge(START, "init")

    # ── Fan-out: init → all 6 specialist agents (parallel) ───────────────────
    _PARALLEL_AGENTS = ["news", "financial", "sentiment", "technical", "sector", "corporate"]
    for agent in _PARALLEL_AGENTS:
        builder.add_edge("init", agent)

    # ── Fan-in: all 6 agents → report ────────────────────────────────────────
    for agent in _PARALLEL_AGENTS:
        builder.add_edge(agent, "report")

    # ── Exit ──────────────────────────────────────────────────────────────────
    builder.add_edge("report", END)

    graph = builder.compile()
    logger.info("[Graph] StateGraph compiled successfully.")
    return graph


async def run_analysis(ticker: str) -> StockResearchState:
    """
    Async entry point — runs the full multi-agent pipeline for one ticker.

    Args:
        ticker: Raw user-supplied ticker e.g. "TCS", "RELIANCE"

    Returns:
        Final StockResearchState with all agent outputs populated.
    """
    graph = build_graph()
    initial_state = StockResearchState(ticker=ticker)

    logger.info(f"[Graph] Invoking graph for ticker='{ticker}'")
    final_state_dict = await graph.ainvoke(initial_state)

    # LangGraph returns a dict — reconstruct the typed state
    final_state = StockResearchState(**final_state_dict)

    if final_state.errors:
        logger.warning(
            f"[Graph] Analysis for '{ticker}' completed with errors: "
            f"{list(final_state.errors.keys())}"
        )
    else:
        logger.info(f"[Graph] Analysis for '{ticker}' completed successfully.")

    return final_state


def run_analysis_sync(ticker: str) -> StockResearchState:
    """
    Sync wrapper around run_analysis.
    Used in non-async contexts (CLI, tests, Streamlit callbacks).
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # Already inside an event loop (e.g. FastAPI) — use nest_asyncio
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(run_analysis(ticker))
    except RuntimeError:
        # No event loop running — safe to use asyncio.run()
        return asyncio.run(run_analysis(ticker))