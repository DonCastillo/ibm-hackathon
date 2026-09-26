"""
grouper.py

Pure function — no LLM calls.
Clusters commits by their most common top-level touched directory,
then records which authors contributed to each group.
"""

from collections import defaultdict


def group_commits(commits: list[dict]) -> list[dict]:
    """
    Group commits by the top-level directory of the files they touch.

    Args:
        commits: Analyzed commit list (each has 'files_changed' and 'summary').

    Returns:
        List of group dicts: {theme, commits, authors}
    """
    buckets: dict[str, list[dict]] = defaultdict(list)

    for commit in commits:
        theme = _get_theme(commit["files_changed"])
        buckets[theme].append(commit)

    groups = []
    for theme, group_commits in buckets.items():
        authors = sorted({c["author"] for c in group_commits})
        groups.append({
            "theme": theme,
            "commits": group_commits,
            "authors": authors,
        })

    # Sort groups by number of commits descending (most active first)
    groups.sort(key=lambda g: len(g["commits"]), reverse=True)
    return groups


def _get_theme(files: list[str]) -> str:
    """
    Derive a theme label from the list of touched files.
    Uses the most common top-level directory, or the filename for root files.
    """
    if not files:
        return "misc"

    themes = []
    for f in files:
        parts = f.split("/")
        themes.append(parts[0] if len(parts) > 1 else f)

    # Pick the most common theme in this commit
    return max(set(themes), key=themes.count)
