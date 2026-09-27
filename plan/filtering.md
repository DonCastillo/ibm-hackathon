# filtering.md — How Standup Sync decides what counts as an accomplishment

Reports list **accomplishments only**. Every commit in the selected date range passes through three stages. Each stage can remove commits, and only what survives all three appears in the Slack, Email and Standup reports.

| Stage | Where | Uses the LLM? | Removes |
|---|---|---|---|
| 1. Extraction | `backend/git_extractor.py` | No | Merge commits |
| 2. Noise filter | `backend/noise_filter.py` | No | Generated/lock-file-only commits, spacing-only commits, reverts (and the commit they revert) |
| 3. Impact tagging | `prompts/diff_analysis.txt`, `backend/diff_analyzer.py`, `backend/main.py` | Yes | Commits tagged `[MINOR]` |

Stages 1 and 2 run before the LLM, so dropped commits cost nothing.

---

## Stage 1: Extraction

- **Merge commits** are skipped (`git log --no-merges`). The work they merged is still counted through the original commits.
- Commits from **every branch** are included, and a commit on several branches is counted once.

## Stage 2: Noise filter (code, no LLM)

A commit is dropped if **any** of these apply:

### Only generated or lock files changed
The commit is dropped when every file it touches matches one of these patterns. A commit that also touches a real source file is kept.

| Kind | Patterns |
|---|---|
| Lock files | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `composer.lock`, `Pipfile.lock`, `poetry.lock` |
| Minified / source maps | `*.min.js`, `*.min.css`, `*.map` |
| Build output | `dist/`, `build/`, `.next/`, `coverage/` |
| Python bytecode | `__pycache__/`, `*.pyc` |

### Spacing-only changes
The added and removed lines are compared with **all whitespace removed**. If they match, the commit is dropped. This covers:
- re-indenting code,
- adding or removing trailing spaces,
- adding or removing blank lines.

A spacing change combined with any real edit is kept.

### Reverts
- A commit whose message starts with **"Revert"** or **"Undo"** (any capitalization) is dropped.
- When git's standard revert message is used (`Revert "<original message>"`), the **original commit is dropped too**. The pair cancels out, so neither is an accomplishment.
- Words that merely contain these letters, like "reverted-state" or "undoable", don't count.

## Stage 3: Impact tagging (LLM)

In the same call that writes each commit's one-sentence summary, the LLM tags it `[MAJOR]` or `[MINOR]`. The definitions in `prompts/diff_analysis.txt`:

| Tag | Covers |
|---|---|
| **[MAJOR]** | A new feature, a user-visible behaviour change, a significant bug fix, a security fix, or a change to architecture, APIs, data models or deployment |
| **[MINOR]** | Typo, formatting, spacing, code-style or linting changes; comment or documentation edits; renames; small refactors; config or dependency tweaks; test-only changes; small cosmetic or copy changes; reverts or undoing earlier work |

Tie-breaker: **"When unsure, choose [MINOR]. Only tag work a team lead would mention in a standup as [MAJOR]."**

Stage 3 is also the fallback for stage 2. Formatting that the code-level checks miss (quote style, line wrapping) and reverts worded differently ("restore old checkout flow") are meant to be tagged `[MINOR]` here.

### Safety nets (in code)
- **Untagged summaries count as major.** If the LLM leaves out the tag, the commit is kept rather than hidden.
- **The commit-message fallback counts as major.** If the LLM gives no usable summary for a commit (for example a reply cut off mid-list), the commit message is used and the commit is kept.
- **If every commit is minor, all are shown.** A quiet period still produces a report rather than an empty one.

---

## Where the result shows up

| Place | What it counts |
|---|---|
| Slack / Email / Standup reports | Major updates only. The developer versions end with "+ N minor updates (small fixes, docs, tweaks) not shown". Client versions omit that note. |
| Developer Stats: **Highlights** | Per person, commits that made it into the reports (passed all three stages) |
| Developer Stats: **Commits** | Per person, every commit in the date range (after stage 1 only) |
| Raw git log | Every commit in the date range (after stage 1 only) |

## Changing the rules

| To change… | Edit |
|---|---|
| Which files count as generated | `GENERATED_FILE_PATTERNS` in `backend/noise_filter.py` |
| Spacing or revert detection | `_is_whitespace_only` / `_REVERT_RE` in `backend/noise_filter.py` |
| What counts as major or minor | The `[MAJOR]` / `[MINOR]` definitions in `prompts/diff_analysis.txt` (the prompt, not code) |
| Keeping or dropping untagged commits | `_split_impact` in `backend/diff_analyzer.py` |

Tests for these rules are in `tests/test_noise_filter.py` and `tests/test_diff_analyzer.py`.

## Known limitations

- **Major/minor is an LLM judgment.** It can vary between runs and models. The prompt leans strict ("when unsure, choose minor").
- **A revert of a revert** (re-applying work) is treated as noise, and the re-applied work is dropped too.
- **Reordering lines** (for example sorting imports) counts as a spacing-only change and is dropped, because only the set of lines is compared.
- **Highlights is a count, not a weight.** A whole new feature and a significant bug fix each count as 1.
