# Finance Research Agent

An intelligent multi-step LLM chain that automates equity research. Given a natural-language investment query, it produces a professional investment research report complete with financial health scores, sentiment analysis, risk assessment, and buy/hold/sell verdicts.

## What It Does

This agent orchestrates a **7-step chain** combining LLM reasoning with live financial data:

1. **Parse Query** (LLM) — Extract ticker, company name, analysis type, time horizon, and confidence from user intent
2. **Fetch Stock Data** (Tool) — Retrieve live fundamentals from Yahoo Finance (price, P/E, market cap, ROE, debt ratios, etc.)
3. **Analyze Financials** (LLM) — Score valuation, financial health, and growth (1–10 scale) based on fundamentals
4. **Fetch News** (Tool) — Search DuckDuckGo for recent articles about the company
5. **Analyze Sentiment** (LLM) — Assess market sentiment from news (bullish to bearish, -5 to +5 score)
6. **Assess Risk** (LLM) — Synthesize financial + sentiment data into a risk profile and investor suitability rating
7. **Generate Report** (LLM) — Compose a professional markdown report with executive summary, verdict, and disclaimer

Each step reads from and writes to a shared state, ensuring information flows through the chain without context loss.

## Key Features

- **7 well-structured steps** — Chaining logic is explicit in separate functions, not monolithic
- **Live financial data** — Integrates yfinance for current stock metrics and DuckDuckGo for recent news
- **Multiple LLM calls** — 5 strategic LLM calls per query for parse, analyze, risk, and generate tasks
- **Retry logic** — Automatic exponential backoff for transient API failures
- **Graceful fallback** — Switches to a smaller model if primary model hits quota
- **No API keys for tools** — yfinance and DuckDuckGo require no authentication
- **Supports US & Indian tickers** — Handles standard symbols (AAPL, TSLA) and NSE tickers (TCS.NS, RELIANCE.NS)

## Prerequisites

- **Python 3.8+**
- **API Key** — One of:
  - [OpenAI API key](https://platform.openai.com/api-keys) (requires paid account or credits)
  - [Grok API key](https://console.x.ai/) from xAI (free tier available)
  - Any OpenAI-compatible API endpoint

## Installation

### 1. Clone or Download

```bash
# If using GitHub:
git clone <your-repo-url>
cd finance_agent

# Or unzip the provided .zip file
unzip finance_agent.zip
cd finance_agent
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `openai>=1.3.0` — LLM API client
- `yfinance>=0.2.40` — Stock data fetcher
- `ddgs` — DuckDuckGo search client

## Configuration

Set your API credentials as environment variables:

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
python main.py "Should I invest in Apple?"
```

### Grok (xAI)
```bash
export OPENAI_API_KEY="grok_..."  # Your xAI key
export OPENAI_BASE_URL="https://api.x.ai/v1"
python main.py "Should I invest in Apple?"
```

### Other Compatible APIs
```bash
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="https://your-api-endpoint/v1"
python main.py "Should I invest in Apple?"
```

## Usage

### Command-Line with Argument

```bash
python main.py "Should I invest in TCS for value investing?"
python main.py "Analyze Apple (AAPL) for long-term growth"
python main.py "Is Reliance Industries a good buy right now?"
```

### Interactive Mode

```bash
python main.py
# Prompts: "Enter your query:" → type your question → press Enter
```

### Example Queries

- `"Analyse TCS for value investing"` → Analyzes Tata Consultancy Services (NSE ticker: TCS.NS)
- `"Should I invest in Apple (AAPL) for long-term growth?"` → Analyzes Apple Inc. (US ticker: AAPL)
- `"What is the risk profile of Tesla stock?"` → Risk-focused analysis
- `"Is Wipro a good dividend play?"` → Dividend income analysis

## Input Expectations

### Query Format

Provide a natural-language investment question. The agent accepts:

- **Company name only** → Auto-detects US ticker (e.g., "Apple" → AAPL)
- **Explicit ticker** → Any stock exchange symbol (e.g., "AAPL", "TCS.NS")
- **Analysis type** → Optional keywords like "value investing", "growth", "dividend", "risk"
- **Time horizon** → Optional: "short-term", "medium-term", "long-term"

### Examples

✅ **Good queries:**
- "Should I invest in Apple for long-term growth?"
- "Analyse TCS (Tata Consultancy Services) for value investing"
- "Is Reliance a good dividend stock?"
- "AAPL value analysis"
- "What is the risk of Tesla?"

❌ **Poor queries:**
- "stocks" (ambiguous)
- "Is the market going up?" (not stock-specific)
- "Imagine a company..." (hypothetical, not real)

## Output

### Report Structure

Each run generates **two files** in the `output/` directory:

1. **Markdown Report** (`{TICKER}_{TIMESTAMP}_report.md`)
   - Professional 7-section equity research report
   - Executive summary, company overview, financial assessment, sentiment, risk, verdict, disclaimer
   - Human-readable format, suitable for sharing

2. **State JSON** (`{TICKER}_{TIMESTAMP}_state.json`)
   - Full chain state with all intermediate outputs
   - Useful for debugging and audit trails

### Example Report Structure

```
# Investment Research Report — [Company Name]
*Generated: [Date]*

## 1. Executive Summary
[Ticker, current price, verdict, thesis]

## 2. Company Overview
[Business description, sector, importance]

## 3. Financial Health Assessment
[Scores, valuation, balance sheet analysis]

## 4. Market Sentiment & Recent News
[News summary, catalysts, risks]

## 5. Risk Assessment
[Risk level, market risk, company-specific risk, suitability]

## 6. Investment Verdict
[BUY / HOLD / SELL with 3–5 sentence rationale]

## 7. Disclaimer
[Standard financial disclaimer]

---
## Agent Chain Log
[Table of all 7 steps with inputs and outputs]
```

## Architecture

### Chain Design

```
User Query
    ↓
Step 1: Parse Query (LLM)
    ↓
Step 2: Fetch Stock Data (yfinance Tool)
    ├→ Step 3: Analyze Financials (LLM)
    ↓
Step 4: Fetch News (DuckDuckGo Tool)
    ↓
Step 5: Analyze Sentiment (LLM)
    ├→ Step 6: Assess Risk (LLM)
    ↓
Step 7: Generate Report (LLM)
    ↓
Output: Markdown Report + State JSON
```

### Code Structure

```
finance_agent/
├── main.py                    # Entry point, state management, output writers
├── agent/
│   ├── __init__.py
│   ├── llm.py                 # OpenAI API wrapper, retry logic, fallback models
│   ├── steps.py               # 7 step functions (each ~50–100 lines)
│   └── tools.py               # yfinance & DuckDuckGo integrations
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

Each step function is **independent and testable** — not a monolithic function.

## Limitations & Known Issues

### Rate Limiting

Free-tier OpenAI/Grok APIs have per-minute and daily quotas. Each query makes **5 LLM calls**, so:
- **OpenAI Free**: Limited queries per day
- **Grok Free Tier**: 5 requests/minute; ~3 full runs per hour

**Mitigation**: 
- Use a paid tier for production
- Cache results locally for repeated queries (future enhancement)
- Run queries sequentially to respect rate limits

### Ticker Validation

`yfinance` silently returns empty data for invalid tickers. The agent now includes a validation guard:
- If `yfinance` returns no data, the chain aborts early
- User is prompted to verify the ticker symbol

### Data Freshness

Stock data and news are fetched live, but may lag by a few minutes depending on exchange hours and search engine indexing.

### Non-English Content

News articles are parsed as-is. For non-English markets, the LLM may struggle with untranslated content.

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

```bash
# Make sure to set your API key before running:
export OPENAI_API_KEY="your_key_here"
python main.py "your query"
```

### "Ticker not found" / Stock data fetch failed

```bash
# Use the correct ticker symbol:
# US stocks: AAPL, MSFT, TSLA, GOOGL
# Indian NSE stocks: TCS.NS, RELIANCE.NS, WIPRO.NS, INFY.NS
# Verify on Yahoo Finance: https://finance.yahoo.com
```

### Rate limit errors

```bash
# Wait a few minutes or use a higher-tier API plan
# For Grok: Max 5 requests/min on free tier
# For OpenAI: Depends on your plan (usually ample for development)
```

### "Could not extract JSON from LLM response"

Rare edge case. The LLM may have hallucinated non-JSON text. Try again or use a different query.

## Example Run

```bash
$ export OPENAI_API_KEY="sk-..."
$ python main.py "Analyse TCS for value investing"

==============================================================
  FINANCE RESEARCH AGENT    OpenAI GPT-4 Turbo
==============================================================
  Query: Analyse TCS for value investing
==============================================================

[Step 1 / LLM] Parsing user query...
   Tata Consultancy Services Limited (TCS.NS) | focus=value | horizon=long-term

[Step 2 / Tool – yfinance] Fetching stock data...
   Tata Consultancy Services Limited  Price=INR 2427.3  30d=-1.88%

[Step 3 / LLM] Analysing financial fundamentals...
   Overall financial score : 5/10 | Valuation=8 Health=3 Growth=6

[Step 4 / Tool – DuckDuckGo] Fetching recent news...
   8 articles fetched

[Step 5 / LLM] Analysing news sentiment...
   Sentiment : bullish score=4 confidence=high

[Step 6 / LLM] Assessing investment risk...
   Risk level : high score=7/10 suitable_for=aggressive growth

[Step 7 / LLM] Generating final investment research report...
   Report generated

==============================================================
  FINAL REPORT
==============================================================
[Full markdown report printed to terminal]

==============================================================
  Outputs saved:
    Markdown report : output/TCS_NS_20260505_191637_report.md
    Full state JSON : output/TCS_NS_20260505_191637_state.json
==============================================================
```

## Contributing

Ideas for improvement (see `report.tex` for detailed reflection):
- Add LRU cache for repeated ticker queries
- Parallelize Steps 3 & 4 (financial analysis & news fetch)
- Build a web UI (Streamlit/Gradio)
- Robust local ticker validation
- Structured logging for error diagnosis

## License

MIT (or as specified in your project)

## Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Verify your API key is set and valid
3. Ensure the ticker symbol is correct (check Yahoo Finance)
4. Review output JSON for intermediate step results

---

**Happy investing!** 🚀

*This agent is for educational and informational purposes only. It does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.*
# Multi-Step_LLM_Agent
