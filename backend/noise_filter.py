"""
noise_filter.py

Pure function — no LLM calls.
Drops commits that carry no meaningful signal:
  - all changed files are generated/lock files
  - the diff is whitespace/formatting only
  - reverts, together with the commit they revert (the pair cancels out,
    so neither is an accomplishment)
"""

import re
from collections import Counter

# Patterns for generated or lock files — extend as needed
GENERATED_FILE_PATTERNS = [
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"composer\.lock$",
    r"Pipfile\.lock$",
    r"poetry\.lock$",
    r"\.min\.js$",
    r"\.min\.css$",
    r"dist/",
    r"build/",
    r"\.next/",
    r"__pycache__/",
    r"\.pyc$",
    r"coverage/",
    r"\.map$",
]

_GENERATED_RE = re.compile("|".join(GENERATED_FILE_PATTERNS))

# "Revert ..." / "Undo ..." subjects; git's own revert subject is: Revert "<original subject>"
_REVERT_RE = re.compile(r"^(revert|undo)\b", re.IGNORECASE)
_REVERTED_SUBJECT_RE = re.compile(r'^Revert "(.+)"$')


def filter_commits(commits: list[dict]) -> list[dict]:
    """
    Remove low-signal commits from a list.

    Args:
        commits: Raw commit list from git_extractor.extract_commits().

    Returns:
        Filtered list — same shape, subset of input.
    """
    reverted = {
        m.group(1)
        for c in commits
        if (m := _REVERTED_SUBJECT_RE.match(c.get("message", "")))
    }
    return [
        c for c in commits
        if _is_meaningful(c)
        and not _REVERT_RE.match(c.get("message", ""))
        and c.get("message", "") not in reverted
    ]


def _is_meaningful(commit: dict) -> bool:
    files = commit.get("files_changed", [])
    diff = commit.get("diff", "")

    # Keep commits that touch at least one non-generated file
    real_files = [f for f in files if not _GENERATED_RE.search(f)]
    if files and not real_files:
        return False

    # Drop whitespace/formatting-only diffs
    if diff and _is_whitespace_only(diff):
        return False

    return True


def _is_whitespace_only(diff: str) -> bool:
    """
    Returns True if the diff only changes spacing: indentation, trailing
    spaces, or blank lines. Compares added vs removed lines with all
    whitespace stripped, so re-indenting a block counts as no change.
    """
    added: Counter = Counter()
    removed: Counter = Counter()

    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added["".join(line[1:].split())] += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed["".join(line[1:].split())] += 1

    # Blank lines added or removed don't count
    del added[""], removed[""]
    return added == removed
