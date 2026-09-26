"""
summarizer.py

Assembles the final summary object from grouped commits and blockers.
This is the single source of truth that all format renderers consume.
"""

from datetime import datetime, timezone


def build_summary(
    repo: str,
    since: str,
    until: str | None,
    groups: list[dict],
    blockers: list[dict],
    raw_commits: list[dict],
) -> dict:
    """
    Assemble the canonical summary object.

    Returns:
        {
            repo, range: {since, until},
            groups: [{theme, commits, authors}],
            blockers: [{target, reason}],
            raw_log: [raw commit messages for before/after view]
        }
    """
    until_str = until or datetime.now(timezone.utc).isoformat()

    raw_log = [
        f"{c['hash'][:7]} {c['author']} — {c['message']}"
        for c in raw_commits
    ]

    return {
        "repo": repo,
        "range": {
            "since": since,
            "until": until_str,
        },
        "groups": groups,
        "blockers": blockers,
        "raw_log": raw_log,
    }
