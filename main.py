"""
Finance Research Agent - main entry point.

Chain structure (7 steps, 5 LLM calls + 2 tool calls):

  Step 1  LLM   parse_query         parsed_query
  Step 2  Tool  fetch_stock_data    stock_data          (yfinance)
  Step 3  LLM   analyze_financials  financial_analysis  (uses steps 1+2)
  Step 4  Tool  fetch_news          news_data           (DuckDuckGo)
  Step 5  LLM   analyze_sentiment   sentiment_analysis  (uses steps 2+4)
  Step 6  LLM   assess_risk         risk_assessment     (uses steps 3+5)
  Step 7  LLM   generate_report     final_report        (uses ALL)

Requires: OPENAI_API_KEY environment variable (or compatible API key)
Works with: OpenAI, Grok, or any OpenAI-compatible API endpoint

Usage:
    python main.py "Should I invest in Apple for long-term growth?"
    python main.py "Analyse TCS for value investing"
    python main.py                    # interactive prompt

Optional environment variables:
    OPENAI_API_KEY          - Your API key (required)
    OPENAI_BASE_URL         - For custom endpoints (e.g., Grok: https://api.x.ai/v1)
"""

import json
import os
import sys
from datetime import datetime

from agent.llm import setup_llm
from agent.steps import (
    step1_parse_query,
    step2_fetch_stock_data,
    step3_analyze_financials,
    step4_fetch_news,
    step5_analyze_sentiment,
    step6_assess_risk,
    step7_generate_report,
)

OUTPUT_DIR = "output"


# 
# State factory
# 

def create_state(user_query: str) -> dict:
    """Return a fresh shared state object that every step reads from and writes to."""
    return {
        # Input
        "user_query": user_query,
        # Step outputs (populated as chain runs)
        "parsed_query":       {},   # Step 1
        "stock_data":         {},   # Step 2 (Tool)
        "financial_analysis": {},   # Step 3
        "news_data":          {},   # Step 4 (Tool)
        "sentiment_analysis": {},   # Step 5
        "risk_assessment":    {},   # Step 6
        "final_report":       "",   # Step 7
        # Bookkeeping
        "step_log": [],
        "errors":   [],
        "timestamp": datetime.now().isoformat(),
    }


# 
# Output writers
# 

def save_outputs(state: dict) -> tuple[str, str]:
    """Persist the full state as JSON and the report as Markdown."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ticker_safe = (
        state["parsed_query"].get("ticker", "UNKNOWN")
        .replace(".", "_")
        .replace("/", "_")
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Full state JSON (for debugging / demo)
    json_path = os.path.join(OUTPUT_DIR, f"{ticker_safe}_{ts}_state.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)

    # 2. Human-readable Markdown report
    md_path = os.path.join(OUTPUT_DIR, f"{ticker_safe}_{ts}_report.md")
    company = state["parsed_query"].get("company_name", ticker_safe)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Investment Research Report  {company}\n")
        f.write(f"*Generated: {state['timestamp']}*\n\n")
        f.write("---\n\n")
        f.write(state.get("final_report", "_No report generated._"))
        f.write("\n\n---\n\n")
        f.write("## Agent Chain Log\n\n")
        f.write("| Step | Name | Type | Input | Output |\n")
        f.write("|------|------|------|-------|--------|\n")
        for log in state["step_log"]:
            f.write(
                f"| {log['step']} | {log['name']} | {log['type']} "
                f"| {log['input_summary']} | {log['output_summary']} |\n"
            )
        if state["errors"]:
            f.write("\n## Errors Encountered\n\n")
            for err in state["errors"]:
                f.write(f"- {err}\n")

    return json_path, md_path


# 
# Agent runner
# 

def run_agent(user_query: str) -> dict:
    """Execute the full 7-step chain and return the final state."""

    print("\n" + "" * 62)
    print("  FINANCE RESEARCH AGENT    OpenAI GPT-4 Turbo")
    print("" * 62)
    print(f"  Query: {user_query}")
    print("" * 62)

    model = setup_llm()
    state = create_state(user_query)

    try:
        state = step1_parse_query(model, state)
        state = step2_fetch_stock_data(state)

        if not state["stock_data"].get("success"):
            ticker = state["parsed_query"].get("ticker", "UNKNOWN")
            err_msg = (
                f"Stock data fetch failed for ticker '{ticker}'. "
                f"The symbol may not exist. Aborting to avoid wasting API credits."
            )
            print(f"\n  [ABORT] {err_msg}")
            state["errors"].append(err_msg)
            state["final_report"] = (
                f"## Error\n\n{err_msg}\n\n"
                "Please verify the ticker symbol and try again."
            )
            return state

        state = step3_analyze_financials(model, state)
        state = step4_fetch_news(state)
        state = step5_analyze_sentiment(model, state)
        state = step6_assess_risk(model, state)
        state = step7_generate_report(model, state)

    except Exception as exc:
        print(f"\n[FATAL] Chain aborted at: {exc}")
        state["errors"].append(f"Fatal: {exc}")
        import traceback
        traceback.print_exc()

    #  Print report to terminal 
    print("\n" + "" * 62)
    print("  FINAL REPORT")
    print("" * 62)
    print(state.get("final_report") or "No report was generated.")

    #  Persist outputs 
    json_path, md_path = save_outputs(state)
    print("\n" + "" * 62)
    print(f"  Outputs saved:")
    print(f"    Markdown report : {md_path}")
    print(f"    Full state JSON : {json_path}")
    if state["errors"]:
        print(f"    Errors logged   : {state['errors']}")
    print("" * 62 + "\n")

    return state


# 
# CLI entry point
# 

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("\nFinance Research Agent  Enter your query.")
        print("Examples:")
        print("  Should I invest in Apple (AAPL) for long-term growth?")
        print("  Analyse TCS (Tata Consultancy Services) for value investing")
        print("  What is the risk profile of Tesla stock?")
        print("  Is Reliance Industries a good buy right now?\n")
        query = input("Query: ").strip()
        if not query:
            query = "Should I invest in Apple (AAPL) for long-term growth?"

    run_agent(query)
