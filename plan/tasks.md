# tasks.md — Standup Sync build checklist

Assumes a tight remaining window (well under 24h). Ordered so that if you run out of time, everything already checked off is still a working, demoable product. Do not start a later section until the one before it works end-to-end on a real repo.

## 0. Setup (15 min)
- [ ] Pick stack (backend language, no frontend framework unless already fluent in one).
- [ ] Confirm access to a real test repo with a real commit history from the last 24h (yours or a public one) — you need this to test against, not a toy repo with 2 commits.
- [ ] Confirm how to call Bob programmatically (API/SDK/CLI) — do this check first, before writing pipeline code, so you're not blocked later.
- [ ] Start your Bob session-summary screenshot habit right now, from the first session.

## 1. Core pipeline — single repo (target: 3–4 hours)
- [ ] Git extraction: given a local repo path + date range, return raw commits with diffs (`git log -p --since=...`).
- [ ] Noise filter: strip merges, lockfiles/generated files, whitespace-only diffs. Write this as a pure function; test it on your real repo's log.
- [ ] Diff analysis: send filtered commits (batched) to Bob, get back one plain-English sentence per commit describing what changed and why.
- [ ] Sanity check: manually read 10 of the generated sentences against the real diffs. If they're vague or wrong, fix the prompt before moving on — this is the core value prop, don't skip the check.

## 2. Grouping and blockers (target: 1–2 hours)
- [ ] Grouping: cluster commits by touched directory/file, attach author list per group. Pure function, no LLM call.
- [ ] Blocker detection: same-file-3+-times and revert/wip message detection. Pure function, no LLM call.
- [ ] Assemble the summary object (see `architecture.md` §6) from the above.
- [ ] Test on the real repo: does it produce at least one sensible group and (ideally) one real or plausible blocker flag?

## 3. One output format first (target: 1 hour)
- [ ] Pick ONE format to build first — recommend Slack, it's the most visually convincing in a demo.
- [ ] Write the renderer as a pure function: `summary -> Slack-formatted string`.
- [ ] Only after this works end-to-end, add a second format (Standup or Email) if time allows. Do not build all three before one is fully working and tested.

## 4. Minimal web UI (target: 2 hours)
- [ ] Form: repo path/URL input, date range (or just "last 24h" hardcoded if time is short — a dropdown is a stretch, not a requirement), a "Generate" button.
- [ ] Results view: show the generated summary in the current format.
- [ ] Before/after panel: raw git log (or raw commit messages) next to the generated summary — this single view is your strongest demo moment, don't cut it.
- [ ] Format toggle, if more than one renderer exists yet.
- [ ] Skip: auth, persistence, styling beyond "readable and not broken."

## 5. Stretch (only if everything above is done and stable)
- [ ] Second and third output formats.
- [ ] Nicer UI styling.
- [ ] Config-based (not LLM-based) multi-repo support — only attempt this if the single-repo version has been working cleanly for a while with time to spare. If in doubt, don't.

## 6. Submission prep (budget 3–4 hours minimum, do not compress this)
- [ ] Collect and organize all Bob task-session screenshots taken so far into one folder.
- [ ] Write a short "How Bob was used" section (README or submission long description) — one line per session: what was asked, what Bob produced.
- [ ] Deploy the app somewhere reachable (Vercel/Render/Replit/etc.) and confirm the URL actually works from a fresh browser/incognito window.
- [ ] Record a 2–3 minute demo video: show the problem, run the tool live on a real repo, show the before/after view, highlight one blocker catch.
- [ ] Write short description, long description, pick technology/category tags.
- [ ] Cover image: screenshot of the before/after view.
- [ ] Slide deck: problem, solution, architecture (reuse `architecture.md` diagram), differentiation, how Bob was used.
- [ ] Fill out and submit the lablab.ai form. Do this with buffer time before the deadline, not at the last minute — uploads and form quirks eat time.

## Cut list — do not build these under this timeline
- Multi-repo aggregation beyond a possible config-based stretch (see §5).
- Any LLM-based ("smart") repo/theme classification.
- Scheduled/automated runs, cron, GitHub Actions integration.
- User accounts, auth, persistence/database.
- Real Slack OAuth app install — a webhook or copy-paste output is enough for the demo.
