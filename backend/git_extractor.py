"""
git_extractor.py

Given a local repo path (or a URL to clone) and a date range,
returns a list of raw commit objects with diffs.
"""

import subprocess
import tempfile
import shutil
import re
from datetime import datetime
from typing import Optional


def extract_commits(
    repo: str,
    since: str,
    until: Optional[str] = None,
) -> list[dict]:
    """
    Extract commits with diffs from a git repo.

    Args:
        repo:  Local path or HTTPS URL to a git repository.
        since: ISO date string or relative string e.g. "2024-01-01" or "24 hours ago".
        until: Optional ISO date string. Defaults to now.

    Returns:
        List of dicts: {hash, author, timestamp, message, diff, files_changed}

    Raises:
        ValueError: if the repo path is invalid or no git repo is found.
        RuntimeError: if git subprocess fails.
    """
    tmp_dir = None
    try:
        if repo.startswith("http://") or repo.startswith("https://") or repo.startswith("git@"):
            tmp_dir = tempfile.mkdtemp(prefix="standup_sync_")
            _run(["git", "clone", "--bare", "--filter=blob:none", "--depth=200", repo, tmp_dir])
            repo_path = tmp_dir
        else:
            repo_path = repo

        _verify_repo(repo_path)

        cmd = [
            "git", "-C", repo_path,
            "log",
            "--no-merges",
            f"--since={since}",
            "-p",
            "--no-color",
            "--format=COMMIT_START|%H|%an|%ai|%s",
        ]
        if until:
            cmd.append(f"--until={until}")

        raw = _run(cmd)
        return _parse_log(raw)

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _verify_repo(path: str) -> None:
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--git-dir"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ValueError(f"Not a valid git repository: {path}")


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def _parse_log(raw: str) -> list[dict]:
    """Split raw git log -p output into structured commit objects."""
    commits = []
    # Split on our custom separator line
    blocks = re.split(r"(?=COMMIT_START\|)", raw)

    for block in blocks:
        block = block.strip()
        if not block.startswith("COMMIT_START|"):
            continue

        lines = block.splitlines()
        header = lines[0]
        parts = header.split("|", 4)
        if len(parts) < 5:
            continue

        _, hash_, author, timestamp, message = parts
        diff = "\n".join(lines[1:]).strip()

        # Collect touched file names from diff headers
        files_changed = re.findall(r"^diff --git a/(.+?) b/", diff, re.MULTILINE)

        stats = _parse_diff_stats(diff)
        commits.append({
            "hash": hash_.strip(),
            "author": author.strip(),
            "timestamp": timestamp.strip(),
            "message": message.strip(),
            "diff": diff,
            "files_changed": files_changed,
            **stats,
        })

    return commits


def _parse_diff_stats(diff: str) -> dict:
    """
    Parse a raw git diff patch and return file-level and line-level counts.

    File classification per file block:
      - added:    source is /dev/null  (--- /dev/null)
      - deleted:  dest   is /dev/null  (+++ /dev/null)
      - modified: everything else

    lines_added:   count of '+' lines excluding '+++ b/...' headers
    lines_deleted: count of '-' lines excluding '--- a/...' headers
    lines_updated: per-hunk min(plus_lines, minus_lines) summed across all hunks
                   — approximates lines changed in-place rather than purely added/removed

    Returns:
        {files_added, files_deleted, files_modified, lines_added, lines_deleted, lines_updated}
    """
    files_added = files_deleted = files_modified = 0
    total_lines_added = total_lines_deleted = total_lines_updated = 0

    # Split into per-file blocks on "diff --git" boundaries
    file_blocks = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)

    for block in file_blocks:
        if not block.strip():
            continue

        is_added   = bool(re.search(r"^--- /dev/null", block, re.MULTILINE))
        is_deleted = bool(re.search(r"^\+\+\+ /dev/null", block, re.MULTILINE))

        if is_added:
            files_added += 1
        elif is_deleted:
            files_deleted += 1
        else:
            files_modified += 1

        # Count lines per hunk for lines_updated approximation
        # Split on hunk headers (@@ ... @@)
        hunks = re.split(r"^@@[^@]*@@[^\n]*\n?", block, flags=re.MULTILINE)
        for hunk in hunks[1:]:  # first element is file header, skip it
            hunk_plus = 0
            hunk_minus = 0
            for line in hunk.splitlines():
                if line.startswith("+"):
                    hunk_plus += 1
                    total_lines_added += 1
                elif line.startswith("-"):
                    hunk_minus += 1
                    total_lines_deleted += 1
            total_lines_updated += min(hunk_plus, hunk_minus)

    return {
        "files_added":    files_added,
        "files_deleted":  files_deleted,
        "files_modified": files_modified,
        "lines_added":    total_lines_added,
        "lines_deleted":  total_lines_deleted,
        "lines_updated":  total_lines_updated,
    }
