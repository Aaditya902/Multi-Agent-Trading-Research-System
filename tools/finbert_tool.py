"""
FinBERT sentiment analyser.
Loads the ProsusAI/finbert model once and reuses it for all requests.
Falls back to a simple keyword scorer if the model fails to load.
"""

from __future__ import annotations
import os
from functools import lru_cache

from logging_config import logger

_MODEL_NAME = os.getenv("FINBERT_MODEL", "ProsusAI/finbert")


@lru_cache(maxsize=1)
def _load_pipeline():
    """Load and cache the FinBERT sentiment pipeline."""
    try:
        from transformers import pipeline as hf_pipeline
        logger.info(f"Loading FinBERT model: {_MODEL_NAME} …")
        pipe = hf_pipeline(
            "text-classification",
            model=_MODEL_NAME,
            tokenizer=_MODEL_NAME,
            top_k=None,           # return all class scores
            truncation=True,
            max_length=512,
            device=-1,            # CPU; set to 0 for GPU
        )
        logger.info("FinBERT loaded successfully.")
        return pipe
    except Exception as e:
        logger.error(f"FinBERT load failed: {e} — falling back to keyword scorer")
        return None


def analyse_sentiment(texts: list[str]) -> dict:
    """
    Run FinBERT on a list of texts (headlines / summaries).
    Returns aggregated sentiment with scores.

    Output schema:
        {
            "sentiment": "Bullish" | "Neutral" | "Bearish",
            "score": float (-1.0 to 1.0),
            "positive_score": float,
            "negative_score": float,
            "neutral_score": float,
            "explanation": str,
        }
    """
    if not texts:
        return _neutral_result("No text provided for sentiment analysis.")

    pipe = _load_pipeline()
    if pipe is None:
        return _keyword_fallback(texts)

    try:
        pos_total = neg_total = neu_total = 0.0
        count = 0

        for text in texts[:30]:  # cap to avoid timeout
            if not text.strip():
                continue
            try:
                results = pipe(text[:512])
                # results is a list of [{label, score}]
                scores = {r["label"].lower(): r["score"] for r in results[0]}
                pos_total += scores.get("positive", 0.0)
                neg_total += scores.get("negative", 0.0)
                neu_total += scores.get("neutral", 0.0)
                count += 1
            except Exception as inner:
                logger.debug(f"FinBERT skipped one text: {inner}")

        if count == 0:
            return _neutral_result("FinBERT could not process any texts.")

        pos_avg = pos_total / count
        neg_avg = neg_total / count
        neu_avg = neu_total / count

        # Composite score: +1 = max bullish, -1 = max bearish
        composite = pos_avg - neg_avg

        if composite > 0.1:
            sentiment = "Bullish"
        elif composite < -0.1:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        return {
            "sentiment": sentiment,
            "score": round(composite, 4),
            "positive_score": round(pos_avg, 4),
            "negative_score": round(neg_avg, 4),
            "neutral_score": round(neu_avg, 4),
            "explanation": (
                f"FinBERT analysed {count} text segments. "
                f"Average positive={pos_avg:.2%}, negative={neg_avg:.2%}, neutral={neu_avg:.2%}. "
                f"Composite score={composite:+.3f} → {sentiment}."
            ),
        }

    except Exception as e:
        logger.error(f"FinBERT inference failed: {e}")
        return _keyword_fallback(texts)


def _neutral_result(explanation: str) -> dict:
    return {
        "sentiment": "Neutral",
        "score": 0.0,
        "positive_score": 0.0,
        "negative_score": 0.0,
        "neutral_score": 1.0,
        "explanation": explanation,
    }


def _keyword_fallback(texts: list[str]) -> dict:
    """
    Simple keyword-based fallback when FinBERT is unavailable.
    Not production-grade but prevents hard failures.
    """
    positive_words = {
        "profit", "growth", "surge", "rally", "beat", "strong", "record",
        "upgrade", "buy", "outperform", "dividend", "gain", "rise", "bullish",
        "breakout", "recovery", "robust", "expand", "revenue", "order",
    }
    negative_words = {
        "loss", "decline", "fall", "miss", "weak", "downgrade", "sell",
        "underperform", "cut", "bearish", "risk", "concern", "slump", "debt",
        "fraud", "penalty", "fine", "lawsuit", "delay", "warning",
    }

    pos_count = neg_count = 0
    for text in texts:
        words = text.lower().split()
        pos_count += sum(1 for w in words if w in positive_words)
        neg_count += sum(1 for w in words if w in negative_words)

    total = pos_count + neg_count or 1
    composite = (pos_count - neg_count) / total

    if composite > 0.1:
        sentiment = "Bullish"
    elif composite < -0.1:
        sentiment = "Bearish"
    else:
        sentiment = "Neutral"

    return {
        "sentiment": sentiment,
        "score": round(composite, 4),
        "positive_score": round(pos_count / total, 4),
        "negative_score": round(neg_count / total, 4),
        "neutral_score": 0.0,
        "explanation": (
            f"[Keyword fallback — FinBERT unavailable] "
            f"Positive signals: {pos_count}, Negative signals: {neg_count}. "
            f"Sentiment: {sentiment}."
        ),
    }