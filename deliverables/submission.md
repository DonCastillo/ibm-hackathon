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

**The problem.** Every standup, status email and client update starts the same way: a developer scrolls through `git log` trying to reconstruct what they got done. Commit messages rarely help ("fix stuff", "wip"), so people open diffs, jump between branches and piece the week together from memory, then write it up again for the team, Slack and the client. It is slow, repetitive and error-prone: unmerged branch work gets forgotten, and reverts or formatting changes get reported as progress.

**The solution.** Standup Sync is a web app that writes those updates from the code itself. It reads the actual changes in a git repository over a date range, keeps only the meaningful ones, and produces ready-to-post Slack, Email and Standup updates, each in a developer version and a client version.

**Who it's for.** Developers preparing standups, team leads summarizing a week, and freelancers or agencies reporting to non-technical clients.

**How they use it.** Paste a repository URL (any git host; private repos with a Personal Access Token), pick a range such as "last 7 days", and press ⚡ Sync My Standup. A live tracker shows each step, then the six updates arrive: switch formats, toggle Developers and Clients, and copy with one click. Per-developer highlights show who shipped what.

**Why it's creative and unique.** Changelog tools repeat commit messages, count every commit, usually read one branch and write one technical format. Standup Sync does the opposite:
- **It reads the diffs, not the messages,** so "fix stuff" still becomes "Fixed duplicate charge on payment retry".
- **It reports accomplishments only.** Merges, lock files, spacing-only edits and reverts (with the commit they undo) are removed in code; the AI tags each remaining change MAJOR or MINOR, and only major ones are reported.
- **It covers every branch,** including unmerged feature work.
- **It writes for the audience:** file and function names for developers, plain-English outcomes for clients, in the same run.

**How it solves the problem effectively and efficiently.**
- **Accurate:** reports come from the code itself, across every branch, with noise filtered out. 102 automated tests, including runs against real public repositories, cover the pipeline.
- **Concise by design:** strict limits (Slack 3–6 bullets, email under 300 words, standup at most three lines per person) are enforced in code as well as in the prompt, so updates stay short enough to post as-is.
- **Efficient:** only two of five steps use an LLM, which only sees commits that survive the filter, so a typical run costs a few cents. Clones fetch only what a report needs: on microsoft/vscode, collecting a week of commits dropped from 807 to 143 seconds.
- **One run, six outputs:** the same week never has to be rewritten for each audience.

**Built with IBM Bob,** which planned from our specs, set up watsonx.ai from IBM's documentation, and built the first working version.

**Try it:** https://standup-sync.onrender.com · **Code:** https://github.com/DonCastillo/standup-sync · **Video:** https://youtu.be/U1RgV6Qivug

*(≈ 485 words)*

---

## IBM Bob Usage Statement

We used IBM Bob in three tasks on Sept 26, 2026 (about ten hours) to take Standup Sync from planning documents to a working app. Every task's full export is in `bob_sessions/`.

**1. Planning from our documents (document understanding).** We gave Bob our `AGENTS.md` and `plan/` folder. It read them, estimated the build at 11–14 hours, walked us through the setup decisions, and noted that the challenge favours an IBM model, so we added watsonx.ai.

**2. Setting up IBM watsonx.ai (IBM documentation search).** Bob searched IBM's watsonx documentation for the Python SDK setup, available model IDs, account creation and project configuration, then guided us through IBM Cloud: creating the project, finding the credentials, and associating a Watson Machine Learning runtime. When calls failed with "project is not associated with a WML instance", Bob diagnosed the region and resource-group filters hiding our service and verified the fix with a test script.

**3. Building the pipeline (agentic coding).** Bob scaffolded the application: git extraction, the noise filter, the diff-analysis prompt, grouping, the summary object, Slack/Email/Standup renderers and the FastAPI app. It fixed a failing `ibm-watsonx-ai` install by rebuilding the environment on Python 3.11, fixed errors from our test runs, and made generation feel fast by streaming progress to the browser and running LLM batches concurrently. It also added a one-line switch between watsonx.ai and Anthropic, and a `.gitignore` that keeps API keys out of git.

**4. Cost and speed analysis.** Bob counted the LLM calls per run, estimated token costs for both providers, and found why clones were slow: it switched to bare, blobless clones that download only git history. When summaries only echoed commit messages, it found diffs were cut at 1,500 characters and raised the limit so the model reads the actual changes.

**5. Features with planning, a subagent and Agent mode.** For per-developer statistics, Bob used its planning skill to write a plan, spawned an explore subagent to map the codebase, asked us a design question, then switched to Agent mode to implement it. It also built client-facing versions of every format (a new prompt and renderer), repository-format tooltips, Personal Access Token support with the correct token format for GitHub, GitLab, Bitbucket and Azure DevOps, date-range presets with validation, and split the frontend into HTML, CSS and JavaScript.

From Sept 27 onward we continued with Claude Code for testing, the accomplishments-only filtering, the final output formats, the UI redesign and deployment.

**How the project uses IBM watsonx.ai.** Every LLM call goes through one module, `backend/llm_client.py`. With `LLM_PROVIDER=watsonx` (the code's default), it calls IBM watsonx.ai through the `ibm-watsonx-ai` SDK (`ModelInference`, chat API) with `mistralai/mistral-small-3-1-24b-instruct-2503`, both to summarize and classify each commit's diff and to write the Slack, Email and Standup updates. The public demo is configured with Claude Haiku 4.5; switching it to watsonx.ai is a settings change (the provider and watsonx credentials), with no code changes. We did not use watsonx Orchestrate.

*(≈ 483 words)*

---

## Additional links

- **Demo video:** https://youtu.be/U1RgV6Qivug
- **Live app:** https://standup-sync.onrender.com
- **Source code:** https://github.com/DonCastillo/standup-sync

---

## Technology tags

IBM Bob · IBM watsonx.ai · Anthropic Claude · Python · FastAPI · Git · Large Language Models · Render

## Category tags

Developer Tools · Productivity · Generative AI · DevOps · Team Collaboration

---

## Notes for the submitter (not for the form)

- **Claims to double-check before submitting:**
  - "fix stuff" → "Fixed duplicate charge on payment retry" is an illustrative example (the same one as the landing page), not output from a real run.
  - "a few cents" per run: an estimate for typical repos on Claude Haiku 4.5; very busy repos cost more (about $1.30 for a week of microsoft/vscode).
  - "102 automated tests": the count as of Sept 27 (`tests/tests.md`). Update it if tests change.
  - The Bob features named (document understanding, IBM docs search, planning skill, explore subagent, Agent mode) all appear in the `bob_sessions/` exports. "Parallel tasks" was not used, so it is not claimed.
- **No time-saved number is given** because none was measured. If you want one, time yourself writing a weekly update by hand and with the app, and add "from ~N minutes to ~M" to the Impact paragraph.
- **Claude Code is mentioned once, in the Bob Usage Statement** ("From Sept 27 onward we continued with Claude Code…"), matching the README. It keeps the statement accurate; remove it only if the hackathon rules require otherwise.
- **The Bob statement says the public demo runs Claude Haiku 4.5**, and that watsonx.ai is one environment variable away. If you switch the Render service to `LLM_PROVIDER=watsonx` (plus the three `WATSONX_*` keys) before judging, change that sentence to say the demo runs on watsonx.ai.
