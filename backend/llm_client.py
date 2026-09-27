"""
llm_client.py

Single entry point for all LLM calls in the pipeline.
Provider is selected via the LLM_PROVIDER env var:
  LLM_PROVIDER=watsonx  (default) — uses IBM watsonx.ai
  LLM_PROVIDER=anthropic          — uses Anthropic Claude

Swap this file out to change providers entirely — nothing else in the
codebase touches the LLM API directly.
"""

import os
import warnings
from dotenv import load_dotenv

load_dotenv()

_PROVIDER = os.getenv("LLM_PROVIDER", "watsonx").lower()

# ── Watsonx config ────────────────────────────────────────────────────────────
_WATSONX_MODEL_ID = "mistralai/mistral-small-3-1-24b-instruct-2503"
_watsonx_model = None

# ── Anthropic config ──────────────────────────────────────────────────────────
_ANTHROPIC_MODEL_ID = "claude-haiku-4-5-20251001"  # fastest/cheapest available on this account
_anthropic_client = None


# ── Provider initializers ─────────────────────────────────────────────────────

def _get_watsonx():
    global _watsonx_model
    if _watsonx_model is None:
        from ibm_watsonx_ai.foundation_models import ModelInference
        api_key = os.getenv("WATSONX_API_KEY")
        project_id = os.getenv("WATSONX_PROJECT_ID")
        url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        if not api_key or not project_id:
            raise RuntimeError(
                "Missing WATSONX_API_KEY or WATSONX_PROJECT_ID. "
                "Fill in your .env file."
            )
        _watsonx_model = ModelInference(
            model_id=_WATSONX_MODEL_ID,
            credentials={"apikey": api_key, "url": url},
            project_id=project_id,
            params={"max_new_tokens": 200, "temperature": 0.1},
        )
    return _watsonx_model


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing ANTHROPIC_API_KEY. "
                "Fill in your .env file."
            )
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


# ── Public interface ──────────────────────────────────────────────────────────

def generate(prompt: str, max_tokens: int = 200) -> str:
    """
    Send a prompt to the configured LLM and return the response text.

    Args:
        prompt:     Full prompt string.
        max_tokens: Maximum tokens to generate. Defaults to 200 (enough for
                    single-sentence per-commit summaries). Pass a higher value
                    for longer narrative outputs (e.g. client-facing summaries).

    Returns:
        Generated text string.
    """
    if _PROVIDER == "anthropic":
        client = _get_anthropic()
        response = client.messages.create(
            model=_ANTHROPIC_MODEL_ID,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    else:  # default: watsonx
        model = _get_watsonx()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = model.chat(
                messages=[{"role": "user", "content": prompt}],
                params={"max_new_tokens": max_tokens, "temperature": 0.3},
            )
        return response["choices"][0]["message"]["content"].strip()
