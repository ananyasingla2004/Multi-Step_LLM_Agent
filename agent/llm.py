"""
LLM API wrapper supporting OpenAI and compatible APIs (including Grok).
All LLM calls route through here so retry logic and model config live in one place.
"""

import os
import json
import re
import time
from openai import OpenAI

_PRIMARY_MODEL = "gpt-4-turbo"
_FALLBACK_MODEL = "gpt-3.5-turbo"


def setup_llm() -> OpenAI:
    """Initialize OpenAI client. Supports OpenAI API and API-compatible services like Grok."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set.\n"
            "Run: export OPENAI_API_KEY=your_api_key_here\n"
            "Works with: OpenAI API, Grok API (xai.com), or any OpenAI-compatible endpoint."
        )
    
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        # For Grok or other compatible APIs
        return OpenAI(api_key=api_key, base_url=base_url)
    else:
        # Default to OpenAI
        return OpenAI(api_key=api_key)


def _is_retryable(e: Exception) -> bool:
    """Check if error is retryable (rate limit, temporary unavailability, etc)."""
    text = str(e).lower()
    return (
        "429" in str(e)
        or "rate_limit" in text
        or "quota" in text
        or "unavailable" in text
        or "503" in str(e)
        or "timeout" in text
    )


def _extract_retry_delay(exc: Exception) -> float | None:
    """Try to parse the seconds-to-wait from error message."""
    text = str(exc)
    # "Please retry in 21.475719406s."
    m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Check for "Retry-After" style header info
    m = re.search(r"retry.after.?:\s*([0-9]+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _generate_with_retries(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    retries: int = 5,
) -> str:
    """Call OpenAI API with retry logic for transient failures."""
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1 and _is_retryable(e):
                delay = _extract_retry_delay(e)
                wait = (delay or 5.0) + 2.0 if _is_rate_limit(e) else 2 ** attempt + 1.0
                tag = "Rate-limit" if _is_rate_limit(e) else "Unavailable"
                print(f"  [LLM] {tag} on {model} (attempt {attempt + 1}/{retries}). Retrying in {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Unreachable after {retries} retries")


def _is_rate_limit(e: Exception) -> bool:
    """Check if the error is a rate-limit error."""
    text = str(e).lower()
    return "429" in str(e) or "rate_limit" in text or "quota" in text


def call_llm(client: OpenAI, system_prompt: str, user_prompt: str, retries: int = 5) -> str:
    """
    Call LLM (OpenAI, Grok, or compatible API) with system + user prompts.
    Retries on transient failures with exponential backoff.
    """
    try:
        return _generate_with_retries(client, _PRIMARY_MODEL, system_prompt, user_prompt, retries)
    except Exception as primary_err:
        if not _is_retryable(primary_err):
            raise RuntimeError(f"LLM call failed: {primary_err}") from primary_err
        print(f"  [LLM] Primary model {_PRIMARY_MODEL} exhausted. Falling back to {_FALLBACK_MODEL}...")
        try:
            return _generate_with_retries(client, _FALLBACK_MODEL, system_prompt, user_prompt, retries)
        except Exception as fallback_err:
            raise RuntimeError(
                f"LLM call failed on both {_PRIMARY_MODEL} and {_FALLBACK_MODEL}: {fallback_err}"
            ) from fallback_err


def extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.
    Handles markdown fences, leading/trailing prose, etc.
    """
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract JSON from LLM response.\n"
        f"First 300 chars: {text[:300]}"
    )
