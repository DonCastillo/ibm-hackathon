# Developer Stats UI — Plan

## Top-Level Overview

Add a per-developer stats table to the Standup Sync UI that shows — for the given repo and date range — each developer who pushed commits, with columns for: commits, files added, files deleted, files modified, lines added, lines deleted, and lines updated (approximated as per-hunk minimum of added/deleted lines in each diff hunk).

The stats table appears **above** the existing "Before vs. After" card in the results section. It is sortable: default sort is by commit count (descending), with a toggle to sort alphabetically by developer name.

All stat computation is deterministic (no LLM calls). The `diff` field already present on each commit contains the full `git log -p` patch — we parse it in the backend and aggregate by author, then pass the aggregated data to the frontend in the existing `result` SSE event payload.

---

## Sub-Tasks

---

### Sub-Task 1 — Parse diff stats per commit in `git_extractor.py`

**Status:** `[ ] pending`

**Intent**
Add a pure function `_parse_diff_stats(diff: str) -> dict` to [`backend/git_extractor.py`](../backend/git_extractor.py) that reads the raw patch text of a single commit and returns file-level and line-level counts. Call it inside `_parse_log()` so every commit dict gets the new fields.

**Expected Outcomes**
- Every commit dict returned by `extract_commits()` has five new integer fields: `files_added`, `files_deleted`, `files_modified`, `lines_added`, `lines_deleted`, `lines_updated`.
- The function is a pure, standalone function with no side effects and no LLM calls.
- Existing fields (`hash`, `author`, `timestamp`, `message`, `diff`, `files_changed`) are unchanged.

**Todo List**
1. In `_parse_diff_stats(diff)`:
   - Split diff on `diff --git` boundaries to get one block per file.
   - For each block: classify as **added** if `--- /dev/null` is present, **deleted** if `+++ /dev/null` is present, else **modified**.
   - Count `lines_added`: lines beginning with `+` that are NOT the `+++ b/...` header.
   - Count `lines_deleted`: lines beginning with `-` that are NOT the `--- a/...` header.
   - Compute `lines_updated`: iterate over diff hunks (sections between `@@` markers); for each hunk, `min(hunk_plus_count, hunk_minus_count)` — sum these across all hunks. This is the per-hunk approximation of "updated" lines.
2. In `_parse_log()`, after building the commit dict, call `_parse_diff_stats(diff)` and merge the result into the commit dict.

**Relevant Context**
- File: [`backend/git_extractor.py`](../backend/git_extractor.py)
- The `diff` variable is already populated at line 101 as `"\n".join(lines[1:]).strip()`.
- The commit dict is assembled at lines 106–113.

---

### Sub-Task 2 — Aggregate per-author stats in `summarizer.py`

**Status:** `[ ] pending`

**Intent**
In [`backend/summarizer.py`](../backend/summarizer.py), aggregate the per-commit stat fields across all commits for each author and add an `author_stats` key to the returned summary object. This is consumed by the frontend to render the table.

**Expected Outcomes**
- The summary object returned by `build_summary()` includes a new `author_stats` key.
- Shape:
  ```json
  {
    "author_stats": {
      "Alice": {
        "commits": 3,
        "files_added": 5,
        "files_deleted": 1,
        "files_modified": 12,
        "lines_added": 220,
        "lines_deleted": 45,
        "lines_updated": 30
      }
    }
  }
  ```
- Aggregation uses `raw_commits` (the full unfiltered list) so noise-filtered commits still appear in stats. Wait — reconsider: use the **filtered** commits passed through the pipeline (the same commits that reach analysis), since those represent real signal. The `raw_commits` parameter is already the post-filter list at the call site in `main.py`.

**Todo List**
1. In `build_summary()`, add an aggregation loop over `raw_commits`.
2. For each commit, accumulate each of the 6 stat fields under the commit's `author` key. Initialize missing authors on first encounter.
3. Add `"author_stats": author_stats` to the returned dict.

**Relevant Context**
- File: [`backend/summarizer.py`](../backend/summarizer.py)
- `raw_commits` is already passed in — it is the filtered commit list from `main.py` (see call site in `backend/main.py`).
- The 6 new fields (`files_added`, `files_deleted`, `files_modified`, `lines_added`, `lines_deleted`, `lines_updated`) are added in Sub-Task 1.

---

### Sub-Task 3 — Render Developer Stats table in `frontend/index.html`

**Status:** `[ ] pending`

**Intent**
Add a new "Developer Stats" results card to the frontend that renders `author_stats` as a sortable table. The card is placed **above** the existing "Before vs. After" card. Default sort: by commit count descending. Secondary sort: alphabetical by name (toggled via a sort button).

**Expected Outcomes**
- A new card appears in the results section, above "Before vs. After", once results arrive.
- Table columns: Developer | Commits | Files Added | Files Deleted | Files Modified | Lines Added | Lines Deleted | Lines Updated.
- Default sort: highest commit count first.
- A "Sort A→Z" button (toggles to "Sort by Commits") re-sorts the table rows in place without re-fetching.
- Numbers are right-aligned in the table; developer name is left-aligned.
- Added/deleted columns use subtle green/red coloring to make the data scannable at a glance.
- If `author_stats` is empty or missing, the card is hidden (same pattern as the blockers card).

**Todo List**
1. Add CSS for the stats table: `.stats-table` — full width, clean borders, right-aligned number cells, color classes `.added` (green), `.deleted` (red), `.updated` (muted blue).
2. Add the HTML card skeleton above the "Before vs. After" card inside `#results`:
   ```html
   <div id="dev-stats-section" class="hidden card">
     <h2>👥 Developer Stats
       <button id="sort-toggle-btn">Sort A→Z</button>
     </h2>
     <table class="stats-table" id="dev-stats-table">...</table>
   </div>
   ```
3. In `showResult(data)`, call a new `renderDevStats(data.summary.author_stats)` function.
4. `renderDevStats(authorStats)`:
   - Build a rows array from `Object.entries(authorStats)`.
   - Sort by commit count descending by default.
   - Render `<tr>` elements into `#dev-stats-table tbody`.
   - Show/hide the section card.
5. Add sort toggle button logic: clicking "Sort A→Z" re-sorts rows alphabetically and relabels the button to "Sort by Commits"; clicking again reverts.

**Relevant Context**
- File: [`frontend/index.html`](../frontend/index.html)
- The "Before vs. After" card starts at line 124. The new card goes before it, inside `#results` (line 121).
- Pattern for show/hide: `blockersSection.classList.remove('hidden')` — same approach.
- `showResult(data)` is at line 211 — add the `renderDevStats` call there.

---

## Implementation Notes

- `lines_updated` approximation: for each `@@` hunk in the diff, `lines_updated += min(plus_lines_in_hunk, minus_lines_in_hunk)`. This avoids double-counting and represents lines that were truly changed in place rather than purely added or removed.
- Sub-Tasks must be done in order: 1 → 2 → 3 (each feeds the next).
- No new dependencies, no new endpoints, no schema changes to the SSE event format beyond adding `author_stats` to the existing `summary` object.
