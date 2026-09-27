"""
summarizer.py

Assembles the final summary object from grouped commits.
This is the single source of truth that all format renderers consume.
"""

import re
from datetime import date, datetime, timedelta, timezone


def build_summary(
    repo: str,
    since: str,
    until: str | None,
    groups: list[dict],
    raw_commits: list[dict],
    omitted_minor: int = 0,
) -> dict:
    """
    Assemble the canonical summary object.

    Returns:
        {
            repo, range: {since, until}, period: "Sep 20, 2026 - Sep 27, 2026",
            groups: [{theme, commits, authors}],
            raw_log: [raw commit messages for before/after view],
            omitted_minor: count of minor updates left out of groups
        }
    """
    until_str = until or datetime.now(timezone.utc).isoformat()

    raw_log = [format_log_line(c) for c in raw_commits]

    # Per-author stats. commits: every commit in the range. highlights: commits
    # that made it into the reports (the major updates in `groups`).
    author_stats: dict[str, dict] = {}
    for c in raw_commits:
        stats = author_stats.setdefault(c["author"], {"highlights": 0, "commits": 0, "branches": set()})
        stats["commits"] += 1
        if c.get("branch"):
            stats["branches"].add(c["branch"])
    for group in groups:
        for c in group["commits"]:
            author_stats.setdefault(c["author"], {"highlights": 0, "commits": 0, "branches": set()})
            author_stats[c["author"]]["highlights"] += 1

    for stats in author_stats.values():
        stats["branches"] = sorted(stats["branches"])

    return {
        "repo": repo,
        "period": period_label(since, until),
        "range": {
            "since": since,
            "until": until_str,
        },
        "groups": groups,
        "raw_log": raw_log,
        "author_stats": author_stats,
        "omitted_minor": omitted_minor,
    }


def omitted_note(summary: dict) -> str | None:
    """Footer line for renderers, e.g. '+ 4 minor updates (small fixes, docs, tweaks) not shown'."""
    n = summary.get("omitted_minor", 0)
    if not n:
        return None
    return f"+ {n} minor update{'s' if n != 1 else ''} (small fixes, docs, tweaks) not shown"


def format_log_line(commit: dict) -> str:
    """One-line raw log entry, e.g. 'abc1234 [feature/login] Jane — Add login form'."""
    branch = f"[{commit['branch']}] " if commit.get("branch") else ""
    return f"{commit['hash'][:7]} {branch}{commit['author']} — {commit['message']}"


def period_label(since: str, until: str | None, now: datetime | None = None) -> str:
    """
    Human-readable range, matching the UI title: "Sep 20, 2026 - Sep 27, 2026",
    or "Sep 10, 2026" for a single day. `since` is a preset like "7 days ago" or
    a YYYY-MM-DD date; `until` is a YYYY-MM-DD date or None (now).
    """
    now = now or datetime.now()
    m = re.fullmatch(r"(\d+)\s+(hour|day)s?\s+ago", since.strip())
    if m:
        n = int(m.group(1))
        start = (now - (timedelta(hours=n) if m.group(2) == "hour" else timedelta(days=n))).date()
    elif re.match(r"\d{4}-\d{2}-\d{2}", since):
        start = date.fromisoformat(since[:10])
    else:
        return since
    end = date.fromisoformat(until[:10]) if until else now.date()

    def fmt(d: date) -> str:
        return f"{d:%b} {d.day}, {d.year}"

    return fmt(start) if start == end else f"{fmt(start)} - {fmt(end)}"
