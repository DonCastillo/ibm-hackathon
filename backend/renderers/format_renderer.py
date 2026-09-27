"""
format_renderer.py

Renders the summary object into all six outputs: Slack / Email / Standup for
a developer and a client audience, following plan/format.md.

One LLM call per audience writes all three formats at once (2 calls per run,
run in parallel). The prompt is assembled from prompts/render_base.md, the
audience file, and one rules file per format, so each format's constraints
live in their own file. The reply is split on === SLACK === / === EMAIL === /
=== STANDUP === markers, the length limits are enforced in code, and the
headers (title, period, greeting, sign-off) are added here, not by the LLM.
"""

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.llm_client import generate
from backend.summarizer import omitted_note

_PROMPTS = Path(__file__).parent.parent.parent / "prompts"
_AUDIENCES = ("developer", "client")
_FORMATS = ("slack", "email", "standup")
# Output budget for all three formats together (~650 tokens expected)
_MAX_TOKENS = 1500

# Hard limits from plan/format.md. Email allows ~400 before it counts as too long.
_SLACK_MAX_BULLETS = 6
_STANDUP_MAX_FRAGMENTS = 3
_EMAIL_MAX_WORDS = 400

_MARKER_RE = re.compile(r"^\s*===\s*(SLACK|EMAIL|STANDUP)\s*===\s*$", re.MULTILINE | re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*(?:[•\-*]|\d+[.)])\s*")
_CLIENT_UNAVAILABLE = "(This update couldn't be generated. Please try again.)"


def render_all(summary: dict) -> tuple[dict, dict]:
    """
    Returns:
        (developer_formats, client_formats), each {"slack", "email", "standup"} -> str
    """
    with ThreadPoolExecutor(max_workers=len(_AUDIENCES)) as pool:
        dev, client = pool.map(lambda audience: _render_audience(summary, audience), _AUDIENCES)
    return dev, client


# ── One audience: prompt -> LLM -> split -> enforce -> wrap ───────────────────

def _render_audience(summary: dict, audience: str) -> dict:
    bodies = {}
    try:
        prompt = _build_prompt(summary, audience)
        # One retry if the email is over its word limit (the whole call is redone)
        for attempt in range(2):
            bodies = _split_sections(generate(prompt, max_tokens=_MAX_TOKENS))
            if _word_count(bodies.get("email", "")) <= _EMAIL_MAX_WORDS:
                break
    except Exception:
        bodies = {}  # LLM unavailable: fall back below rather than failing the whole report

    enforced = {
        "slack":   _enforce_slack(bodies.get("slack", "")),
        "email":   _enforce_email(bodies.get("email", "")),
        "standup": _enforce_standup(bodies.get("standup", "")),
    }
    for fmt in _FORMATS:
        if not enforced[fmt]:
            # Developer: a plain list built from the summaries. Client: never show
            # technical summaries, so just say it's unavailable.
            enforced[fmt] = _FALLBACKS[fmt](summary) if audience == "developer" else _CLIENT_UNAVAILABLE
    return {fmt: _wrap(fmt, audience, enforced[fmt], summary) for fmt in _FORMATS}


def _build_prompt(summary: dict, audience: str) -> str:
    updates = [
        f"- [{group['theme']}] ({commit['author']}) {commit.get('summary') or commit['message']}"
        for group in summary["groups"]
        for commit in group["commits"]
    ]
    return (
        _read("render_base.md")
        .replace("{{AUDIENCE_RULES}}", _read(f"audience_{audience}.md").strip())
        .replace("{{SLACK_RULES}}", _read("slack.md").strip())
        .replace("{{EMAIL_RULES}}", _read("email.md").strip())
        .replace("{{STANDUP_RULES}}", _read("standup.md").strip())
        .replace("{{PERIOD}}", summary["period"])
        .replace("{{UPDATES}}", "\n".join(updates) or "(none)")
    )


def _read(name: str) -> str:
    return (_PROMPTS / name).read_text()


def _split_sections(response: str) -> dict:
    """Split the reply on its === MARKER === lines. Missing sections are simply absent."""
    parts = _MARKER_RE.split(response)
    # re.split with one group -> [before, NAME, body, NAME, body, ...]
    sections = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        sections.setdefault(name.lower(), body.strip())
    return sections


# ── Enforcing the format.md limits ─────────────────────────────────────────────

def _enforce_slack(body: str) -> str:
    bullets = [_BULLET_RE.sub("", line).strip() for line in body.splitlines() if line.strip()]
    return "\n".join(f"• {b}" for b in bullets[:_SLACK_MAX_BULLETS] if b)


def _enforce_standup(body: str) -> str:
    """Keep at most 3 fragments per person; lines without a bullet are names."""
    people: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        if not line.strip():
            continue
        if _BULLET_RE.match(line):
            if people:
                people[-1][1].append(_BULLET_RE.sub("", line).strip())
        else:
            people.append((line.strip(), []))
    blocks = [
        "\n".join([name] + [f"- {f}" for f in fragments[:_STANDUP_MAX_FRAGMENTS]])
        for name, fragments in people
        if fragments
    ]
    return "\n\n".join(blocks)


def _enforce_email(body: str) -> str:
    """If still over the word limit after the retry, drop trailing sections."""
    sections = [s.strip() for s in re.split(r"\n\s*\n", body) if s.strip()]
    while len(sections) > 1 and _word_count("\n\n".join(sections)) > _EMAIL_MAX_WORDS:
        sections.pop()
    return "\n\n".join(sections)


def _word_count(text: str) -> int:
    return len(text.split())


# ── Developer fallbacks (LLM unavailable or a section missing) ────────────────

def _fallback_slack(summary: dict) -> str:
    items = [c.get("summary") or c["message"] for g in summary["groups"] for c in g["commits"]]
    return "\n".join(f"• {s}" for s in items[:_SLACK_MAX_BULLETS])


def _fallback_email(summary: dict) -> str:
    return "\n\n".join(
        f"{g['theme']}:\n" + "\n".join(f"- {c.get('summary') or c['message']}" for c in g["commits"][:5])
        for g in summary["groups"][:4]
    )


def _fallback_standup(summary: dict) -> str:
    by_author = defaultdict(list)
    for g in summary["groups"]:
        for c in g["commits"]:
            by_author[c["author"]].append(c.get("summary") or c["message"])
    return "\n\n".join(
        "\n".join([author] + [f"- {s}" for s in items[:_STANDUP_MAX_FRAGMENTS]])
        for author, items in sorted(by_author.items())
    )


_FALLBACKS = {"slack": _fallback_slack, "email": _fallback_email, "standup": _fallback_standup}


# ── Headers ────────────────────────────────────────────────────────────────────

def _wrap(fmt: str, audience: str, body: str, summary: dict) -> str:
    """Add title, period, greeting and sign-off. Client versions never show the repo name."""
    period = summary["period"]
    client = audience == "client"
    # Minor-update count is useful to developers, noise to clients
    note = None if client else omitted_note(summary)

    if fmt == "slack":
        title = "*📢 Product Update*" if client else f"*📋 Standup Sync — `{summary['repo']}`*"
        lines = [title, f"_{period}_", "", body]
        if note:
            lines += ["", f"_{note}_"]
    elif fmt == "email":
        subject = f"Subject: Product Update — {period}" if client else f"Subject: Project Update — {summary['repo']}"
        lines = [subject] + ([] if client else [f"Period: {period}"])
        lines += ["", "Hi," if client else "Hi team,", "", body]
        if note:
            lines += ["", f"({note}.)"]
        lines += ["", "Best,", "Standup Sync"]
    else:
        title = "PRODUCT UPDATE" if client else f"STANDUP NOTES — {summary['repo']}"
        lines = [title, period, "", body]
        if note:
            lines += ["", note]
    return "\n".join(lines)
