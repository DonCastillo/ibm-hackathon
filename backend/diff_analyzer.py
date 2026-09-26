"""
diff_analyzer.py

Sends filtered commits to the LLM in batches, concurrently.
Returns each commit enriched with a plain-English summary sentence.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from backend.llm_client import generate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "diff_analysis.txt"
_BATCH_SIZE = 10   # commits per LLM call
_MAX_WORKERS = 3   # concurrent LLM calls
_DIFF_LIMIT = 1500 # chars per diff — tighter truncation = fewer tokens = faster


def analyze_commits(commits: list[dict]) -> list[dict]:
    """
    Enrich each commit with a plain-English 'summary' field.
    Batches are sent to the LLM concurrently for speed.

    Args:
        commits: Filtered commit list from noise_filter.filter_commits().

    Returns:
        Same list with 'summary' field added to each commit dict.
    """
    if not commits:
        return []

    prompt_template = _PROMPT_PATH.read_text()
    batches = _batch(commits, _BATCH_SIZE)

    # Run all batches concurrently, preserve original order
    results_by_index: dict[int, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {
            executor.submit(_analyze_batch, batch, prompt_template): i
            for i, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            i = futures[future]
            results_by_index[i] = future.result()

    # Flatten back in original order
    results = []
    for i in range(len(batches)):
        results.extend(results_by_index[i])
    return results


def _batch(items: list, size: int) -> list[list]:
    """Split a list into chunks of at most `size` items."""
    return [items[i:i + size] for i in range(0, len(items), size)]


def _analyze_batch(batch: list[dict], prompt_template: str) -> list[dict]:
    """Send one batch of commits to the LLM, return enriched commit dicts."""
    commits_text = ""
    for i, commit in enumerate(batch, 1):
        diff_snippet = commit["diff"][:_DIFF_LIMIT] if commit["diff"] else "(no diff)"
        commits_text += (
            f"\n---\nCommit {i}\n"
            f"Message: {commit['message']}\n"
            f"Files: {', '.join(commit['files_changed']) or 'unknown'}\n"
            f"Diff:\n{diff_snippet}\n"
        )

    prompt = prompt_template.replace("{{COMMITS}}", commits_text).replace(
        "{{COUNT}}", str(len(batch))
    )

    raw_response = generate(prompt)
    summaries = _parse_summaries(raw_response, len(batch))
    return [{**commit, "summary": summary} for commit, summary in zip(batch, summaries)]


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
