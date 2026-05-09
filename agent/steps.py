"""
The seven steps of the Finance Research Agent chain.

Dependency graph:
    Step 1 (LLM)   parsed_query
    Step 2 (Tool)  stock_data          [uses: parsed_query]
    Step 3 (LLM)   financial_analysis  [uses: stock_data, parsed_query]
    Step 4 (Tool)  news_data           [uses: parsed_query]
    Step 5 (LLM)   sentiment_analysis  [uses: news_data, stock_data]
    Step 6 (LLM)   risk_assessment     [uses: financial_analysis, sentiment_analysis, stock_data]
    Step 7 (LLM)   final_report        [uses: ALL previous state]

Every step reads from `state` and writes its output back to `state`.
"""

import json
from datetime import datetime
from agent.llm import call_llm, extract_json
from agent.tools import fetch_stock_data, fetch_financial_news


# 
# STEP 1  LLM: Parse user query into structured intent
# 

_S1_SYSTEM = """You are a financial query parser. Extract structured information from the user's investment research request.

Respond ONLY with a valid JSON object  no markdown, no explanation, no preamble:
{
  "ticker": "exchange ticker symbol (e.g. AAPL, TSLA, RELIANCE.NS, TCS.NS, INFY.NS)",
  "company_name": "full official company name",
  "analysis_type": "one of: growth | value | dividend | risk | general",
  "user_focus": "what the user specifically wants to know, 1-2 sentences",
  "time_horizon": "one of: short-term | medium-term | long-term",
  "confidence": "how confident you are in the ticker: high | medium | low"
}

Rules:
- Indian NSE stocks  append .NS (e.g. RELIANCE.NS, TCS.NS, HDFC.NS, WIPRO.NS)
- US stocks  standard ticker (AAPL, MSFT, GOOGL, AMZN)
- If ticker is truly unclear, make your best guess and set confidence to low."""


def step1_parse_query(model, state: dict) -> dict:
    """Step 1 (LLM): Parse the user's natural-language query into structured intent."""
    print("\n[Step 1 / LLM] Parsing user query...")

    user_prompt = f"Parse this investment research request:\n\n{state['user_query']}"
    raw = call_llm(model, _S1_SYSTEM, user_prompt)
    parsed = extract_json(raw)

    state["parsed_query"] = parsed
    _log(state, 1, "Query Parsing", "LLM", state["user_query"],
         f"Ticker={parsed.get('ticker')}  Company={parsed.get('company_name')}")

    print(f"   {parsed.get('company_name')} ({parsed.get('ticker')})  "
          f"| focus={parsed.get('analysis_type')}  horizon={parsed.get('time_horizon')}")
    return state


# 
# STEP 2  Tool: Fetch live stock data via yfinance
# 

def step2_fetch_stock_data(state: dict) -> dict:
    """Step 2 (Tool  yfinance): Fetch real financial data. LLM cannot produce this."""
    print("\n[Step 2 / Tool  yfinance] Fetching stock data...")

    ticker = state["parsed_query"].get("ticker", "").strip()
    if not ticker:
        state["errors"].append("Step 2: No ticker identified in Step 1.")
        state["stock_data"] = {"success": False, "data": {}, "error": "No ticker"}
        _log(state, 2, "Stock Data Fetch", "Tool  yfinance", ticker, "FAILED: no ticker")
        return state

    result = fetch_stock_data(ticker)
    state["stock_data"] = result

    if result["success"]:
        d = result["data"]
        print(f"   {d.get('company_name')}  "
              f"Price={d.get('currency')} {d.get('current_price')}  "
              f"30d={d.get('price_30d_change')}%")
        _log(state, 2, "Stock Data Fetch", "Tool  yfinance", ticker,
             f"Price={d.get('current_price')}  P/E={d.get('pe_ratio')}")
    else:
        state["errors"].append(f"Step 2 tool error: {result['error']}")
        print(f"   Tool call failed: {result['error']}  chain continues with partial data.")
        _log(state, 2, "Stock Data Fetch", "Tool  yfinance", ticker,
             f"FAILED: {result['error']}")

    return state


# 
# STEP 3  LLM: Analyse financial fundamentals
# 

_S3_SYSTEM = """You are a senior buy-side financial analyst. Analyse the provided stock fundamentals and produce a structured financial health assessment.

Respond ONLY with a valid JSON object:
{
  "valuation_score": <int 1-10>,
  "valuation_summary": "<2-3 sentences>",
  "financial_health_score": <int 1-10>,
  "financial_health_summary": "<2-3 sentences>",
  "growth_score": <int 1-10>,
  "growth_summary": "<2-3 sentences>",
  "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "key_concerns": ["<concern 1>", "<concern 2>", "<concern 3>"],
  "peer_context": "<1-2 sentences comparing to typical industry benchmarks>",
  "overall_financial_score": <int 1-10>
}

Scoring guide: 10 = outstanding, 7-9 = strong, 4-6 = average, 1-3 = weak.
Be specific  mention actual numbers from the data."""


def step3_analyze_financials(model, state: dict) -> dict:
    """Step 3 (LLM): Analyse fundamentals from Step 2 stock data."""
    print("\n[Step 3 / LLM] Analysing financial fundamentals...")

    d = state["stock_data"].get("data", {})
    p = state["parsed_query"]

    user_prompt = f"""Analyse these fundamentals for {p.get('company_name')} ({p.get('ticker')}):

Sector / Industry : {d.get('sector')} / {d.get('industry')}
Current Price     : {d.get('currency')} {d.get('current_price')}
Market Cap        : {d.get('market_cap')}
P/E (trailing)    : {d.get('pe_ratio')}   |  Forward P/E : {d.get('forward_pe')}
EPS               : {d.get('eps')}
Revenue           : {d.get('revenue')}   |  Growth : {d.get('revenue_growth')}
Profit Margin     : {d.get('profit_margins')}
Debt / Equity     : {d.get('debt_to_equity')}   |  Current Ratio : {d.get('current_ratio')}
ROE               : {d.get('roe')}
52-wk High/Low    : {d.get('52_week_high')} / {d.get('52_week_low')}
30-day chg        : {d.get('price_30d_change')}%
Analyst target    : {d.get('target_price')}   |  Recommendation : {d.get('analyst_recommendation')}

Business summary  : {d.get('business_summary')}

User's focus      : {p.get('user_focus')}
Analysis type     : {p.get('analysis_type')}
Time horizon      : {p.get('time_horizon')}"""

    raw = call_llm(model, _S3_SYSTEM, user_prompt)
    analysis = extract_json(raw)

    state["financial_analysis"] = analysis
    _log(state, 3, "Financial Analysis", "LLM",
         f"Stock metrics for {p.get('ticker')}",
         f"Overall score={analysis.get('overall_financial_score')}/10")

    print(f"   Overall financial score : {analysis.get('overall_financial_score')}/10  "
          f"| Valuation={analysis.get('valuation_score')}  "
          f"Health={analysis.get('financial_health_score')}  "
          f"Growth={analysis.get('growth_score')}")
    return state


# 
# STEP 4  Tool: Fetch recent news via DuckDuckGo
# 

def step4_fetch_news(state: dict) -> dict:
    """Step 4 (Tool  DuckDuckGo): Fetch recent news. No API key required."""
    print("\n[Step 4 / Tool  DuckDuckGo] Fetching recent news...")

    company = state["parsed_query"].get("company_name", "")
    ticker  = state["parsed_query"].get("ticker", "")

    result = fetch_financial_news(company, ticker)
    state["news_data"] = result

    count = len(result.get("articles", []))
    if result["success"]:
        print(f"   {count} articles fetched")
        _log(state, 4, "News Fetch", "Tool  DuckDuckGo",
             f"{company} + {ticker}", f"{count} articles")
    else:
        state["errors"].append(f"Step 4 tool error: {result['error']}")
        print(f"   News fetch failed: {result['error']}  sentiment step will use fallback.")
        _log(state, 4, "News Fetch", "Tool  DuckDuckGo",
             f"{company} + {ticker}", f"FAILED: {result['error']}")

    return state


# 
# STEP 5  LLM: News sentiment analysis
# 

_S5_SYSTEM = """You are a financial news analyst specialising in market sentiment. Analyse the supplied news articles and produce a structured sentiment assessment.

Respond ONLY with a valid JSON object:
{
  "overall_sentiment": "very_bullish | bullish | neutral | bearish | very_bearish",
  "sentiment_score": <int -5 to +5>,
  "key_themes": ["<theme 1>", "<theme 2>", "<theme 3>"],
  "positive_catalysts": ["<catalyst 1>", "<catalyst 2>"],
  "negative_risks": ["<risk 1>", "<risk 2>"],
  "news_summary": "<2-3 sentence narrative>",
  "confidence": "high | medium | low"
}

Base confidence on news quantity and quality  fewer/vaguer articles  lower confidence."""


def step5_analyze_sentiment(model, state: dict) -> dict:
    """Step 5 (LLM): Analyse news from Step 4 combined with price context from Step 2."""
    print("\n[Step 5 / LLM] Analysing news sentiment...")

    articles = state["news_data"].get("articles", [])
    company  = state["parsed_query"].get("company_name", "")
    d        = state["stock_data"].get("data", {})

    if not articles:
        fallback = {
            "overall_sentiment": "neutral",
            "sentiment_score": 0,
            "key_themes": ["Insufficient news data"],
            "positive_catalysts": [],
            "negative_risks": ["News unavailable  treat with caution"],
            "news_summary": "No news articles could be retrieved. Sentiment defaulted to neutral.",
            "confidence": "low",
        }
        state["sentiment_analysis"] = fallback
        _log(state, 5, "Sentiment Analysis", "LLM", "No news (fallback)", "neutral / score=0")
        print("   No news available  using neutral fallback.")
        return state

    news_block = "\n\n".join(
        f"Title   : {a['title']}\nSnippet : {a['snippet']}"
        for a in articles[:6]
    )

    user_prompt = f"""Analyse sentiment from recent news about {company}:

{news_block}

---
Financial context:
- 30-day price change : {d.get('price_30d_change')}%
- Analyst consensus   : {d.get('analyst_recommendation')}"""

    raw = call_llm(model, _S5_SYSTEM, user_prompt)
    sentiment = extract_json(raw)

    state["sentiment_analysis"] = sentiment
    _log(state, 5, "Sentiment Analysis", "LLM",
         f"{len(articles)} articles",
         f"{sentiment.get('overall_sentiment')} / score={sentiment.get('sentiment_score')}")

    print(f"   Sentiment : {sentiment.get('overall_sentiment')}  "
          f"score={sentiment.get('sentiment_score')}  "
          f"confidence={sentiment.get('confidence')}")
    return state


# 
# STEP 6  LLM: Risk assessment (financial + sentiment synthesis)
# 

_S6_SYSTEM = """You are a risk analyst at a top-tier investment bank. Combine financial fundamentals AND news sentiment to produce a comprehensive risk assessment.

Respond ONLY with a valid JSON object:
{
  "risk_level": "very_low | low | moderate | high | very_high",
  "risk_score": <int 1-10>,
  "market_risk": "<1-2 sentences on macro/market risk>",
  "company_risk": "<1-2 sentences on company-specific risk>",
  "liquidity_risk": "<1 sentence on liquidity/tradability>",
  "key_risk_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "risk_mitigation": ["<mitigant 1>", "<mitigant 2>"],
  "suitable_for": "<investor profile: e.g. aggressive growth, conservative income, balanced>"
}

risk_score guide: 1-3 = low risk, 4-6 = moderate, 7-9 = high, 10 = extreme."""


def step6_assess_risk(model, state: dict) -> dict:
    """Step 6 (LLM): Risk assessment using outputs of Steps 3 and 5."""
    print("\n[Step 6 / LLM] Assessing investment risk...")

    fin  = state["financial_analysis"]
    sent = state["sentiment_analysis"]
    d    = state["stock_data"].get("data", {})
    p    = state["parsed_query"]

    user_prompt = f"""Assess investment risk for {p.get('company_name')} ({p.get('ticker')}):

=== FINANCIAL ANALYSIS (Step 3 output) ===
Overall score      : {fin.get('overall_financial_score')}/10
Valuation score    : {fin.get('valuation_score')}/10   {fin.get('valuation_summary')}
Health score       : {fin.get('financial_health_score')}/10   {fin.get('financial_health_summary')}
Growth score       : {fin.get('growth_score')}/10   {fin.get('growth_summary')}
Key concerns       : {json.dumps(fin.get('key_concerns', []))}
Debt/Equity        : {d.get('debt_to_equity')}
Current Ratio      : {d.get('current_ratio')}

=== SENTIMENT ANALYSIS (Step 5 output) ===
Overall sentiment  : {sent.get('overall_sentiment')}  score={sent.get('sentiment_score')}
Negative risks     : {json.dumps(sent.get('negative_risks', []))}
Key themes         : {json.dumps(sent.get('key_themes', []))}
Confidence         : {sent.get('confidence')}

=== MARKET DATA ===
52W range          : {d.get('52_week_low')}  {d.get('52_week_high')}
30-day change      : {d.get('price_30d_change')}%
Sector             : {d.get('sector')}

User time horizon  : {p.get('time_horizon')}"""

    raw = call_llm(model, _S6_SYSTEM, user_prompt)
    risk = extract_json(raw)

    state["risk_assessment"] = risk
    _log(state, 6, "Risk Assessment", "LLM",
         "Financial analysis + Sentiment analysis",
         f"{risk.get('risk_level')} / score={risk.get('risk_score')}/10")

    print(f"   Risk level : {risk.get('risk_level')}  "
          f"score={risk.get('risk_score')}/10  "
          f"suitable for={risk.get('suitable_for')}")
    return state


# 
# STEP 7  LLM: Synthesise into final investment research report
# 

_S7_SYSTEM = """You are a senior investment research analyst writing a formal equity research report.
Synthesise all the data into a professional, structured, actionable report.

Use this exact structure:

# [TICKER]  [Company Name] | Investment Research Report
*Date: {report_date}*

## 1. Executive Summary
3-4 sentences: ticker, current price, overall verdict, one-line investment thesis.

## 2. Company Overview
2-3 sentences on what the company does, sector, and why it matters.

## 3. Financial Health Assessment
Use the scored data. Be specific with numbers. Discuss valuation, balance sheet, profitability.

## 4. Market Sentiment & Recent News
Summarise news sentiment, key catalysts, and risks highlighted by recent coverage.

## 5. Risk Assessment
Name the risk level. Explain market, company-specific, and liquidity risks. State who this suits.

## 6. Investment Verdict
One clear verdict: BUY / HOLD / SELL.
State the rationale in 3-5 sentences. Reference price targets if available.

## 7. Disclaimer
Standard disclaimer: not financial advice, based on public data, do your own research.

---
Write in professional prose. Use actual numbers from the data. Do not hedge every sentence."""


def step7_generate_report(model, state: dict) -> dict:
    """Step 7 (LLM): Final synthesis  pulls from ALL prior state to produce the report."""
    print("\n[Step 7 / LLM] Generating final investment research report...")

    fin  = state["financial_analysis"]
    sent = state["sentiment_analysis"]
    risk = state["risk_assessment"]
    d    = state["stock_data"].get("data", {})
    p    = state["parsed_query"]

    user_prompt = f"""Generate a complete investment research report for {p.get('company_name')} ({p.get('ticker')}).

=== RAW DATA ===
Current price      : {d.get('currency')} {d.get('current_price')}
Market cap         : {d.get('market_cap')}
P/E  (trailing)    : {d.get('pe_ratio')}   Forward P/E : {d.get('forward_pe')}
Revenue growth     : {d.get('revenue_growth')}   Profit margin : {d.get('profit_margins')}
30-day change      : {d.get('price_30d_change')}%
Analyst target     : {d.get('target_price')}   Consensus : {d.get('analyst_recommendation')}
Business           : {d.get('business_summary')}

=== FINANCIAL ANALYSIS (Step 3) ===
Overall : {fin.get('overall_financial_score')}/10
Valuation {fin.get('valuation_score')}/10  {fin.get('valuation_summary')}
Health    {fin.get('financial_health_score')}/10  {fin.get('financial_health_summary')}
Growth    {fin.get('growth_score')}/10  {fin.get('growth_summary')}
Strengths : {json.dumps(fin.get('key_strengths', []))}
Concerns  : {json.dumps(fin.get('key_concerns', []))}

=== SENTIMENT (Step 5) ===
{sent.get('overall_sentiment')} (score {sent.get('sentiment_score')})  {sent.get('news_summary')}
Catalysts : {json.dumps(sent.get('positive_catalysts', []))}
Risks     : {json.dumps(sent.get('negative_risks', []))}

=== RISK (Step 6) ===
Level : {risk.get('risk_level')} ({risk.get('risk_score')}/10)
Market risk   : {risk.get('market_risk')}
Company risk  : {risk.get('company_risk')}
Key factors   : {json.dumps(risk.get('key_risk_factors', []))}
Suitable for  : {risk.get('suitable_for')}

=== USER REQUEST ===
"{state['user_query']}"
Time horizon : {p.get('time_horizon')}"""

    report_date = datetime.now().strftime("%B %d, %Y")
    system_prompt = _S7_SYSTEM.format(report_date=report_date)
    raw = call_llm(model, system_prompt, user_prompt)
    state["final_report"] = raw

    _log(state, 7, "Report Generation", "LLM",
         "All prior step outputs combined", "Full markdown report generated")

    print("   Report generated ")
    return state


# 
# Internal helper
# 

def _log(state: dict, step: int, name: str, step_type: str,
         input_summary: str, output_summary: str):
    state["step_log"].append({
        "step": step,
        "name": name,
        "type": step_type,
        "input_summary": str(input_summary)[:120],
        "output_summary": str(output_summary)[:120],
    })
