"""
blocker_detector.py

Pure function — no LLM calls.
Flags patterns that suggest a developer is struggling:
  - Same file touched in 3+ commits within the window
  - Commit message contains "revert", "undo", "wip", or "fix fix"
"""

import re
from collections import Counter

_STRUGGLE_RE = re.compile(r"\b(revert|undo|wip|fix fix)\b", re.IGNORECASE)
_REPEATED_FILE_THRESHOLD = 3


def detect_blockers(commits: list[dict]) -> list[dict]:
    """
    Scan all commits and return a list of blocker signals.

    Args:
        commits: Full analyzed commit list (pre-grouping is fine).

    Returns:
        List of blocker dicts: {target, reason}
        - target: the file path or commit hash that triggered the flag
        - reason: "repeated_changes" | "possible_struggle"
    """
    blockers = []
    blockers.extend(_find_repeated_files(commits))
    blockers.extend(_find_struggle_messages(commits))
    return blockers


def _find_repeated_files(commits: list[dict]) -> list[dict]:
    """Flag files that appear in 3 or more commits."""
    file_counts: Counter = Counter()
    for commit in commits:
        for f in commit.get("files_changed", []):
            file_counts[f] += 1

    return [
        {"target": file, "reason": "repeated_changes"}
        for file, count in file_counts.items()
        if count >= _REPEATED_FILE_THRESHOLD
    ]


def _find_struggle_messages(commits: list[dict]) -> list[dict]:
    """Flag commits whose message matches struggle keywords."""
    blockers = []
    for commit in commits:
        if _STRUGGLE_RE.search(commit.get("message", "")):
            blockers.append({
                "target": commit["hash"],
                "reason": "possible_struggle",
                "message": commit["message"],
            })
    return blockers
