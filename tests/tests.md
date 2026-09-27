# Testing summary

This page covers what the test suite checks, what it found, and what was changed as a result.

**Status (Sept 27, 2026):** all 72 tests pass.

| Suite | Tests | Runtime | Command |
|---|---|---|---|
| Offline (unit + API) | 50 | ~8 s | `pytest -m "not network"` |
| Default (offline + small public repos) | 67 | ~45 s | `pytest` |
| Large repos (opt-in) | 5 | ~4.5 min | `pytest -m slow -s` |

Setup: `pip install -r requirements-dev.txt`. The LLM is replaced by a stub in every test, so no API keys are needed and no LLM usage is billed.

---

## What is tested

### `test_git_extractor.py`: commit extraction (30 tests, offline)

These tests build throwaway git repos with chosen branches, authors and commit dates.

- **All branches:** commits on unmerged feature branches are picked up. A commit shared by several branches is returned once. Merge commits are excluded, but the work they merged is kept. Branches that exist only on the remote (`origin/*`) are included, and their names are shown without the `origin/` prefix.
- **Date ranges:** preset ranges ("7 days ago"), custom From/To dates, a single day (From = To), commits late in the evening of the end date, and ranges with no commits.
- **Local paths:** an empty repo, a folder that isn't a repo, and a path that doesn't exist.
- **Diff stats:** counts of files added, modified and deleted, and of lines added, deleted and updated. A commit message containing `|` survives parsing, and so does a file containing the log's own separator text.
- **Clone errors:** a private repo with no token, a rejected token, SSH access denied, and network failures. Each should give the right message, and the token must never appear in an error.
- **Token formats:** the right URL format for GitHub, GitLab, Bitbucket, Azure DevOps, custom ports, and URLs that already contain credentials.
- **Busy repos:** a repo with 30 daily commits, cloned with a depth of 5. Every commit in the range must come back with correct stats, and `git log` must not need to download anything on demand.

### `test_diff_analyzer.py`: matching LLM summaries to commits (11 tests, offline)

- A complete reply maps one summary to each commit.
- A reply cut off mid-sentence keeps the finished summaries and uses the commit message for the rest.
- An intro line ("Here are the summaries:"), skipped numbers, and items out of order still put each summary on the right commit.
- `1)` and `**1.**` list styles work. Numbers beyond the batch and duplicate numbers are ignored.
- A 12-commit run is split into batches of 10 and 2, each gets the right output budget, and the summaries stay in commit order.
- `[MAJOR]` / `[MINOR]` impact tags are stripped from the summary text and recorded. Untagged summaries and commit-message fallbacks count as major, so nothing is hidden by mistake.

### `test_api.py`: the `/api/generate` pipeline end to end (9 tests, offline)

- **Successful run:** progress, raw log and result events arrive in order. Raw log lines are tagged with their branch. Developer Stats list the branches each person worked on. All six output formats (developer and client-facing Slack, Email and Standup) are generated.
- **Major updates only:** Slack, Email and Standup list only major updates and end with "+ N minor updates (small fixes, docs, tweaks) not shown". The client narrative is only given the major updates. Developer Stats and the raw log still cover every commit. If a period has only minor updates, they are all shown.
- **Errors:** no commits in range, an empty repo, commits that only touch lock files or build output, an invalid path, and a private repo. The private-repo error carries `code: "repo_access"`, which the UI uses to highlight the token field. A request without a `repo` field gets a 422 error.

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

Earlier in the same session, before the test suite existed:

- **Private repos:** they now show "This repository appears to be private… add a Personal Access Token", and the token field is highlighted. Before, users saw a raw git error, and the Personal Access Token could appear inside that error text. Git also no longer waits for a username prompt.
- **All branches:** every branch is analyzed, not just the default one. Each raw log line is tagged with its branch, and Developer Stats have a new **Branches** column.
- **Shorter reports:** the LLM tags each commit major or minor in the same call that writes its summary (no extra calls). Reports list only major updates, with a count of the minor ones left out.
- **Sync button:** it's only enabled when a repo is entered and a date range is chosen (a preset, or both custom dates). It's labeled **⚡ Sync My Standup**.

---

## Known issues not yet fixed

1. Unexpected errors show a full Python traceback in the UI instead of a one-line message.
2. The spinner can hang with no message if the server returns an error response (for example a 422 or 500) instead of an event stream.
3. After an error, the previous run's summary and output tabs stay on screen.
4. Custom dates use the server's time zone, which will be off for users in other time zones once deployed.
5. Author names and error text are inserted into the page without escaping, so a malicious repo could inject HTML or scripts.
6. A deployed server will analyze any local path on its own filesystem.
7. The Copy button relies on the browser's global `event` object.

## Not covered by tests

- **The frontend:** the Sync button's enabled/disabled state and the token-field highlight. Testing these needs a browser tool such as Playwright.
- **The real LLM:** summary quality needs a manual check. Run the app on a real repo and compare about 10 summaries against their diffs (item 15 in `plan/tasks.md`).
