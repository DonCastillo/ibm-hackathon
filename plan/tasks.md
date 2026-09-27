# tasks.md — Standup Sync build checklist

Assumes a tight remaining window (well under 24h). Ordered so that if you run out of time, everything already checked off is still a working, demoable product. Do not start a later section until the one before it works end-to-end on a real repo.

## 0. Setup (15 min)
- [x] Pick stack (backend language, no frontend framework unless already fluent in one). → Python + FastAPI; plain HTML/JS frontend.
- [x] Confirm access to a real test repo with a real commit history from the last 24h (yours or a public one) — you need this to test against, not a toy repo with 2 commits. → https://github.com/DonCastillo/ibm-hackathon
- [x] Confirm how to call Bob programmatically (API/SDK/CLI) — do this check first, before writing pipeline code, so you're not blocked later. → ibm-watsonx-ai SDK confirmed, .env populated.
- [x] Start your Bob session-summary screenshot habit right now, from the first session. → Screenshots saved to `bob_sessions/`.

## 1. Core pipeline — single repo (target: 3–4 hours)
- [x] Git extraction: given a local repo path + date range, return raw commits with diffs (`git log -p --since=...`). → `backend/git_extractor.py`
- [x] Noise filter: strip merges, lockfiles/generated files, whitespace-only diffs. Write this as a pure function; test it on your real repo's log. → `backend/noise_filter.py`
- [x] Diff analysis: send filtered commits (batched) to Bob, get back one plain-English sentence per commit describing what changed and why. → `backend/diff_analyzer.py` + `prompts/diff_analysis.txt`. Now "what changed" in 8–15 words, tagged [MAJOR]/[MINOR]; reports show major updates only.
- [x] Sanity check: manually read 10 of the generated sentences against the real diffs. If they're vague or wrong, fix the prompt before moving on — this is the core value prop, don't skip the check. → Verified on a real run (Sept 27). Along the way: "(summary unavailable)" for ~30% of commits (LLM replies cut off at 200 tokens) and fake commits from this repo's own source were found and fixed.

## 2. Grouping and blockers (target: 1–2 hours)
- [x] Grouping: cluster commits by touched directory/file, attach author list per group. Pure function, no LLM call. → `backend/grouper.py`
- [x] ~~Blocker detection~~ → Removed: reports cover accomplishments only. Reverts (and the commit they revert) are dropped by the noise filter instead. Originally: revert/wip message detection. Pure function, no LLM call. (`backend/blocker_detector.py`, since deleted)
- [x] Assemble the summary object (see `architecture.md` §6) from the above. → `backend/summarizer.py`
- [x] Test on the real repo: does it produce at least one sensible group and (ideally) one real or plausible blocker flag? → Verified on https://github.com/DonCastillo/ibm-hackathon (Sept 27): groups and major/minor split look right. Blockers were removed (accomplishments only).

## 3. One output format first (target: 1 hour)
- [x] Pick ONE format to build first — recommend Slack, it's the most visually convincing in a demo. → Slack chosen.
- [x] Write the renderer as a pure function: `summary -> Slack-formatted string`. → Originally `backend/renderers/slack_renderer.py`; now `backend/renderers/format_renderer.py` (see §5).
- [x] Only after this works end-to-end, add a second format (Standup or Email) if time allows. Do not build all three before one is fully working and tested. → All three renderers built: Slack, Email, Standup.

## 4. Minimal web UI (target: 2 hours)
- [x] Form: repo path/URL input, date range (or just "last 24h" hardcoded if time is short — a dropdown is a stretch, not a requirement), a "Generate" button. → `frontend/index.html`
- [x] Results view: show the generated summary in the current format. → `frontend/index.html`
- [x] Before/after panel: raw git log (or raw commit messages) next to the generated summary — this single view is your strongest demo moment, don't cut it. → `frontend/index.html`. Later reworked: the side-by-side "Generated summary" panel only duplicated the Slack tab, so it was removed. The page now shows Output Formats (Developer/Client toggle, Slack/Email/Standup tabs) with the full-width Raw git log below it.
- [x] Format toggle, if more than one renderer exists yet. → Slack / Email / Standup tabs in UI.
- [x] Skip: auth, persistence, styling beyond "readable and not broken."

## 5. Stretch (only if everything above is done and stable)
- [x] Second and third output formats. → Slack, Email, Standup for both developer and client audiences, following `plan/format.md` (Slack 3–6 bullets, Email ≤300 words, Standup ≤3 fragments per person). Written by the LLM in 2 parallel calls (one per audience) from `prompts/render_base.md` + `slack.md` / `email.md` / `standup.md` + `audience_*.md`; limits enforced in `backend/renderers/format_renderer.py`.
- [x] Nicer UI styling. → Quick-range date pills + custom date picker, tooltips for repo URL and token, Developer Stats table, developer/client tone toggle, progress steps; CSS split into `frontend/styles.css`.
- [ ] Config-based (not LLM-based) multi-repo support — only attempt this if the single-repo version has been working cleanly for a while with time to spare. If in doubt, don't. → Skipped (out of scope per AGENTS.md).

## 6. Submission prep (budget 3–4 hours minimum, do not compress this)
- [x] Collect and organize all Bob task-session screenshots taken so far into one folder. → `bob_sessions/`: 3 session-summary screenshots + 4 Bob task exports (`bob-task-*.json`), Sept 26–27.
- [ ] Write a short "How Bob was used" section (README or submission long description) — one line per session: what was asked, what Bob produced.
- [ ] Deploy the app somewhere reachable (Vercel/Render/Replit/etc.) and confirm the URL actually works from a fresh browser/incognito window.
- [ ] Record a 2–3 minute demo video: show the problem, run the tool live on a real repo, show the before/after view, highlight one blocker catch. → Blockers were removed; highlight the developer/client toggle and how minor changes and reverts are left out instead.
- [ ] Write short description, long description, pick technology/category tags.
- [ ] Cover image: screenshot of the before/after view.
- [ ] Slide deck: problem, solution, architecture (reuse `architecture.md` diagram), differentiation, how Bob was used.
- [ ] Fill out and submit the lablab.ai form. Do this with buffer time before the deadline, not at the last minute — uploads and form quirks eat time.

## Added during the build (not in the original plan)
- [x] All-branch analysis: commits on unmerged feature branches are captured; raw log lines and Developer Stats show the branch.
- [x] Private repo support: Personal Access Token field, clear "repo is private — add a token" error, token never leaked in errors.
- [x] Generate button (now "⚡ Sync My Standup") enabled only with a repo and a valid date range.
- [x] Test suite: 88 tests (offline, real public repos, large repos). Found and fixed 7 bugs, including date ranges dropping commits, truncated LLM summaries, slow/crashing clones on busy repos, and fake commits from files containing the log separator. See `tests/tests.md`.
- [x] Accomplishments-only reports: blocker detection removed; reverts (with the commit they undo) and spacing-only changes dropped before the LLM; minor updates tagged by the LLM and left out, with a "+ N minor updates not shown" note for developers.
- [x] UI redesign (`plan/UI.md`), VS Code + Monokai look:
    - [x] Phase 1: theme and app page. `/standup` with editor chrome, settings-style form, glowing ⚡ Sync My Standup button with a "what's missing" hint and ⌘↵ shortcut, 5-step progress tracker with an OUTPUT log and timer, skeletons, error banner + toasts, coloured outputs and raw log.
    - [x] Phase 2: landing page at `/`: logo, hero with an animated git-log → Slack mini editor, 6 feature cards, "not another changelog bot" diff view, 5-step how-it-works pipeline (LLM steps marked), terminal-style call to action. The app moved to `/standup`.
    - [x] Phase 3: polish. Command palette (title-bar box, ⌘K / Ctrl+K or ⌘⇧P; filter, arrow keys, Enter, Esc), mobile pass (toasts clear the bottom icon row, empty state fits, the page scrolls to the progress tracker after Sync).
- [x] Report title above the results: "Accomplishments between {first} - {last}" or "Accomplishments on {date}" for a single day.
- [x] Fix remaining known issues before the demo. See `tests/tests.md` → "Known issues not yet fixed".
    - [x] Raw Python tracebacks shown in the UI on unexpected errors. Fixed: the UI shows one readable line; the full traceback goes to the server log.
    - [x] Spinner hangs with no message when the server returns an error response (422/500) instead of an event stream. Fixed: error responses and streams that end early now show a clear message.
    - [x] Stale results after an error. Fixed: a new run hides the whole results area, and previous Output Formats and Developer Stats stay hidden until the new result arrives.
    - [x] Unescaped text in the page. Fixed: author and branch names are escaped, and all status/error messages are set as plain text.

## Cut list — do not build these under this timeline
- Multi-repo aggregation beyond a possible config-based stretch (see §5).
- Any LLM-based ("smart") repo/theme classification.
- Scheduled/automated runs, cron, GitHub Actions integration.
- User accounts, auth, persistence/database.
- Real Slack OAuth app install — a webhook or copy-paste output is enough for the demo.
