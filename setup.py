"""
setup.py — enables `pip install -e .` for local development.
Most configuration lives in requirements.txt; this is a minimal shim.
"""

from setuptools import setup, find_packages

setup(
    name="indian-stock-platform",
    version="1.0.0",
    description="Multi-Agent Indian Stock Research & Portfolio Intelligence Platform",
    packages=find_packages(exclude=["tests*", "logs*"]),
    python_requires=">=3.10",
    install_requires=[
        # Core deps — full list in requirements.txt
        "fastapi",
        "uvicorn[standard]",
        "streamlit",
        "langgraph",
        "google-genai",
        "yfinance",
        "pandas",
        "pandas-ta",
        "transformers",
        "sqlalchemy",
        "aiosqlite",
        "pydantic>=2.0",
        "python-dotenv",
        "loguru",
        "httpx",
        "feedparser",
        "fpdf2",
        "plotly",
        "tenacity",
    ],
    entry_points={
        "console_scripts": [
            "stock-platform=app:main",
        ],
    },
)