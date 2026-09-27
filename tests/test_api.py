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


# ── Major-only reports ─────────────────────────────────────────────────────────

def test_reports_list_only_major_updates(git_repo, fake_llm):
    git_repo.commit("Add payments API", {"api/pay.py": "def pay(): pass\n"}, author="Alice")
    git_repo.commit("minor: fix typo in docs", {"docs/readme.md": "hello\n"}, author="Bob")
    git_repo.commit("minor: rename variable", {"api/util.py": "x = 1\n"}, author="Bob")

    result = last(generate(repo=str(git_repo.path), since=WIDE), "result")

    for fmt in ("slack", "email", "standup"):
        text = result["formats"][fmt]
        assert "Summary of Add payments API." in text
        assert "typo" not in text and "rename" not in text
        assert "+ 2 minor updates (small fixes, docs, tweaks) not shown" in text
    # Both render calls (developer + client) are only given the major update
    render_prompts = [p for p in fake_llm if "=== SLACK ===" in p]
    assert len(render_prompts) == 2
    for prompt in render_prompts:
        assert "Add payments API" in prompt and "typo" not in prompt
    # Client versions: rendered with the client audience, no repo path, no minor-update note
    for text in result["formats_client"].values():
        assert "Client: Summary of Add payments API." in text
        assert str(git_repo.path) not in text and "not shown" not in text
    # Stats and the raw log still cover everything
    stats = result["summary"]["author_stats"]
    # Highlights count only what made it into the reports; commits count everything
    assert (stats["Alice"]["highlights"], stats["Alice"]["commits"]) == (1, 1)
    assert (stats["Bob"]["highlights"], stats["Bob"]["commits"]) == (0, 2)
    assert set(stats["Bob"]) == {"highlights", "commits", "branches"}
    assert len(result["summary"]["raw_log"]) == 3


def test_all_minor_period_still_shows_its_updates(git_repo, fake_llm):
    git_repo.commit("minor: fix typo", {"a.md": "a\n"})
    git_repo.commit("minor: bump version", {"b.txt": "b\n"})

    result = last(generate(repo=str(git_repo.path), since=WIDE), "result")

    slack = result["formats"]["slack"]
    assert "Summary of minor: fix typo." in slack and "Summary of minor: bump version." in slack
    assert "not shown" not in slack


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


def test_unexpected_error_is_one_readable_line_not_a_traceback(monkeypatch, fake_llm):
    def crash(*args, **kwargs):
        raise RuntimeError("Missing ANTHROPIC_API_KEY. Fill in your .env file.\nsecond line of detail")

    monkeypatch.setattr("backend.main.extract_commits", crash)

    detail = last(generate(repo="/anything", since=WIDE), "error")["detail"]

    assert detail == ("Something went wrong while generating the report: "
                      "Missing ANTHROPIC_API_KEY. Fill in your .env file.")
    assert "Traceback" not in detail and "second line" not in detail


def test_missing_repo_field_is_rejected():
    assert client.post("/api/generate", json={"since": WIDE}).status_code == 422


# ── Pages ─────────────────────────────────────────────────────────────────────

def test_app_page_is_served_at_standup_and_root():
    for path in ("/standup", "/"):
        res = client.get(path)
        assert res.status_code == 200
        assert 'id="generate-btn"' in res.text


def test_static_assets_are_served():
    for asset in ("theme.css", "standup.css", "app.js", "logo.svg"):
        assert client.get(f"/static/{asset}").status_code == 200
