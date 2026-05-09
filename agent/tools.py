"""
External tool calls. These are the non-LLM steps in the chain.

Tools used:
  - yfinance  : fetches real-time stock fundamentals and price history
  - duckduckgo_search : fetches recent news without requiring an API key
"""

import yfinance as yf
from ddgs import DDGS


# 
# Tool 1  Stock data via yfinance
# 

def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch comprehensive stock fundamentals and recent price history.

    Returns a dict with keys:
        success (bool), data (dict), error (str | None)
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # yfinance sometimes returns an empty dict for bad tickers
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            # Last-ditch: try fast_info
            fi = stock.fast_info
            current_price = getattr(fi, "last_price", None)
        else:
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        hist = stock.history(period="1mo")

        price_30d_change = None
        price_history = []
        if not hist.empty:
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            price_30d_change = round(((end_price - start_price) / start_price) * 100, 2)
            price_history = [
                {"date": str(idx.date()), "close": round(row["Close"], 2)}
                for idx, row in hist.tail(10).iterrows()
            ]

        biz = info.get("longBusinessSummary", "N/A")
        data = {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "current_price": current_price,
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margins": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "roe": info.get("returnOnEquity"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "analyst_recommendation": info.get("recommendationKey", "N/A"),
            "target_price": info.get("targetMeanPrice"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "business_summary": (biz[:600] if biz and biz != "N/A" else "N/A"),
            "price_30d_change": price_30d_change,
            "price_history": price_history,
        }

        # Guard against non-existent tickers: yfinance sometimes returns
        # an empty dict without throwing an exception.
        if not info or (current_price is None and not price_history):
            return {
                "success": False,
                "data": data,
                "error": f"Ticker '{ticker}' not found or has no price data.",
            }

        return {"success": True, "data": data, "error": None}

    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}


# 
# Tool 2  Recent financial news via DuckDuckGo (no API key needed)
# 

def fetch_financial_news(company_name: str, ticker: str, max_results: int = 8) -> dict:
    """
    Search DuckDuckGo for recent news about the company.

    Returns a dict with keys:
        success (bool), articles (list[dict]), error (str | None)
    """
    articles = []
    queries = [
        f"{company_name} stock news 2025",
        f"{ticker} earnings results outlook 2025",
    ]
    try:
        with DDGS() as ddgs:
            for query in queries:
                results = list(ddgs.text(query, max_results=max_results // 2 + 1))
                for r in results:
                    articles.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", "")[:350],
                        "url": r.get("href", ""),
                        "source": r.get("source", ""),
                    })

        # Deduplicate by title
        seen, unique = set(), []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)

        return {"success": True, "articles": unique[:max_results], "error": None}

    except Exception as e:
        return {"success": False, "articles": [], "error": str(e)}
