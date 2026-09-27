"""
Tests for backend/noise_filter.py — pure function, no git or LLM needed.
"""

from backend.noise_filter import filter_commits


def _c(message: str, files=("app.py",), diff="+new line\n-old line") -> dict:
    return {"message": message, "files_changed": list(files), "diff": diff}


def _kept(commits):
    return [c["message"] for c in filter_commits(commits)]


def test_revert_and_the_commit_it_reverts_are_both_dropped():
    commits = [
        _c("Add dark mode"),
        _c('Revert "Add dark mode"'),
        _c("Add export button"),
    ]
    assert _kept(commits) == ["Add export button"]


def test_hand_written_reverts_and_undos_are_dropped():
    commits = [_c("revert login tweak"), _c("Undo last change"), _c("Add search")]
    assert _kept(commits) == ["Add search"]


def test_words_containing_revert_are_not_mistaken_for_reverts():
    assert _kept([_c("Add reverted-state badge"), _c("Handle undoable actions")]) == [
        "Add reverted-state badge", "Handle undoable actions",
    ]


def test_spacing_only_changes_are_dropped():
    reindent = "+    x = 1\n+    y = 2\n-  x = 1\n-  y = 2"
    trailing = "+return total\n-return total   "
    blank_lines = "+\n+   \n-\n"
    assert _kept([_c("Reindent", diff=reindent), _c("Trim", diff=trailing), _c("Blank", diff=blank_lines)]) == []


def test_spacing_plus_a_real_change_is_kept():
    diff = "+    x = 1\n+    y = 3\n-  x = 1\n-  y = 2"
    assert _kept([_c("Reindent and fix y", diff=diff)]) == ["Reindent and fix y"]


def test_lock_and_generated_files_only_are_dropped():
    commits = [_c("Bump deps", files=("package-lock.json",)), _c("Rebuild", files=("dist/app.min.js",))]
    assert _kept(commits) == []


def test_real_change_is_kept():
    assert _kept([_c("Add OAuth login")]) == ["Add OAuth login"]
