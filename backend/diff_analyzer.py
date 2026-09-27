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
_DIFF_LIMIT = 4000 # chars per diff — enough to fit most real diffs in full
# Output budget per commit. A specific one-sentence summary runs ~30–50 tokens;
# the old flat 200-token default cut batches off after ~6 commits.
_TOKENS_PER_COMMIT = 80


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

    raw_response = generate(prompt, max_tokens=_TOKENS_PER_COMMIT * len(batch))
    summaries = _parse_summaries(raw_response, [c["message"] for c in batch])
    return [{**commit, "summary": summary} for commit, summary in zip(batch, summaries)]


def _parse_summaries(response: str, messages: list[str]) -> list[str]:
    """
    Map the LLM's numbered list back onto the batch by number ("3." -> commit 3),
    so an intro line or a skipped item can't shift summaries onto the wrong commit.

    Any commit without a usable summary falls back to its own commit message:
    missing numbers, or a final line cut off mid-sentence by the token limit.
    """
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    by_number: dict[int, str] = {}
    for line in lines:
        # Accept "3. text", "3) text" and markdown-bold "**3.** text"
        m = re.match(r"^\**(\d+)[.)]\**\s*(.+)$", line)
        if not m:
            continue
        n, text = int(m.group(1)), m.group(2).strip()
        if 1 <= n <= len(messages) and n not in by_number:
            by_number[n] = text

    # A final line with no closing punctuation was truncated mid-sentence
    if lines and by_number:
        last_n = max(by_number)
        if lines[-1].endswith(by_number[last_n]) and not re.search(r"[.!?)\"'`]$", by_number[last_n]):
            del by_number[last_n]

    return [by_number.get(i, msg) for i, msg in enumerate(messages, 1)]
