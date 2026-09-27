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

        commits.append({
            "hash": hash_.strip(),
            "author": author.strip(),
            "timestamp": timestamp.strip(),
            "message": message.strip(),
            "diff": diff,
            "files_changed": files_changed,
        })

    return commits
