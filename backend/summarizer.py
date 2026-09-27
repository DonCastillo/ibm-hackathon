"""
summarizer.py

Assembles the final summary object from grouped commits.
This is the single source of truth that all format renderers consume.
"""

from datetime import datetime, timezone


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
            repo, range: {since, until},
            groups: [{theme, commits, authors}],
            raw_log: [raw commit messages for before/after view],
            omitted_minor: count of minor updates left out of groups
        }
    """
    until_str = until or datetime.now(timezone.utc).isoformat()

    raw_log = [format_log_line(c) for c in raw_commits]

    # Aggregate per-commit stats by author
    _STAT_KEYS = ("files_added", "files_deleted", "files_modified",
                  "lines_added", "lines_deleted", "lines_updated")
    author_stats: dict[str, dict] = {}
    for c in raw_commits:
        author = c["author"]
        if author not in author_stats:
            author_stats[author] = {"commits": 0, **{k: 0 for k in _STAT_KEYS}, "branches": set()}
        author_stats[author]["commits"] += 1
        if c.get("branch"):
            author_stats[author]["branches"].add(c["branch"])
        for k in _STAT_KEYS:
            author_stats[author][k] += c.get(k, 0)

    for stats in author_stats.values():
        stats["branches"] = sorted(stats["branches"])

    return {
        "repo": repo,
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
