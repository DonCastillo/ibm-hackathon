# architecture.md — Standup Sync (single-repo)

## Overview

One repo, one pass, one shared summary object rendered three ways.

```
Repo (local path or URL)
        │
        ▼
┌───────────────────┐
│ Git extraction     │  git log -p --since=<range>
└───────────────────┘
        │  raw commits + diffs
        ▼
┌───────────────────┐
│ Noise filter        │  drop merges, lockfiles, formatting-only
└───────────────────┘
        │  filtered commits
        ▼
┌───────────────────┐
│ Diff analysis (LLM) │  per-commit / batched "what changed & why"
└───────────────────┘
        │  per-commit summaries
        ▼
┌───────────────────┐
│ Grouping            │  by touched dir/file, by author
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Summary object (JSON)│  ← single source of truth for rendering
└───────────────────┘
        │
        ▼
┌────────────────────────────────────┐
│ Format router                        │
│  ├─ Slack renderer                   │
│  ├─ Email renderer                   │
│  └─ Standup renderer                 │
└────────────────────────────────────┘
        │
        ▼
   Web UI (input form + before/after view + format toggle)
```

## Components

### 1. Git extraction
- Input: repo path or URL, date range (default: last 24h).
- If URL, `git clone --depth=<N>` into a temp dir; if local path, use as-is.
- Run `git log --since="<range>" -p --no-color` (or `--numstat` first to
  scope which commits to fetch full diffs for, if performance matters).
- Output: list of `{hash, author, timestamp, message, diff, files_changed}`.

### 2. Noise filter (pure function, no LLM)
- Drop commits where:
  - it's a merge commit (`git log --no-merges` handles most of this upstream)
  - all changed files match a lockfile/generated-file pattern
    (`package-lock.json`, `yarn.lock`, `*.min.js`, `dist/**`, etc.)
  - the diff only changes spacing (indentation, trailing spaces, blank lines)
  - it's a revert — together with the commit it reverts
- Output: same shape, filtered list.
- Full rules: [`filtering.md`](filtering.md).

### 3. Diff analysis (LLM — Bob / underlying model)
- Batch filtered commits (e.g. 5–10 per call to control token usage).
- Prompt asks for one 8–15-word sentence per commit describing what changed
  (not why), read from the diff rather than the commit message, and tagged
  `[MAJOR]` or `[MINOR]`. Only major commits go into the reports.
- Output: `summary` and `impact` ("major" / "minor") merged back onto the
  commit objects.
- Major/minor definitions and safety nets: [`filtering.md`](filtering.md).

### 4. Grouping (pure function, no LLM)
- Group commits by their most common top-level touched directory (or file,
  for small repos).
- Within each group, keep author breakdown.
- Output: `{theme: string, commits: [...], authors: [...]}[]`.

### 5. Blocker detection — removed
Reports cover accomplishments only. Blocker detection (files touched 3+
times, revert/wip messages) was dropped; reverts are instead removed by the
noise filter together with the commit they revert, and minor changes are
tagged by the LLM and left out of reports.

### 6. Summary object (the contract between backend and renderers)
```json
{
  "repo": "string",
  "range": { "since": "ISO date", "until": "ISO date" },
  "groups": [
    {
      "theme": "auth",
      "commits": [{ "hash": "...", "summary": "...", "author": "..." }],
      "authors": ["..."]
    }
  ],
  "omitted_minor": 0
}
```
This is the only object the format renderers read. Nothing downstream ever
touches raw git data again.

### 7. Format renderers (templates over the summary object)
- **Slack**: short bullets per theme, emoji allowed.
- **Email**: subject line + grouped sections by theme, slightly more formal
  tone.
- **Standup**: grouped by author instead of theme — "what I did" per person.
- All three are pure string-templating functions: `render(summary) -> string`.
  No LLM call needed here if the group/commit summaries are already good
  plain English — if the writing needs more polish per format, one extra LLM
  pass per format is acceptable but is a stretch, not core.

### 8. Web UI
- Single page: repo input, date range picker, "Generate" button.
- Results view: tabs or toggle for Slack / Email / Standup, plus a
  side-by-side "raw git log vs. generated summary" panel — this is the
  single most convincing thing to show judges.
- No auth, no persistence. State lives in memory for the session.

## Suggested stack (pick whatever your team knows fastest)
- Backend: Python (FastAPI) or Node (Express) — either is fine, pick based
  on team familiarity, not on any tool preference.
- Git access: subprocess calls to the `git` CLI (`git log`, `git clone`) —
  don't reach for a git-parsing library, subprocess is faster to get right
  under time pressure.
- LLM calls: whatever Bob exposes as an API/SDK; keep prompts in a
  `prompts/` folder as plain text or small template files.
- Frontend: plain HTML/CSS/JS or a minimal React app — do not add a build
  pipeline you don't already know cold.

## What is explicitly NOT in this architecture
- No database.
- No multi-repo fan-out.
- No scheduling/cron.
- No auth/session management.
- No semantic (LLM-based) repo or theme classification beyond the grouping
  described in step 4, which is deterministic.
