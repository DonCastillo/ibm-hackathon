# Testing summary

This page covers what the test suite checks, what it found, and what was changed as a result.

**Status (Sept 27, 2026):** all 102 tests pass.

| Suite | Tests | Runtime | Command |
|---|---|---|---|
| Offline (unit + API) | 80 | ~9 s | `pytest -m "not network"` |
| Default (offline + small public repos) | 97 | ~45 s | `pytest` |
| Large repos (opt-in) | 5 | ~4.5 min | `pytest -m slow -s` |

Setup: `pip install -r requirements-dev.txt`. The LLM is replaced by a stub in every test, so no API keys are needed and no LLM usage is billed.

---

## What is tested

### `test_git_extractor.py`: commit extraction (31 tests, offline)

These tests build throwaway git repos with chosen branches, authors and commit dates.

- **All branches:** commits on unmerged feature branches are picked up. A commit shared by several branches is returned once. Merge commits are excluded, but the work they merged is kept. Branches that exist only on the remote (`origin/*`) are included, and their names are shown without the `origin/` prefix.
- **Date ranges:** preset ranges ("7 days ago"), custom From/To dates, a single day (From = To), commits late in the evening of the end date, and ranges with no commits.
- **Local paths:** an empty repo, a folder that isn't a repo, and a path that doesn't exist.
- **Diff stats:** counts of files added, modified and deleted, and of lines added, deleted and updated. A commit message containing `|` survives parsing, and so does a file containing the log's own separator text.
- **Clone errors:** a private repo with no token, a rejected token, SSH access denied, and network failures. Each should give the right message, and the token must never appear in an error.
- **Token formats:** the right URL format for GitHub, GitLab, Bitbucket, Azure DevOps, custom ports, and URLs that already contain credentials.
- **Busy repos:** a repo with 30 daily commits, cloned with a depth of 5. Every commit in the range must come back with correct stats, and `git log` must not need to download anything on demand.

### `test_noise_filter.py`: dropping low-signal commits before the LLM (7 tests, offline)

- A revert is dropped together with the commit it reverts (git's `Revert "<subject>"` format). Hand-written "revert …" and "undo …" commits are dropped too, but words like "reverted-state" are not mistaken for reverts.
- Spacing-only changes are dropped: re-indentation, trailing spaces and blank lines. A spacing change combined with a real change is kept.
- Commits touching only lock files or build output are dropped.

### `test_diff_analyzer.py`: matching LLM summaries to commits (11 tests, offline)

- A complete reply maps one summary to each commit.
- A reply cut off mid-sentence keeps the finished summaries and uses the commit message for the rest.
- An intro line ("Here are the summaries:"), skipped numbers, and items out of order still put each summary on the right commit.
- `1)` and `**1.**` list styles work. Numbers beyond the batch and duplicate numbers are ignored.
- A 12-commit run is split into batches of 10 and 2, each gets the right output budget, and the summaries stay in commit order.
- `[MAJOR]` / `[MINOR]` impact tags are stripped from the summary text and recorded. Untagged summaries and commit-message fallbacks count as major, so nothing is hidden by mistake.

### `test_format_renderer.py`: output formats per `plan/format.md` (9 tests, offline)

- **One LLM call per audience** (developer and client). Each prompt combines the audience rules with all three format rules ("no more than 6 bullets, each under 15 words", "no more than 300 words", "at most 3 short fragments"), the universal "what changed, not why" rule, the period and the updates.
- **Limits enforced in code:** Slack is cut to 6 bullets (bullet styles normalized). Standup is cut to 3 fragments per person. An email over 400 words gets one retry, then trailing sections are dropped. A short email is not retried.
- **Fallbacks:** a missing section falls back to a plain list for developers, and to "couldn't be generated" for clients, so technical summaries never reach a client. An LLM failure never breaks the report.
- **Headers:** developer versions show the repo, period and minor-update count. Client versions never show the repo name or the minor-update note.

### `test_api.py`: the `/api/generate` pipeline end to end (12 tests, offline)

- **Successful run:** progress, raw log and result events arrive in order. Raw log lines are tagged with their branch. Developer Stats show, per person, highlights (commits that made it into the reports), total commits, and branches. All six output formats (developer and client-facing Slack, Email and Standup) are generated.
- **Major updates only:** Slack, Email and Standup list only major updates and end with "+ N minor updates (small fixes, docs, tweaks) not shown". The client narrative is only given the major updates. Developer Stats and the raw log still cover every commit. If a period has only minor updates, they are all shown.
- **Errors:** no commits in range, an empty repo, commits that only touch lock files or build output, an invalid path, and a private repo. The private-repo error carries `code: "repo_access"`, which the UI uses to highlight the token field. An unexpected failure comes back as one readable line, never a traceback. The app page is served at `/standup` and `/`, and its static assets load. A request without a `repo` field gets a 422 error.

### `test_remote_repos.py`: real public repos (17 in the default run, plus 5 opt-in)

| Repo | What it checks |
|---|---|
| `octocat/Hello-World` | A repo with no activity since 2018: all 3 branches are captured, a `.git` URL gives the same result, every preset range returns no commits, and a custom 2011–2018 range works |
| `octocat/Spoon-Knife` | A repo with no activity since 2014 returns no commits |
| `fastapi/fastapi`, `expressjs/express` | Active repos return recent commits with well-formed fields and no duplicates |
| `pallets/flask`, `sindresorhus/awesome` | Quiet repos don't raise an error |
| `octocat/does-not-exist-xyz` | Reported as private, with and without a fake token |
| `notarealhost.example` | Gives a plain error, not the private-repo message |
| `git@github.com:…` (SSH) | Either clones, or fails with a clear message instead of hanging |

**Large repos (opt-in), last 7 days, after the fixes below:**

| Repo | Branches | Commits found | Before | After |
|---|---|---|---|---|
| gitlab-org/cli | ~460 | 71 | **failed** | 4 s |
| facebook/react | ~970 | 8 | 20 s | 16 s |
| kubernetes/kubernetes | ~60 | 99 | 128 s | 53 s |
| dependabot/dependabot-core | ~550 | 79 | 81 s | 55 s |
| microsoft/vscode | ~5,300 | 1,125 | 807 s | 143 s |

---

## Bugs found and fixed

| # | Bug | Found by | Fix |
|---|---|---|---|
| 1 | **Custom date ranges lost commits.** Git reads a plain date like `2026-09-10` as that day at the *current* time of day. A single-day range (From = To) was always empty, and commits late on the end date were dropped. | Date-range tests | Plain dates are now pinned to 00:00:00 (From) and 23:59:59 (To). |
| 2 | **Branches that exist only on the remote kept the `origin/` prefix** (`origin/feature/x` instead of `feature/x`). | Remote-only branch test | The remote name is stripped from branch tags. |
| 3 | **About 30% of commits showed "(summary unavailable)".** Every LLM batch of 10 commits was capped at 200 output tokens, so replies were cut off after about 6 summaries. The fallback also left list numbers ("6.", "7.") and half-finished sentences in the summaries, and it could put summaries on the wrong commit. | Spotted in the UI, then reproduced in a test | Each batch now gets 80 output tokens per commit. Replies are matched to commits by number, and a missing or cut-off summary falls back to the commit message. The extra cost is about $0.008 per 100 commits. |
| 4 | **Cloning busy repos was slow, and it crashed on some hosts.** The clone skips file contents to save time, so `git log -p` then downloaded them one commit at a time (13.5 min for vscode). On GitLab this aborted with a "promisor remote" error. | Large-repo tests | All the file contents the report needs are now downloaded in one request before `git log` runs. |
| 5 | **Very active repos silently lost commits.** The clone only goes 200 commits deep per branch, which can be less than a week of history on a busy repo. The oldest commit fetched also had no parent in the clone, so its stats counted every file in the repo as added. | Large-repo tests, then the busy-repo test | If the 200-commit cutoff falls inside the date range, the clone is extended by another 200 commits, up to 10 times. |
| 6 | **SSH clones could hang forever** on a host-key or password prompt. | Found while writing the SSH test | SSH now runs in batch mode, so it fails instead of prompting. |
| 7 | **Repos containing the log-parsing marker produced fake commits.** The parser split git's output wherever the text `COMMIT_START\|` appeared, including inside diffs. This project's own `git_extractor.py` and Bob session exports contain that text, so 35 of 59 "commits" on this repo were fake (hash `%H`, author `%an`, source code as the branch). The real commits touching those files also had their diffs cut short. | Manual test against this repo | The parser now splits only where the marker starts a line. Diff content lines always begin with `+`, `-` or a space, so file content can't match. |
| 8 | **Commits were tagged `HEAD` instead of their branch.** On a local repo whose branch is ahead of the remote (unpushed work), commits shared with `origin/main` were labelled from `origin/HEAD`, a pointer to the default branch rather than a real branch. "HEAD" then showed in the raw log and the Branches column. | Screenshots of the new UI | `origin/HEAD` is excluded when listing branches (`--exclude=*/HEAD`). |

Earlier in the same session, before the test suite existed:

- **Private repos:** they now show "This repository appears to be private… add a Personal Access Token", and the token field is highlighted. Before, users saw a raw git error, and the Personal Access Token could appear inside that error text. Git also no longer waits for a username prompt.
- **All branches:** every branch is analyzed, not just the default one. Each raw log line is tagged with its branch, and Developer Stats have a new **Branches** column.
- **Output formats follow `plan/format.md`:** Slack (3–6 bullets), Email (≤300 words, 2–4 sections) and Standup (≤3 fragments per person) are now written by the LLM for both audiences, in 2 parallel calls (about +$0.0075 per run). The prompts live in `prompts/`. Client versions no longer show the repo name, and headers show readable dates.
- **Accomplishments only:** blocker detection was removed entirely, so there are no blocker bullets, "Watch items" or blocker lines. Reverts are dropped before the LLM, together with the commit they undo. The spacing check now also catches re-indentation and trailing spaces, not just blank lines.
- **Shorter reports:** the LLM tags each commit major or minor in the same call that writes its summary (no extra calls). Reports list only major updates, with a count of the minor ones left out.
- **Sync button:** it's only enabled when a repo is entered and a date range is chosen (a preset, or both custom dates). It's labeled **⚡ Sync My Standup**.

---

## Known issues

Fixed:
- ~~Unexpected errors show a full Python traceback.~~ The UI now shows one readable line ("Something went wrong while generating the report: …"); the traceback goes to the server log.
- ~~The spinner can hang with no message on a 422/500 response.~~ Error responses, and streams that end without a result, now show a clear message.
- ~~After an error, the previous run's results stay on screen.~~ Previous outputs and stats are hidden until the new result arrives.
- ~~Author names and error text are inserted without escaping.~~ Author and branch names are escaped, and status/error messages are set as plain text.

Fixed before deployment:
- ~~Custom dates use the server's time zone.~~ The browser sends its UTC offset, so "Sep 10" means the user's Sep 10 even on a UTC server.
- ~~A deployed server will analyze any local path on its own filesystem.~~ Local paths and `file://` URLs are refused unless `ALLOW_LOCAL_REPOS=1` (local development only).
- ~~The Copy button relies on the browser's global `event` object.~~ It is now passed the button directly.

## Not covered by tests

- **The frontend:** the Sync button's enabled/disabled state and the token-field highlight. Testing these needs a browser tool such as Playwright.
- **The real LLM:** summary quality needs a manual check. Run the app on a real repo and compare about 10 summaries against their diffs (item 15 in `plan/tasks.md`).
