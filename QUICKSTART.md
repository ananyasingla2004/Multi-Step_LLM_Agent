# Quick Start

Get the Finance Research Agent running in 3 minutes.

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `openai` - LLM API client
- `yfinance` - Stock data
- `ddgs` - News search

## 2. Set Your API Key

### Option A: OpenAI (Recommended)
```bash
export OPENAI_API_KEY="sk-your_key_here"
```

Get your key: https://platform.openai.com/api-keys

### Option B: Grok (xAI)
```bash
export OPENAI_API_KEY="grok_your_key_here"
export OPENAI_BASE_URL="https://api.x.ai/v1"
```

Get your key: https://console.x.ai/

### Option C: Using .env file
```bash
cp .env.example .env
# Edit .env with your credentials
source .env
```

## 3. Run a Query

```bash
# Command-line mode
python main.py "Should I invest in Apple?"

# Interactive mode
python main.py
```

## Example Output

The agent generates two files in `output/`:

1. **report.md** — Professional investment research report
2. **state.json** — Full chain state (for debugging)

## Try These Queries

- `"Analyse TCS for value investing"` - Indian stock
- `"Should I invest in AAPL for long-term growth?"` - US stock
- `"Is Reliance a good dividend stock?"` - Dividend analysis
- `"What is the risk profile of Tesla?"` - Risk-focused

## Troubleshooting

**API Key Error?**
```bash
echo $OPENAI_API_KEY  # Check if set
export OPENAI_API_KEY="your_key"  # Set it
python main.py "test query"
```

**Ticker Not Found?**
- Verify ticker on Yahoo Finance: https://finance.yahoo.com
- Use correct format: AAPL (US) or TCS.NS (India NSE)

**Rate Limit Error?**
- Free tiers have request limits
- Wait a few minutes and retry
- Consider upgrading to a paid plan

---

For full documentation, see [README.md](README.md)
