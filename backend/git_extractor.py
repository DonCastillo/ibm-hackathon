"""
git_extractor.py

Given a local repo path (or a URL to clone) and a date range,
returns a list of raw commit objects with diffs.
"""

import os
import subprocess
import tempfile
import shutil
import re
from datetime import datetime
from typing import Optional


class RepoAccessError(Exception):
    """Raised when a clone fails because the repo is private or the credentials were rejected."""


# stderr fragments git hosts emit when a clone is refused for lack of (valid) credentials.
# GitHub answers "private" and "doesn't exist" identically when unauthenticated.
_AUTH_FAILURE_PATTERNS = re.compile(
    r"could not read (username|password)"
    r"|terminal prompts disabled"
    r"|authentication failed"
    r"|invalid username or (password|token)"
    r"|repository not found"
    r"|http basic: access denied"
    r"|the requested url returned error: 40[134]"
    r"|permission denied \(publickey",
    re.IGNORECASE,
)

# Remote clones start shallow and blobless (commits + trees only) so all-branch
# clones stay fast; history and file contents are then filled in only where the
# date range needs them. See _complete_history() and _prefetch_blobs().
_CLONE_DEPTH = 200
_MAX_DEEPEN_ROUNDS = 10  # up to ~2,200 commits deep per branch

# Never block on a prompt: GIT_TERMINAL_PROMPT=0 for HTTPS credentials,
# BatchMode for SSH (password / unknown-host-key prompts).
_GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
_GIT_ENV.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")


def _inject_token(url: str, token: str) -> str:
    """
    Inject a Personal Access Token into an HTTPS git URL using the
    correct format for each host.

    Formats:
      GitHub / Gitea / generic:  https://<token>@host/...
      GitLab (cloud + self-hosted): https://oauth2:<token>@host/...
      Bitbucket Cloud:           https://x-token-auth:<token>@host/...
      Azure DevOps:              https://pat:<token>@host/...
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    host = parsed.hostname or ""

    if "gitlab" in host:
        userinfo = f"oauth2:{token}"
    elif "bitbucket" in host:
        userinfo = f"x-token-auth:{token}"
    elif "dev.azure.com" in host or "visualstudio.com" in host:
        userinfo = f"pat:{token}"
    else:
        # GitHub and everything else — token alone works as username
        userinfo = token

    # Replace netloc with credentialed version (strip any existing userinfo first)
    netloc = f"{userinfo}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunparse(parsed._replace(netloc=netloc))


def extract_commits(
    repo: str,
    since: str,
    until: Optional[str] = None,
    token: Optional[str] = None,
) -> list[dict]:
    """
    Extract commits with diffs from every branch of a git repo, so work on
    unmerged feature branches is captured. A commit on several branches is
    only returned once, tagged with one of them.

    Args:
        repo:  Local path or HTTPS URL to a git repository.
        since: ISO date string or relative string e.g. "2024-01-01" or "24 hours ago".
        until: Optional ISO date string. Defaults to now.
        token: Optional Personal Access Token for private repos (HTTPS only).

    Returns:
        List of dicts: {hash, author, timestamp, branch, message, diff, files_changed}

    Raises:
        ValueError: if the repo path is invalid or no git repo is found.
        RepoAccessError: if the clone is refused (private repo, bad token, SSH key rejected).
        RuntimeError: if git subprocess fails.
    """
    since = _day_bound(since, "00:00:00")
    # A bare clone keeps branches under refs/heads; local repos also have refs/remotes
    range_args = ["--no-merges", f"--since={since}"]
    if until:
        range_args.append(f"--until={_day_bound(until, '23:59:59')}")
    range_args += ["--branches", "--remotes"]

    tmp_dir = None
    try:
        if repo.startswith(("http://", "https://", "git@", "file://")):
            clone_url = _inject_token(repo, token) if token and repo.startswith(("http://", "https://")) else repo
            tmp_dir = tempfile.mkdtemp(prefix="standup_sync_")
            _clone(clone_url, tmp_dir, repo, token)
            _complete_history(tmp_dir, since, token)
            _prefetch_blobs(tmp_dir, range_args, token)
            repo_path = tmp_dir
        else:
            repo_path = repo

        _verify_repo(repo_path)

        cmd = [
            "git", "-C", repo_path,
            "log",
            "-p",
            "--no-color",
            # --source makes %S the ref each commit was reached from, i.e. its branch
            "--source",
            "--format=COMMIT_START|%H|%an|%ai|%S|%s",
            *range_args,
            "--",
        ]

        raw = _run(cmd)
        remotes = _run(["git", "-C", repo_path, "remote"]).split()
        return _parse_log(raw, remotes)

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _day_bound(date: str, time: str) -> str:
    """
    Pin a plain YYYY-MM-DD date to a time of day. Git otherwise reads a bare
    date as that day at the *current* time, so From == To gave an empty range
    and commits late on the end date were dropped.
    """
    return f"{date} {time}" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else date


def _verify_repo(path: str) -> None:
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--git-dir"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ValueError(f"Not a valid git repository: {path}")


def _clone(clone_url: str, dest: str, repo: str, token: Optional[str]) -> None:
    # --depth implies --single-branch (default branch only), so opt out to get every branch.
    result = subprocess.run(
        ["git", "clone", "--bare", "--filter=blob:none", f"--depth={_CLONE_DEPTH}",
         "--no-single-branch", clone_url, dest],
        capture_output=True, text=True, env=_GIT_ENV,
    )
    if result.returncode == 0:
        return

    stderr = result.stderr.replace(token, "***") if token else result.stderr
    if _AUTH_FAILURE_PATTERNS.search(stderr):
        if repo.startswith("git@"):
            raise RepoAccessError(
                "SSH access to this repository was denied. Make sure your SSH key is added to your "
                "git host, or use the HTTPS URL together with a Personal Access Token."
            )
        if token:
            raise RepoAccessError(
                "Couldn't access this repository with the Personal Access Token provided. Check that "
                "the token is correct, hasn't expired, and has read access to this repository."
            )
        raise RepoAccessError(
            "This repository appears to be private (or the URL is wrong). Add a Personal Access "
            "Token in the field above and try again."
        )
    raise RuntimeError(f"git clone failed for {repo}\n{stderr}")


def _complete_history(repo_path: str, since: str, token: Optional[str]) -> None:
    """
    Deepen the shallow clone until no cut-off point falls inside the date range.

    A commit at the cut-off has no parent in the clone, so it would be missing
    its predecessors (lost commits on busy repos) and its diff would list every
    file in the repo as added (inflated stats).
    """
    for _ in range(_MAX_DEEPEN_ROUNDS):
        shallow_file = os.path.join(repo_path, "shallow")
        if not os.path.exists(shallow_file):
            return  # whole history fetched
        with open(shallow_file) as f:
            boundaries = f.read().split()
        in_range = _run(["git", "-C", repo_path, "log", "--no-walk", "--format=%H",
                         f"--since={since}", *boundaries, "--"]).split()
        if not in_range:
            return
        _fetch(repo_path, [f"--deepen={_CLONE_DEPTH}", "origin"], token)


def _prefetch_blobs(repo_path: str, range_args: list[str], token: Optional[str]) -> None:
    """
    Download every file version the diffs need in one request.

    Without this, `git log -p` on a blobless clone fetches blobs one commit at a
    time: minutes on busy repos, and on some hosts it aborts with a "promisor
    remote" error. `--raw` compares trees only, so listing the ids is free.
    """
    raw = _run(["git", "-C", repo_path, "log", "--raw", "--no-abbrev", "--no-renames",
                "--format=", *range_args, "--"])
    blobs = set()
    for line in raw.splitlines():
        # :<old mode> <new mode> <old id> <new id> <status>\t<path>
        if not line.startswith(":"):
            continue
        old_mode, new_mode, old_id, new_id = line[1:].split("\t")[0].split()[:4]
        for mode, oid in ((old_mode, old_id), (new_mode, new_id)):
            if mode != "160000" and set(oid) != {"0"}:  # skip submodule pointers and "no file"
                blobs.add(oid)
    if blobs:
        # Best effort: if the host refuses, `git log -p` still fetches on demand
        _fetch(repo_path, ["--stdin", "origin"], token, stdin="\n".join(sorted(blobs)), check=False)


def _fetch(repo_path: str, args: list[str], token: Optional[str],
           stdin: Optional[str] = None, check: bool = True) -> None:
    result = subprocess.run(
        ["git", "-C", repo_path, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "-q",
         "--no-tags", "--no-write-fetch-head", "--filter=blob:none", *args],
        input=stdin, capture_output=True, text=True, env=_GIT_ENV,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.replace(token, "***") if token else result.stderr
        raise RuntimeError(f"git fetch failed: {' '.join(args)}\n{stderr}")


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def _parse_log(raw: str, remotes: list[str] = ()) -> list[dict]:
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
        parts = header.split("|", 5)
        if len(parts) < 6:
            continue

        _, hash_, author, timestamp, source, message = parts
        diff = "\n".join(lines[1:]).strip()

        # Collect touched file names from diff headers
        files_changed = re.findall(r"^diff --git a/(.+?) b/", diff, re.MULTILINE)

        stats = _parse_diff_stats(diff)
        commits.append({
            "hash": hash_.strip(),
            "author": author.strip(),
            "timestamp": timestamp.strip(),
            "branch": _branch_name(source.strip(), remotes),
            "message": message.strip(),
            "diff": diff,
            "files_changed": files_changed,
            **stats,
        })

    return commits


def _branch_name(source: str, remotes: list[str] = ()) -> str:
    """
    Turn a --source ref into the branch name developers use. Git shortens it
    (refs/heads/x -> x, refs/remotes/origin/x -> origin/x), so strip the
    remote name too.
    """
    source = source.removeprefix("refs/heads/").removeprefix("refs/remotes/")
    for remote in remotes:
        if source.startswith(f"{remote}/"):
            return source.removeprefix(f"{remote}/")
    return source


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
