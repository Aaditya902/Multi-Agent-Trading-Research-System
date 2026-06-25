"""
Gemini prompt for the News Agent — summarises raw headlines into structured output.
"""


def build_news_summary_prompt(ticker: str, company_name: str, headlines: list[str]) -> str:
    headlines_str = "\n".join(f"- {h}" for h in headlines) if headlines else "- No recent headlines found."
    return f"""You are a financial news analyst specialising in Indian equity markets.

Analyse the following recent news headlines for {company_name} ({ticker}) and provide a structured analysis.

HEADLINES:
{headlines_str}

Respond in this EXACT JSON format (no markdown, no preamble):
{{
  "news_summary": "<2-3 sentence summary of the most important recent developments>",
  "bullish_news": ["<bullish catalyst 1>", "<bullish catalyst 2>"],
  "bearish_news": ["<bearish catalyst 1>", "<bearish catalyst 2>"],
  "overall_news_impact": "<Positive | Negative | Neutral>"
}}

Rules:
- bullish_news and bearish_news should each have 0-5 specific points
- Be factual and specific to the headlines provided
- If no headlines are relevant, set overall_news_impact to "Neutral"
- Return ONLY valid JSON
"""