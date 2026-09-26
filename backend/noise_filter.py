"""
noise_filter.py

Pure function — no LLM calls.
Drops commits that carry no meaningful signal:
  - all changed files are generated/lock files
  - the diff is whitespace/formatting only
"""

import re

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


def filter_commits(commits: list[dict]) -> list[dict]:
    """
    Remove low-signal commits from a list.

    Args:
        commits: Raw commit list from git_extractor.extract_commits().

    Returns:
        Filtered list — same shape, subset of input.
    """
    return [c for c in commits if _is_meaningful(c)]


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
    Returns True if every changed line (+ or - prefix) differs only in whitespace.
    """
    added = []
    removed = []

    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])

    if not added and not removed:
        return True

    all_lines = added + removed
    return all(line.strip() == "" for line in all_lines)
