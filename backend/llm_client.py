"""
llm_client.py

Single entry point for all LLM calls in the pipeline.
Swap this file out to change providers — nothing else in the codebase
touches the LLM API directly.
"""

import os
import warnings
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters
from dotenv import load_dotenv

load_dotenv()

_MODEL_ID = "mistralai/mistral-small-3-1-24b-instruct-2503"

_model: ModelInference | None = None


def _get_model() -> ModelInference:
    global _model
    if _model is None:
        api_key = os.getenv("WATSONX_API_KEY")
        project_id = os.getenv("WATSONX_PROJECT_ID")
        url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

        if not api_key or not project_id:
            raise RuntimeError(
                "Missing WATSONX_API_KEY or WATSONX_PROJECT_ID in environment. "
                "Copy .env.example to .env and fill in your credentials."
            )

        _model = ModelInference(
            model_id=_MODEL_ID,
            credentials={"apikey": api_key, "url": url},
            project_id=project_id,
            params={
                "max_new_tokens": 200,
                "temperature": 0.1,
            },
        )
    return _model


def generate(prompt: str) -> str:
    """
    Send a prompt to the LLM and return the response text.

    Args:
        prompt: Full prompt string (system + user content combined).

    Returns:
        Generated text string.
    """
    model = _get_model()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = model.chat(messages=[{"role": "user", "content": prompt}])
    return response["choices"][0]["message"]["content"].strip()
