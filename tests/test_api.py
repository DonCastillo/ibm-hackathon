"""
Offline end-to-end tests for POST /api/generate (SSE stream), with the LLM stubbed.
"""

import json

import pytest
from fastapi.testclient import TestClient

from backend.git_extractor import RepoAccessError
from backend.main import app

client = TestClient(app)
WIDE = "2000-01-01"


def generate(**body) -> list[tuple[str, dict]]:
    """POST to /api/generate and return the SSE stream as [(event, data), ...]."""
    res = client.post("/api/generate", json=body)
    assert res.status_code == 200
    events = []
    for frame in res.text.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.strip().splitlines() if ": " in line)
        if "event" in lines:
            events.append((lines["event"], json.loads(lines["data"])))
    return events


def last(events, name):
    return next(data for event, data in reversed(events) if event == name)


# ── Happy path ─────────────────────────────────────────────────────────────────

def test_full_pipeline_across_branches(git_repo, fake_llm):
    git_repo.commit("Set up API", {"api/server.py": "app = 1\n"}, author="Alice")
    git_repo.branch("feature/login")
    git_repo.commit("Add login endpoint", {"api/login.py": "def login(): pass\n"}, author="Bob")
    git_repo.checkout("main")

    events = generate(repo=str(git_repo.path), since=WIDE)
    names = [e for e, _ in events]

    assert "error" not in names, last(events, "error")
    assert names[0] == "progress" and "raw_log" in names and names[-1] == "result"

    raw_log = last(events, "raw_log")["lines"]
    assert any("[feature/login] Bob — Add login endpoint" in line for line in raw_log)
    assert any("[main] Alice — Set up API" in line for line in raw_log)

    result = last(events, "result")
    stats = result["summary"]["author_stats"]
    assert stats["Bob"]["branches"] == ["feature/login"]
    assert stats["Alice"]["branches"] == ["main"]
    assert stats["Bob"]["commits"] == 1
    for fmt in ("slack", "email", "standup"):
        assert result["formats"][fmt]
        assert result["formats_client"][fmt]
    assert fake_llm, "LLM stub should have been called"


# ── Error events ───────────────────────────────────────────────────────────────

def test_no_commits_in_range(git_repo, fake_llm):
    git_repo.commit("Ancient", {"a.txt": "a\n"}, date="2015-01-01T12:00:00")

    events = generate(repo=str(git_repo.path), since="7 days ago")

    assert "No commits found" in last(events, "error")["detail"]
    assert not fake_llm


def test_empty_repo(git_repo, fake_llm):
    events = generate(repo=str(git_repo.path), since=WIDE)
    assert "No commits found" in last(events, "error")["detail"]


def test_only_lock_file_commits_are_filtered_out(git_repo, fake_llm):
    git_repo.commit("Bump deps", {"package-lock.json": "{}\n"})
    git_repo.commit("Rebuild", {"dist/app.min.js": "x\n"})

    events = generate(repo=str(git_repo.path), since=WIDE)

    assert "All commits were filtered out" in last(events, "error")["detail"]
    assert not fake_llm


def test_invalid_local_path(tmp_path, fake_llm):
    events = generate(repo=str(tmp_path / "nope"), since=WIDE)
    assert "Not a valid git repository" in last(events, "error")["detail"]


def test_private_repo_error_is_flagged_for_the_ui(monkeypatch, fake_llm):
    def refuse(*args, **kwargs):
        raise RepoAccessError("This repository appears to be private (or the URL is wrong).")

    monkeypatch.setattr("backend.main.extract_commits", refuse)

    error = last(generate(repo="https://github.com/org/private", since=WIDE), "error")

    assert error["code"] == "repo_access"   # the UI highlights the token field on this code
    assert "private" in error["detail"]
    assert "Traceback" not in error["detail"]


def test_missing_repo_field_is_rejected():
    assert client.post("/api/generate", json={"since": WIDE}).status_code == 422
