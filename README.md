# 📈 Multi-Agent Indian Stock Research & Portfolio Intelligence Platform

An AI-powered, institutional-quality equity research platform for Indian stocks listed on **NSE/BSE**. Six specialist agents run in parallel, powered by **Gemini**, orchestrated by **LangGraph**, with sentiment analysis via **FinBERT** — all completely free to run.

---

## 📸 What It Does

| Feature | Description |
|---|---|
| **Stock Analysis** | Full research report for any NSE/BSE stock — news, financials, sentiment, technical, sector, corporate actions |
| **Stock Comparison** | Head-to-head Gemini-powered comparison between two stocks |
| **Portfolio Analysis** | Sector allocation, diversification score, risk score, concentration risk, suggestions |
| **Market Brief** | Daily AI-generated NIFTY 50 / SENSEX summary with top gainers & losers |

---

## 🏗️ Architecture

```
User Request
     │
     ▼
Orchestrator (LangGraph StateGraph)
     │
     ├─────────────────────────────────────────────┐
     ▼          ▼           ▼          ▼       ▼   ▼
  News      Financial   Sentiment  Technical Sector Corporate
  Agent      Agent       Agent      Agent    Agent   Agent
 (RSS)     (yfinance)  (FinBERT) (pandas-ta) (peers) (yfinance)
     │          │           │          │       │       │
     └──────────┴───────────┴──────────┴───────┴───────┘
                               │
                               ▼
                         Report Agent
                           (Gemini)
                               │
                               ▼
                    Institutional Research Report
                    (Strong Buy → Strong Sell)
```

### Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 1.5 Flash (free tier) |
| Agent Orchestration | LangGraph StateGraph |
| Sentiment Analysis | FinBERT (ProsusAI/finbert) |
| Financial Data | yfinance |
| Technical Analysis | pandas-ta |
| News | Google News RSS |
| Backend API | FastAPI + uvicorn |
| Frontend | Streamlit |
| Database | SQLite + SQLAlchemy (async) |
| PDF Export | fpdf2 |

---

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd indian_stock_platform
```

### 2. Create and activate a virtual environment

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** FinBERT (~440 MB) and PyTorch will be downloaded on first run. This is a one-time download.

### 4. Set your Gemini API key

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Get a free key at → **https://aistudio.google.com/app/apikey**

### 5. Start the FastAPI backend

```bash
python app.py
```

Server starts at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

### 6. Start the Streamlit frontend

Open a **second terminal** (with venv activated):

```bash
streamlit run frontend/app.py
```

Frontend opens at `http://localhost:8501`

---

## 📁 Project Structure

```
indian_stock_platform/
│
├── agents/                     # 7 specialist AI agents
│   ├── news_agent.py           # Google News RSS → Gemini summary
│   ├── financial_agent.py      # yfinance fundamentals analyser
│   ├── sentiment_agent.py      # FinBERT market sentiment
│   ├── technical_agent.py      # pandas-ta indicators (RSI, MACD, BB, MA)
│   ├── sector_agent.py         # Peer comparison & sector position
│   ├── corporate_agent.py      # Dividends, splits, buybacks, earnings
│   └── report_agent.py         # Gemini report + recommendation generator
│
├── graph/                      # LangGraph orchestration
│   ├── state.py                # Typed StockResearchState (Pydantic)
│   ├── nodes.py                # Node functions with error isolation
│   └── workflow.py             # StateGraph — parallel fan-out/fan-in
│
├── tools/                      # Data fetching utilities
│   ├── yfinance_tool.py        # yfinance wrappers with retry
│   ├── news_rss_tool.py        # Google News + financial RSS feeds
│   ├── finbert_tool.py         # FinBERT pipeline + keyword fallback
│   └── technical_tool.py      # pandas-ta indicator computation
│
├── prompts/                    # Gemini prompt templates
│   ├── report_prompt.py        # Full research report + comparison prompt
│   ├── news_prompt.py          # Structured news summary prompt
│   └── sector_prompt.py        # Sector analysis + market brief prompt
│
├── schemas/                    # Pydantic models
│   ├── analysis_schemas.py     # Agent output schemas
│   ├── api_schemas.py          # FastAPI request/response schemas
│   └── portfolio_schemas.py    # Portfolio intelligence schemas
│
├── database/                   # SQLite persistence
│   ├── models.py               # SQLAlchemy ORM models
│   ├── session.py              # Async engine + get_db dependency
│   └── crud.py                 # CRUD operations for all tables
│
├── api/                        # FastAPI backend
│   ├── routes.py               # All endpoint handlers
│   └── dependencies.py         # Gemini client, DB session injection
│
├── frontend/                   # Streamlit UI
│   ├── app.py                  # Entry point + sidebar + routing
│   ├── pages.py                # 4 page implementations
│   └── components.py           # Reusable UI components + PDF export
│
├── services/                   # Business logic services
│   ├── ticker_resolver.py      # 80+ NSE ticker mappings + peer lookup
│   ├── portfolio_service.py    # HHI diversification + risk scoring
│   └── market_brief_service.py # NIFTY/SENSEX fetcher + brief generator
│
├── tests/                      # pytest test suite
│   ├── conftest.py             # Shared fixtures + in-memory SQLite
│   ├── test_agents.py          # Agent unit tests
│   ├── test_api.py             # FastAPI endpoint integration tests
│   └── test_graph.py           # LangGraph workflow tests
│
├── logs/                       # Log output directory
├── app.py                      # FastAPI entry point (uvicorn)
├── logging_config.py           # Loguru structured logging
├── requirements.txt            # All pinned dependencies
├── .env.example                # Environment variable template
└── README.md                   # This file
```

---


### POST `/analyze`

Run full 6-agent parallel analysis for a single stock.

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "TCS"}'
```


```bash
curl -X POST http://localhost:8000/api/v1/portfolio/analyze \
  -H "Content-Type: application/json" \
  -d '{"stocks": ["TCS", "RELIANCE", "HDFCBANK", "SUNPHARMA", "ITC"]}'
```

```json
{
  "stocks": ["TCS", "RELIANCE", "HDFCBANK", "SUNPHARMA", "ITC"],
  "sector_allocation": {"Information Technology": 20.0, "Energy": 20.0, "...": "..."},
  "diversification_score": 72.5,
  "risk_score": 41.0,
  "concentration_risk": "Low",
  "suggestions": ["Portfolio appears reasonably balanced..."],
  "created_at": "2025-01-15T10:30:00Z"
}
```

### GET `/market-brief`

Daily Indian market brief — cached once per calendar day.

```bash
curl http://localhost:8000/api/v1/market-brief
```

### GET `/history`

List recent analysis requests.

```bash
curl "http://localhost:8000/api/v1/history?limit=10"
```

### GET `/history/{ticker}`

History for a specific ticker.

```bash
curl http://localhost:8000/api/v1/history/TCS
```

### GET `/report/{request_id}`

Retrieve a previously generated report.

```bash
curl http://localhost:8000/api/v1/report/1
```

---

## 🎯 Supported Tickers

The platform supports all major NSE-listed stocks. Common examples:

| Sector | Tickers |
|---|---|
| IT | TCS, INFY, HCLTECH, WIPRO, TECHM |
| Banking | HDFCBANK, ICICIBANK, AXISBANK, SBIN, KOTAKBANK |
| Energy | RELIANCE, ONGC, BPCL, ADANIENT, TATAPOWER |
| Consumer | HINDUNILVR, ITC, NESTLEIND, BRITANNIA, DABUR |
| Auto | TATAMOTORS, MARUTI, M&M, BAJAJAUTO, EICHERMOT |
| Pharma | SUNPHARMA, DRREDDY, CIPLA, DIVISLAB, LUPIN |
| Metals | TATASTEEL, JSWSTEEL, HINDALCO, SAIL, VEDL |
| New-Age | ZOMATO, NYKAA, PAYTM, IRCTC, DELHIVERY |

Any NSE ticker not in this list is also supported — just enter the symbol and it appends `.NS` automatically.

---

## 🤖 Agent Details

### News Agent
- Fetches up to 20 recent headlines via Google News RSS
- Sends headlines to Gemini for structured JSON classification
- Outputs bullish/bearish catalysts and overall news impact
- Keyword-based fallback if Gemini is unavailable

### Financial Agent
- Fetches 15 key metrics via yfinance (P/E, ROE, margins, FCF, beta, etc.)
- Scores financial health across 5 dimensions (profitability, ROE, debt, FCF, growth)
- Compares P/E against sector benchmarks (IT: 28x, Banking: 20x, FMCG: 45x, etc.)
- No Gemini call needed — pure rule-based evaluation

### Sentiment Agent
- Runs FinBERT (ProsusAI/finbert) over all news headlines
- Returns composite sentiment score from -1.0 (bearish) to +1.0 (bullish)
- Reuses headlines from the News Agent to avoid duplicate RSS calls
- Keyword-based fallback if FinBERT model fails to load

### Technical Agent
- Fetches 1-year daily OHLCV data from yfinance
- Computes RSI(14), MACD(12,26,9), SMA(50/200), EMA(20/50), Bollinger Bands(20,2)
- Counts bullish vs bearish signal confluence across all indicators
- Determines trend: Uptrend / Sideways / Downtrend

### Sector Agent
- Identifies sector from yfinance info
- Looks up 4 known sector peers from the built-in peer map
- Fetches peer metrics and computes sector averages
- Calls Gemini to classify relative position: Leader / Average / Laggard

### Corporate Actions Agent
- Parses dividends (last 12 months, YoY growth check)
- Parses stock splits (2-year window)
- Fetches upcoming earnings calendar
- Infers buyback signals from float vs shares outstanding ratio
- Flags elevated short interest (>5% of float)

### Report Agent
- Aggregates all 6 agent outputs into a structured Gemini prompt
- Generates a full Markdown research report (~1,500 words)
- Extracts recommendation, confidence score, executive summary via regex
- Full offline fallback builds the report from raw agent data if Gemini fails

---

## ⚙️ Configuration

All configuration is via environment variables in `.env`:

```env
# Required
GEMINI_API_KEY=your_key_here

# Optional — defaults shown
GEMINI_MODEL=gemini-1.5-flash
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=sqlite+aiosqlite:///./stock_platform.db
BACKEND_URL=http://localhost:8000
FINBERT_MODEL=ProsusAI/finbert
```

---

## 🗄️ Database Schema

SQLite database (`stock_platform.db`) with 4 tables:

| Table | Purpose |
|---|---|
| `analysis_requests` | Every incoming request with status, duration, errors |
| `analysis_reports` | Full report markdown + all agent outputs as JSON |
| `portfolio_analyses` | Portfolio intelligence results |
| `market_briefs` | Daily market briefs (one per calendar day) |

---

## 📊 Logging

Structured logging via **loguru**:

- **Development** (`APP_ENV=development`): coloured console output
- **Production** (`APP_ENV=production`): JSON to console + rotating file (`logs/app.log`)

Log levels per module are tagged with agent name for easy filtering:

```
[Graph:NewsNode]      → news agent execution
[Graph:ReportNode]    → report generation
[API /analyze]        → endpoint request/response
[SectorAgent]         → sector analysis steps
```

---

## 🔧 Troubleshooting

**FinBERT download is slow on first run**

FinBERT (~440 MB) downloads from HuggingFace on first use. Subsequent runs use the local cache (`~/.cache/huggingface`). The keyword fallback activates automatically if the download fails.

**yfinance returns empty data**

Some tickers may return empty data during market hours due to rate limiting. The platform retries 3 times with exponential backoff. If data is still unavailable, the agent returns a neutral/unknown output and the report continues with available data.

**Gemini rate limit errors**

The free tier allows 15 requests/minute. On `/compare`, two analyses run in parallel followed by a comparison call — this uses 3 Gemini calls in quick succession. If you hit rate limits, wait 60 seconds and retry.

**Backend connection refused in Streamlit**

Make sure the FastAPI backend is running before opening Streamlit:
```bash
# Terminal 1
python app.py

# Terminal 2
streamlit run frontend/app.py
```

**`ModuleNotFoundError` on startup**

Ensure you activated the virtual environment:
```bash
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\Activate.ps1  # Windows
```

---

## 📝 Disclaimer

This platform is for **informational and educational purposes only**. It does not constitute financial advice. Always conduct your own research and consult a qualified financial advisor before making investment decisions. Past performance is not indicative of future results.

---

## 🧱 Built With

- [Google Gemini](https://aistudio.google.com/) — LLM for report generation
- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent orchestration
- [FinBERT](https://huggingface.co/ProsusAI/finbert) — Financial sentiment analysis
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [pandas-ta](https://github.com/twopirllc/pandas-ta) — Technical indicators
- [FastAPI](https://fastapi.tiangolo.com/) — Backend API
- [Streamlit](https://streamlit.io/) — Frontend UI
- [SQLAlchemy](https://www.sqlalchemy.org/) — Database ORM
- [fpdf2](https://py-fpdf2.readthedocs.io/) — PDF generation