# Submission text — Standup Sync

Drafts for the lablab.ai submission form. Check each field's character limit on the form and trim if needed.

---

## Project title

Standup Sync

## Tagline (one line)

Your standup, written from the code.

## Short description (≈ 200 characters)

Standup Sync reads the actual code changes in a git repo, filters out the noise, and writes Slack, Email and Standup updates for developers or clients. Built with IBM Bob.

*(171 characters)*

## Long description

**The problem.** Every standup, weekly update and client email starts the same way: a developer scrolls through `git log` trying to reconstruct what they actually got done. Commit messages don't help — "fix stuff", "wip", "update" — so people open diffs, jump between branches, and rewrite the same work three times for three audiences. It is slow, repetitive, and easy to get wrong: unmerged branch work gets forgotten, and reverted or cosmetic changes get reported as progress.

**The solution.** Standup Sync turns a repository and a date range into ready-to-post updates. Paste a GitHub, GitLab, Bitbucket or Azure DevOps URL (private repos work with a Personal Access Token), pick "last 7 days", and press ⚡ Sync My Standup. A live progress tracker shows each step; a minute later you have a Slack update, an email and per-person standup notes — each in a developer version (file and function names) and a client version (plain-English outcomes), switchable with one click.

**How it works.**
1. **Git extraction:** commits from every branch in the range, so unmerged feature work is included. Fast blobless clones fetch only the history and file versions the report needs.
2. **Noise filter (no LLM):** merges, lock files, build output, spacing-only changes and reverts (together with the commit they undo) are dropped before any AI runs.
3. **Diff analysis (LLM):** the model reads each diff, not the commit message, writes a one-line summary, and tags it MAJOR or MINOR.
4. **Highlights:** only major updates reach the reports, grouped by area and author, with a note of how many minor ones were left out.
5. **Outputs (LLM):** strict format rules — Slack in 3–6 bullets, email under 300 words, standup in at most 3 fragments per person — enforced in code as well as in the prompt.

**What makes it different.** Changelog bots list commit messages as-is, count every commit, see one branch and write one technical format. Standup Sync reads the diffs, reports accomplishments only, covers every branch, and writes for your audience.

**Built with IBM Bob.** Bob built the first working version in three sessions. It used document understanding to plan from our `AGENTS.md` and `plan/` specs and searched IBM's watsonx.ai documentation to guide the setup; it scaffolded the full pipeline, debugged the watsonx.ai and Anthropic clients, diagnosed slow clones and switched to blobless clones, and used its planning skill, an explore subagent and Agent mode to add developer stats, client-facing outputs, private-repo support and the date-range UI. Every session export is in the repo.

**Impact.** A weekly update that meant reading a week of commits and diffs becomes a paste-and-click. Reports stay accurate — no forgotten branches, no reverted work reported as progress — and one run produces six ready-to-post versions instead of rewriting the same week three times. The app is covered by 102 automated tests, and the live demo runs on Render.

**Try it:** https://standup-sync.onrender.com
**Code:** https://github.com/DonCastillo/ibm-hackathon

*(≈ 480 words)*

---

## Technology tags

IBM Bob · IBM watsonx.ai · Anthropic Claude · Python · FastAPI · Git · Large Language Models · Render

## Category tags

Developer Tools · Productivity · Generative AI · DevOps · Team Collaboration

---

## Notes for the submitter (not for the form)

- **Claims to double-check before submitting:**
  - "a minute later": true for small and medium repos; very busy repos (thousands of branches) take longer. Soften to "moments later" if you demo a large repo.
  - "102 automated tests": the count as of Sept 27 (`tests/tests.md`). Update it if tests change.
  - The Bob features named (document understanding, IBM docs search, planning skill, explore subagent, Agent mode) all appear in the `bob_sessions/` exports. "Parallel tasks" was not used, so it is not claimed.
- **No time-saved number is given** because none was measured. If you want one, time yourself writing a weekly update by hand and with the app, and add "from ~N minutes to ~M" to the Impact paragraph.
- **The long description does not mention Claude Code.** The README's "How IBM Bob was used" section does. Decide whether the form should say so too (see the note in the chat).
