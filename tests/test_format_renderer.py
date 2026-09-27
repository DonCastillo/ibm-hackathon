"""
Tests for backend/renderers/format_renderer.py — the plan/format.md rules.
The LLM is stubbed, so these check prompt assembly, parsing, limit
enforcement, fallbacks and headers — not writing quality.
"""

import threading

from backend.renderers import format_renderer
from backend.renderers.format_renderer import render_all

REPO = "acme/secret-repo"
PERIOD = "Sep 20, 2026 - Sep 27, 2026"


def _summary(omitted_minor=2):
    return {
        "repo": REPO,
        "period": PERIOD,
        "omitted_minor": omitted_minor,
        "groups": [
            {"theme": "api", "authors": ["Alice"], "commits": [
                {"hash": "a1", "author": "Alice", "message": "m1", "summary": "Added OAuth login to `auth.py`."},
                {"hash": "a2", "author": "Alice", "message": "m2", "summary": "Added rate limiting."},
            ]},
            {"theme": "web", "authors": ["Bob"], "commits": [
                {"hash": "b1", "author": "Bob", "message": "m3", "summary": "Added export button."},
            ]},
        ],
    }


def _stub(monkeypatch, reply_for):
    """reply_for(prompt, audience) -> str. Returns the list of (audience, prompt) calls."""
    calls, lock = [], threading.Lock()

    def fake_generate(prompt, max_tokens=200):
        audience = "client" if "non-technical client" in prompt else "developer"
        with lock:
            calls.append((audience, prompt))
        return reply_for(prompt, audience)

    monkeypatch.setattr(format_renderer, "generate", fake_generate)
    return calls


def _reply(slack="• Shipped OAuth", email="API:\n- Added OAuth", standup="Alice\n- Added OAuth"):
    return f"=== SLACK ===\n{slack}\n=== EMAIL ===\n{email}\n=== STANDUP ===\n{standup}\n"


# ── Prompt assembly ────────────────────────────────────────────────────────────

def test_one_call_per_audience_with_combined_format_and_audience_rules(monkeypatch):
    calls = _stub(monkeypatch, lambda p, a: _reply())

    render_all(_summary())

    assert sorted(a for a, _ in calls) == ["client", "developer"]
    for audience, prompt in calls:
        assert "no more than 6 bullets, each under 15 words" in prompt
        assert "no more than 300 words total" in prompt
        assert "at most 3 short fragments" in prompt
        assert "State WHAT changed, not why it matters" in prompt
        assert PERIOD in prompt
        assert "- [api] (Alice) Added OAuth login to `auth.py`." in prompt
        assert "{{" not in prompt, "unfilled placeholder"
    prompts = dict(calls)
    assert "developer audience" in prompts["developer"] and "non-technical client" not in prompts["developer"]
    assert "never mention file names" in prompts["client"]


# ── Limits from plan/format.md ────────────────────────────────────────────────

def test_slack_is_capped_at_6_bullets_and_bullet_styles_are_normalised(monkeypatch):
    slack = "\n".join(["• one", "- two", "* three", "1. four", "five", "• six", "• seven", "• eight", "• nine"])
    _stub(monkeypatch, lambda p, a: _reply(slack=slack))

    dev, _ = render_all(_summary())

    bullets = [l for l in dev["slack"].splitlines() if l.startswith("• ")]
    assert bullets == ["• one", "• two", "• three", "• four", "• five", "• six"]


def test_standup_keeps_at_most_3_fragments_per_person(monkeypatch):
    standup = "Alice\n- a1\n- a2\n- a3\n- a4\n- a5\n\nBob\n- b1"
    _stub(monkeypatch, lambda p, a: _reply(standup=standup))

    dev, _ = render_all(_summary())

    assert "Alice\n- a1\n- a2\n- a3\n\nBob\n- b1" in dev["standup"]
    assert "a4" not in dev["standup"]


def test_long_email_is_retried_once_then_trimmed_by_section(monkeypatch):
    long_section = "Section:\n" + "word " * 250
    email = f"{long_section}\n\n{long_section}\n\nLast:\n- tail"
    calls = _stub(monkeypatch, lambda p, a: _reply(email=email))

    dev, client = render_all(_summary())

    assert [a for a, _ in calls].count("developer") == 2, "one retry per over-long email"
    assert [a for a, _ in calls].count("client") == 2
    body = dev["email"].split("Hi team,", 1)[1]
    assert len(body.split()) <= 400 + 10   # body within limit (+ sign-off/note lines)
    assert "tail" not in body


def test_short_email_is_not_retried(monkeypatch):
    calls = _stub(monkeypatch, lambda p, a: _reply())
    render_all(_summary())
    assert len(calls) == 2


# ── Fallbacks ─────────────────────────────────────────────────────────────────

def test_missing_section_falls_back_for_developer_and_is_withheld_for_client(monkeypatch):
    _stub(monkeypatch, lambda p, a: "=== SLACK ===\n• ok\n=== EMAIL ===\nAPI:\n- ok")  # no STANDUP

    dev, client = render_all(_summary())

    assert "Alice\n- Added OAuth login to `auth.py`.\n- Added rate limiting." in dev["standup"]
    assert "couldn't be generated" in client["standup"]
    assert "auth.py" not in client["standup"]


def test_llm_failure_never_breaks_the_report(monkeypatch):
    def boom(prompt, max_tokens=200):
        raise RuntimeError("LLM down")
    monkeypatch.setattr(format_renderer, "generate", boom)

    dev, client = render_all(_summary())

    assert "• Added export button." in dev["slack"]
    assert all("couldn't be generated" in client[f] for f in ("slack", "email", "standup"))


# ── Headers and client privacy ────────────────────────────────────────────────

def test_developer_headers_show_repo_period_and_minor_note(monkeypatch):
    _stub(monkeypatch, lambda p, a: _reply())

    dev, _ = render_all(_summary(omitted_minor=2))

    assert dev["slack"].startswith(f"*📋 Standup Sync — `{REPO}`*\n_{PERIOD}_")
    assert dev["email"].startswith(f"Subject: Project Update — {REPO}\nPeriod: {PERIOD}")
    assert dev["email"].rstrip().endswith("Best,\nStandup Sync")
    assert dev["standup"].startswith(f"STANDUP NOTES — {REPO}\n{PERIOD}")
    for text in dev.values():
        assert "+ 2 minor updates (small fixes, docs, tweaks) not shown" in text


def test_client_versions_never_show_repo_name_or_minor_note(monkeypatch):
    _stub(monkeypatch, lambda p, a: _reply())

    _, client = render_all(_summary(omitted_minor=2))

    assert client["slack"].startswith(f"*📢 Product Update*\n_{PERIOD}_")
    assert client["email"].startswith(f"Subject: Product Update — {PERIOD}")
    assert client["standup"].startswith(f"PRODUCT UPDATE\n{PERIOD}")
    for text in client.values():
        assert REPO not in text and "secret-repo" not in text
        assert "not shown" not in text
