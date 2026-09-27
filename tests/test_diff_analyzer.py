"""
Tests for backend/diff_analyzer.py — LLM stubbed, so these cost nothing.
"""

import re

from backend.diff_analyzer import _parse_summaries, analyze_commits

MESSAGES = [f"msg {i}" for i in range(1, 11)]


def _commit(i: int) -> dict:
    return {"hash": f"{i:040d}", "message": f"msg {i}", "files_changed": [f"f{i}.py"], "diff": f"+line {i}"}


# ── Parsing ────────────────────────────────────────────────────────────────────

def test_complete_reply_maps_one_to_one():
    reply = "\n".join(f"{i}. Did thing {i}." for i in range(1, 11))
    assert _parse_summaries(reply, MESSAGES) == [f"Did thing {i}." for i in range(1, 11)]


def test_reply_cut_off_mid_sentence_keeps_finished_items_and_falls_back_for_the_rest():
    """The bug from the UI: a 10-commit batch truncated partway through item 7."""
    reply = "\n".join(f"{i}. Did thing {i}." for i in range(1, 7)) + "\n7. Enhanced PDF generation by storing avatar metadata in"

    result = _parse_summaries(reply, MESSAGES)

    assert result[:6] == [f"Did thing {i}." for i in range(1, 7)]
    assert result[6:] == ["msg 7", "msg 8", "msg 9", "msg 10"]   # commit messages, not "(summary unavailable)"
    assert not any(re.match(r"^\d+\.", s) for s in result), "list numbers must not leak into summaries"


def test_intro_line_does_not_shift_summaries():
    reply = "Here are the summaries:\n1. First.\n2. Second.\n3. Third."
    assert _parse_summaries(reply, ["a", "b", "c"]) == ["First.", "Second.", "Third."]


def test_skipped_and_out_of_order_numbers_land_on_the_right_commit():
    reply = "3. Third.\n1. First."
    assert _parse_summaries(reply, ["a", "b", "c"]) == ["First.", "b", "Third."]


def test_alternate_list_styles():
    reply = "1) Paren style.\n**2.** Bold style.\n3.No space."
    assert _parse_summaries(reply, ["a", "b", "c"]) == ["Paren style.", "Bold style.", "No space."]


def test_numbers_beyond_the_batch_and_duplicates_are_ignored():
    reply = "1. First.\n1. Duplicate.\n2. Second.\n9. Hallucinated extra."
    assert _parse_summaries(reply, ["a", "b"]) == ["First.", "Second."]


def test_unnumbered_reply_falls_back_to_messages():
    assert _parse_summaries("I could not summarise these.", ["a", "b"]) == ["a", "b"]


def test_complete_last_item_without_period_is_kept_if_not_last_line():
    reply = "1. Added login form\n2. Fixed crash."
    assert _parse_summaries(reply, ["a", "b"]) == ["Added login form", "Fixed crash."]


# ── Batching and token budget ─────────────────────────────────────────────────

def test_batches_get_enough_output_budget_and_stay_aligned(monkeypatch):
    calls = []

    def fake_generate(prompt, max_tokens=200):
        n = prompt.count("\nCommit ")
        calls.append((n, max_tokens))
        # Summarise each commit by echoing its message, so alignment is checkable
        msgs = re.findall(r"^Message: (.+)$", prompt, re.MULTILINE)
        return "\n".join(f"{i}. Summary of {m}." for i, m in enumerate(msgs, 1))

    monkeypatch.setattr("backend.diff_analyzer.generate", fake_generate)

    commits = [_commit(i) for i in range(1, 13)]   # 12 commits -> batches of 10 and 2
    result = analyze_commits(commits)

    assert sorted(calls) == [(2, 160), (10, 800)]
    assert [c["summary"] for c in result] == [f"Summary of msg {i}." for i in range(1, 13)]
    assert [c["hash"] for c in result] == [c["hash"] for c in commits]
