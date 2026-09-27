"""
Offline tests for backend/git_extractor.py — run against throwaway local repos.
"""

import subprocess
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend import git_extractor
from backend.git_extractor import RepoAccessError, _inject_token, extract_commits

WIDE = "2000-01-01"


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%S")


# ── All-branches extraction ────────────────────────────────────────────────────

def test_captures_commits_on_unmerged_feature_branch(git_repo):
    git_repo.commit("Initial setup", {"app.py": "print(1)\n"}, author="Alice")
    git_repo.branch("feature/login")
    git_repo.commit("Add login form", {"login.py": "form()\n"}, author="Bob")
    git_repo.checkout("main")

    commits = extract_commits(str(git_repo.path), WIDE)

    by_msg = {c["message"]: c for c in commits}
    assert set(by_msg) == {"Initial setup", "Add login form"}
    assert by_msg["Add login form"]["branch"] == "feature/login"
    assert by_msg["Add login form"]["author"] == "Bob"
    assert by_msg["Initial setup"]["branch"] == "main"


def test_commit_shared_by_several_branches_is_counted_once(git_repo):
    git_repo.commit("Shared base", {"a.txt": "a\n"})
    git_repo.branch("feature/one")
    git_repo.commit("One", {"one.txt": "1\n"})
    git_repo.checkout("main")
    git_repo.branch("feature/two")
    git_repo.commit("Two", {"two.txt": "2\n"})

    commits = extract_commits(str(git_repo.path), WIDE)

    messages = [c["message"] for c in commits]
    assert sorted(messages) == ["One", "Shared base", "Two"]


def test_merge_commits_are_excluded_but_merged_work_is_kept(git_repo):
    git_repo.commit("Base", {"a.txt": "a\n"})
    git_repo.branch("feature/x")
    git_repo.commit("Feature work", {"x.txt": "x\n"}, author="Bob")
    git_repo.checkout("main")
    git_repo.merge("feature/x")

    messages = [c["message"] for c in extract_commits(str(git_repo.path), WIDE)]

    assert "Feature work" in messages
    assert not any(m.startswith("Merge") for m in messages)


def test_remote_only_branches_of_a_local_clone_are_captured(git_repo, tmp_path):
    git_repo.commit("Base", {"a.txt": "a\n"})
    git_repo.branch("feature/remote-only")
    git_repo.commit("Pushed but never checked out locally", {"r.txt": "r\n"}, author="Carol")
    git_repo.checkout("main")

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(git_repo.path), str(clone)], check=True)

    commits = extract_commits(str(clone), WIDE)

    remote_only = [c for c in commits if c["author"] == "Carol"]
    assert len(remote_only) == 1
    # "origin/" prefix is stripped so the tag matches the branch name developers use
    assert remote_only[0]["branch"] == "feature/remote-only"
    assert sorted(c["message"] for c in commits) == ["Base", "Pushed but never checked out locally"]


# ── Date ranges ────────────────────────────────────────────────────────────────

def test_relative_preset_excludes_older_commits(git_repo):
    git_repo.commit("Old work", {"a.txt": "a\n"}, date=_days_ago(40))
    git_repo.commit("Recent work", {"b.txt": "b\n"}, date=_days_ago(2))

    messages = [c["message"] for c in extract_commits(str(git_repo.path), "7 days ago")]

    assert messages == ["Recent work"]


def test_custom_range_respects_since_and_until(git_repo):
    git_repo.commit("Before", {"a.txt": "a\n"}, date="2026-09-01T12:00:00")
    git_repo.commit("Inside", {"b.txt": "b\n"}, date="2026-09-10T12:00:00")
    git_repo.commit("After", {"c.txt": "c\n"}, date="2026-09-20T12:00:00")

    commits = extract_commits(str(git_repo.path), "2026-09-05", "2026-09-15")

    assert [c["message"] for c in commits] == ["Inside"]


def test_single_day_range_includes_that_days_commits(git_repo):
    """The UI sends From == To (plain dates) for a one-day range."""
    git_repo.commit("Morning", {"a.txt": "a\n"}, date="2026-09-10T09:00:00")
    git_repo.commit("Evening", {"b.txt": "b\n"}, date="2026-09-10T21:00:00")

    commits = extract_commits(str(git_repo.path), "2026-09-10", "2026-09-10")

    assert sorted(c["message"] for c in commits) == ["Evening", "Morning"]


def test_custom_range_includes_commits_late_on_the_end_date(git_repo):
    git_repo.commit("Late on the last day", {"a.txt": "a\n"}, date="2026-09-15T23:30:00")

    commits = extract_commits(str(git_repo.path), "2026-09-10", "2026-09-15")

    assert [c["message"] for c in commits] == ["Late on the last day"]


def test_no_commits_in_range_returns_empty_list(git_repo):
    git_repo.commit("Ancient", {"a.txt": "a\n"}, date="2015-01-01T12:00:00")
    assert extract_commits(str(git_repo.path), "7 days ago") == []


# ── Local path edge cases ──────────────────────────────────────────────────────

def test_empty_repo_returns_no_commits(git_repo):
    assert extract_commits(str(git_repo.path), WIDE) == []


def test_non_repo_directory_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Not a valid git repository"):
        extract_commits(str(tmp_path), WIDE)


def test_missing_path_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Not a valid git repository"):
        extract_commits(str(tmp_path / "does-not-exist"), WIDE)


# ── Diff stats and parsing ─────────────────────────────────────────────────────

def test_diff_stats_count_added_modified_and_deleted_files(git_repo):
    git_repo.commit("Add files", {"keep.txt": "one\ntwo\n", "gone.txt": "bye\n"})
    git_repo.commit("Change and add", {"keep.txt": "one\nTWO\nthree\n", "new.txt": "hi\n"})
    git_repo.delete("gone.txt", "Remove file")

    by_msg = {c["message"]: c for c in extract_commits(str(git_repo.path), WIDE)}

    change = by_msg["Change and add"]
    assert (change["files_added"], change["files_modified"], change["files_deleted"]) == (1, 1, 0)
    assert change["lines_added"] == 3      # TWO, three, hi
    assert change["lines_deleted"] == 1    # two
    assert change["lines_updated"] == 1    # two -> TWO
    assert sorted(change["files_changed"]) == ["keep.txt", "new.txt"]
    assert by_msg["Remove file"]["files_deleted"] == 1


def test_file_containing_the_log_separator_is_not_split_into_fake_commits(git_repo):
    """Regression: this repo's own git_extractor.py contains the separator text,
    which produced fake commits with hash '%H' and source code as the branch."""
    source = 'fmt = "--format=COMMIT_START|%H|%an|%ai|%S|%s"\nparts = header.split("|")\n'
    git_repo.commit("Add extractor", {"extractor.py": source}, author="Alice")

    commits = extract_commits(str(git_repo.path), WIDE)

    assert len(commits) == 1
    c = commits[0]
    assert (len(c["hash"]), c["author"], c["branch"]) == (40, "Alice", "main")
    assert "COMMIT_START|%H" in c["diff"]          # the diff is kept whole
    assert c["lines_added"] == 2


def test_commit_message_containing_pipes_is_preserved(git_repo):
    git_repo.commit("Fix a | b | c parsing", {"a.txt": "a\n"})
    assert extract_commits(str(git_repo.path), WIDE)[0]["message"] == "Fix a | b | c parsing"


# ── Clone error handling (subprocess stubbed — no network) ─────────────────────

def _fake_clone_failure(monkeypatch, stderr: str):
    monkeypatch.setattr(
        git_extractor.subprocess, "run",
        lambda *a, **kw: SimpleNamespace(returncode=128, stdout="", stderr=stderr),
    )


@pytest.mark.parametrize("stderr", [
    "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
    "remote: Repository not found.\nfatal: repository 'https://github.com/x/y/' not found",
    "fatal: Authentication failed for 'https://gitlab.com/x/y.git/'",
    "remote: HTTP Basic: Access denied",
    "fatal: unable to access '...': The requested URL returned error: 403",
])
def test_private_repo_without_token_asks_for_token(monkeypatch, stderr):
    _fake_clone_failure(monkeypatch, stderr)
    with pytest.raises(RepoAccessError, match="Personal Access Token in the field above"):
        extract_commits("https://github.com/org/private-repo", WIDE)


def test_rejected_token_gets_token_specific_message(monkeypatch):
    _fake_clone_failure(monkeypatch, "remote: Invalid username or token.\nfatal: Authentication failed")
    with pytest.raises(RepoAccessError, match="with the Personal Access Token provided"):
        extract_commits("https://github.com/org/private-repo", WIDE, token="ghp_bad")


def test_ssh_permission_denied_gets_ssh_message(monkeypatch):
    _fake_clone_failure(monkeypatch, "git@github.com: Permission denied (publickey).")
    with pytest.raises(RepoAccessError, match="SSH access"):
        extract_commits("git@github.com:org/repo.git", WIDE)


def test_non_auth_clone_failure_is_runtime_error_without_leaking_token(monkeypatch):
    secret = "ghp_supersecret123"
    _fake_clone_failure(monkeypatch, f"fatal: unable to access 'https://{secret}@nohost.example/r/': Could not resolve host")
    with pytest.raises(RuntimeError) as exc:
        extract_commits("https://nohost.example/r", WIDE, token=secret)
    assert not isinstance(exc.value, RepoAccessError)
    assert secret not in str(exc.value)


@pytest.mark.parametrize("url, expected", [
    ("https://github.com/o/r.git",         "https://TOK@github.com/o/r.git"),
    ("https://gitlab.com/o/r",             "https://oauth2:TOK@gitlab.com/o/r"),
    ("https://bitbucket.org/o/r",          "https://x-token-auth:TOK@bitbucket.org/o/r"),
    ("https://dev.azure.com/o/p/_git/r",   "https://pat:TOK@dev.azure.com/o/p/_git/r"),
    ("https://old@github.com/o/r",         "https://TOK@github.com/o/r"),
    ("https://git.example.com:8443/o/r",   "https://TOK@git.example.com:8443/o/r"),
])
def test_token_injection_per_host(url, expected):
    assert _inject_token(url, "TOK") == expected


# ── Remote clone completeness (file:// remote — no network) ────────────────────

def test_shallow_clone_is_deepened_and_prefetched_so_nothing_is_missing(git_repo, monkeypatch):
    """
    A repo busier than the clone depth: 30 daily commits, depth 5. Every commit
    in range must be returned, the oldest must not show the whole tree as
    "added", and git log must not need to fetch anything lazily.
    """
    for day in range(1, 31):
        git_repo.commit(f"Day {day}", {f"day{day}.txt": f"{day}\n"}, date=f"2026-09-{day:02d}T12:00:00")
    # Let the file:// "server" honour partial clone and fetch-by-blob-id
    git_repo._git("config", "uploadpack.allowFilter", "true")
    git_repo._git("config", "uploadpack.allowAnySHA1InWant", "true")

    monkeypatch.setattr(git_extractor, "_CLONE_DEPTH", 5)
    monkeypatch.setenv("GIT_NO_LAZY_FETCH", "1")  # any blob the prefetch missed fails loudly

    commits = extract_commits(f"file://{git_repo.path}", "2026-09-10", "2026-09-30")

    assert sorted(c["message"] for c in commits) == sorted(f"Day {d}" for d in range(10, 31))
    for c in commits:
        assert (c["files_added"], c["files_modified"]) == (1, 0), c["message"]
