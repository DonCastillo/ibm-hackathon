# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## What this project is
Standup Sync reads a single git repository's commit history over a date range and produces a human-readable summary of what was accomplished — suitable for posting to Slack, sending as an email digest, or reading out in a standup.

The core value-add over existing "changelog bot" tools: instead of just listing commit *messages* (often vague — "fix bug", "wip"), this tool reads the actual *diffs* and infers what changed and why, then groups related commits and flags likely blockers (repeated fixes to the same file, reverts, etc).

## Problem it solves
Developers often work across many small commits with unhelpful messages. Writing a standup update, a Slack progress post, or a status email means manually reconstructing "what did I actually get done" from a messy git log. This tool automates that reconstruction using an LLM that reads real diffs.

## Hackathon context
- Built for the IBM Bob 2.0 Hackathon (lablab.ai), Sept 25–27, 2026.
- IBM Bob must be used meaningfully during development. Take screenshots of Bob's task session summaries as you go, and note below (or in commit messages) which parts Bob generated or substantially assisted with.
- Scope is intentionally single-repo. Multi-repo aggregation is explicitly out of scope for this build — do not add it.
- Deadline is tight (well under 48 hours as of this writing). Bias every decision toward "smallest thing that demos cleanly" over "more complete."

## Core pipeline (in order)
1. **Git extraction** — run `git log -p` over a given date range (default: last 24h) for the target repo, on the local filesystem (clone if given a URL, otherwise use a local path).
2. **Noise filtering** — drop merge commits, formatting-only diffs, and changes to generated/lock files (`package-lock.json`, `*.min.js`, etc.) before anything is sent to the model.
3. **Diff analysis** — send filtered commits/diffs to the LLM in batches; ask it to describe *what changed and why* in plain English, not just restate the commit message.
4. **Grouping** — cluster the per-commit summaries by theme (shared directories/files touched) and by author. Pure logic, no LLM call.
5. **Blocker detection** — flag patterns suggesting a struggle: the same file touched 3+ times in the window, revert commits, or a commit message containing "revert" / "undo" / "wip" / "fix fix". Deterministic pattern-matching only — keep it cheap, fast, and unit-testable.
6. **Summary generation** — produce one structured intermediate summary object (see `architecture.md`) that every output format renders from.
7. **Format rendering** — turn the structured summary into one of:
   - Slack (short, casual, bullet-heavy, light emoji)
   - Email (slightly more formal, grouped by workstream)
   - Standup notes (per-person "what I did / possible blockers")

## Non-goals for this build
- No multi-repo support.
- No scheduled/automated runs (cron, GitHub Action) — manual trigger only.
- No auth, no user accounts, no persistence beyond the current session.
- No Bob-inferred ("smart") semantic classification — grouping uses simple heuristics (shared file paths / directories), not model calls.
- No polished design system — functional UI is enough.

## Conventions for whoever (or whatever agent) builds this
- Keep the noise filter and blocker detector as pure functions with no LLM calls — they must be unit-testable without hitting an API.
- Keep the three output formats as templates over one shared summary object, not three separate pipelines. Adding or tweaking a format should never require touching extraction or analysis code.
- Prefer clarity and a working demo over extensibility. This is a rush build; don't add config systems, plugin architectures, or abstractions that aren't needed for the single-repo case.
- Every LLM prompt used (for diff analysis and summary generation) should live in one clearly named location (e.g. `prompts/`) so it's easy to show judges exactly what was asked of Bob during development and what the running app itself asks the model at runtime — these are two different things and both matter for the submission.
- Fail loudly and simply. If the repo path is invalid or there are no commits in range, show a clear message — don't silently return an empty summary.

## What "done" looks like for the hackathon demo
- Paste a repo path/URL + pick a date range in a simple web UI.
- Click generate, see a before/after view: raw git log vs. the generated summary.
- Toggle between Slack / Email / Standup views of the same underlying data.
- At least one visible example of blocker detection catching something a flat commit list would miss.

## Submission reminders (do not leave until the end)
- Screenshot Bob's task session summaries continuously while building, not retroactively.
- Keep a running one-line log per session of what Bob was asked to do and what it produced (see `tasks.md` for where this fits in the timeline).
- Budget real time (3–4 hours) at the end for: demo video, slides, cover image, deployment, and the actual lablab.ai submission form.

## Rules
- When planning for the project, put any documents and artifacts in the `./plan/` folder.
- Put all deliverables of this project in `./deliverables/`. Deliverables are content, assets, or artifacts to be submitted to the hackathon.
- This project should create/update a `README.md` file that details the following:
  - What this project is
  - Which URL to access the demo app
  - Link of the video demo (to be provided later once the implementation is finished)
  - What tech stacks are used
  - Instructions on how to run the project locally or in development mode
  - Instructions on how to deploy the app live
- Any updates on the architecture, plans, workflows, or tech stacks should update/amend the `README.md`.
- The `README.md` must include a **Project Deliverables** section for hackathon judges, containing links to external or internal sources that judges can view.
- Consult me first or ask me questions if you are about to execute complicated tasks.
