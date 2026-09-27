"""
client_renderer.py

Generates client-facing (non-technical) versions of all three output formats.
One LLM call produces a plain-English benefit narrative; three pure functions
then wrap it into the appropriate format shape.

The client-facing tone:
  - No file names, packages, or code references
  - Focuses on user benefit: what changed, why it matters, what improved
  - No commit groupings by directory (meaningless to non-technical readers)
"""

from pathlib import Path
from backend.llm_client import generate

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "client_summary.txt"
_MAX_TOKENS = 600  # narrative prose needs more room than per-commit sentences


def render_all(summary: dict) -> dict:
    """
    Run one LLM call to produce a client-facing narrative, then wrap it into
    slack / email / standup format strings.

    Returns:
        {"slack": str, "email": str, "standup": str}
    """
    narrative = _generate_narrative(summary)
    repo = summary["repo"]
    since = summary["range"]["since"]
    until = summary["range"]["until"]

    return {
        "slack":   _slack(narrative, repo, since, until),
        "email":   _email(narrative, repo, since, until),
        "standup": _standup(narrative, summary, since, until),
    }


def _generate_narrative(summary: dict) -> str:
    """Call the LLM once with all commit summaries and return the narrative."""
    prompt_template = _PROMPT_PATH.read_text()

    # Collect the developer-written per-commit summaries (already generated)
    commits_text = ""
    for group in summary["groups"]:
        for commit in group["commits"]:
            text = commit.get("summary") or commit["message"]
            commits_text += f"- {text}\n"

    if not commits_text.strip():
        return "No significant changes were found in this period."

    prompt = prompt_template.replace("{{COMMITS}}", commits_text)
    return generate(prompt, max_tokens=_MAX_TOKENS)


# ── Format wrappers ────────────────────────────────────────────────────────────

def _slack(narrative: str, repo: str, since: str, until: str) -> str:
    lines = [
        f"*📢 Product Update — `{repo}`*",
        f"_{since}  →  {until}_",
        "",
        narrative,
    ]
    return "\n".join(lines)


def _email(narrative: str, repo: str, since: str, until: str) -> str:
    lines = [
        f"Subject: Product Update — {repo}",
        f"Period: {since} to {until}",
        "",
        "Hi,",
        "",
        narrative,
        "",
        "Best,",
        "Standup Sync",
    ]
    return "\n".join(lines)


def _standup(narrative: str, summary: dict, since: str, until: str) -> str:
    """
    Client-facing standup: one narrative paragraph per author, re-using the
    same narrative since grouping by file/directory is meaningless to clients.
    We list the authors who contributed so stakeholders know who to credit.
    """
    authors = sorted({
        commit["author"]
        for group in summary["groups"]
        for commit in group["commits"]
    })
    author_line = ", ".join(authors) if authors else "the team"

    lines = [
        f"PRODUCT UPDATE — {summary['repo']}",
        f"{since} → {until}",
        "",
        f"Contributors this period: {author_line}",
        "",
        narrative,
    ]
    return "\n".join(lines)
