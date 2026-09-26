"""
diff_analyzer.py

Sends filtered commits to the LLM in batches.
Returns each commit enriched with a plain-English summary sentence.
"""

import math
from pathlib import Path
from backend.llm_client import generate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "diff_analysis.txt"
_BATCH_SIZE = 5  # commits per LLM call


def analyze_commits(commits: list[dict]) -> list[dict]:
    """
    Enrich each commit with a plain-English 'summary' field.

    Args:
        commits: Filtered commit list from noise_filter.filter_commits().

    Returns:
        Same list with 'summary' field added to each commit dict.
    """
    if not commits:
        return []

    prompt_template = _PROMPT_PATH.read_text()
    results = []

    batches = _batch(commits, _BATCH_SIZE)
    for batch in batches:
        summaries = _analyze_batch(batch, prompt_template)
        for commit, summary in zip(batch, summaries):
            results.append({**commit, "summary": summary})

    return results


def _analyze_batch(batch: list[dict], prompt_template: str) -> list[str]:
    """Send one batch of commits to the LLM, get back one summary per commit."""
    commits_text = ""
    for i, commit in enumerate(batch, 1):
        # Truncate very large diffs to avoid token limits
        diff_snippet = commit["diff"][:3000] if commit["diff"] else "(no diff)"
        commits_text += (
            f"\n---\nCommit {i}\n"
            f"Message: {commit['message']}\n"
            f"Author: {commit['author']}\n"
            f"Files: {', '.join(commit['files_changed']) or 'unknown'}\n"
            f"Diff:\n{diff_snippet}\n"
        )

    prompt = prompt_template.replace("{{COMMITS}}", commits_text).replace(
        "{{COUNT}}", str(len(batch))
    )

    raw_response = generate(prompt)
    summaries = _parse_summaries(raw_response, len(batch))
    return summaries


def _parse_summaries(response: str, expected_count: int) -> list[str]:
    """
    Parse numbered list from LLM response.
    Falls back gracefully if the model doesn't follow the format.
    """
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    # Try to match lines starting with "1.", "2.", etc.
    numbered = [re.sub(r"^\d+\.\s*", "", l) for l in lines if re.match(r"^\d+\.", l)]
    if len(numbered) == expected_count:
        return numbered
    # Fallback: return raw lines, padded/trimmed to expected count
    padded = (lines + ["(summary unavailable)"] * expected_count)[:expected_count]
    return padded


import re  # noqa: E402 — imported here to keep top of file clean
