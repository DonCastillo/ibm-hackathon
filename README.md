# Standup Sync

An AI-powered web app that turns a git repository's commit history into human-readable standup notes, Slack updates, and email digests. Built with IBM Bob; runs on Claude Haiku 4.5 or IBM watsonx.ai.

Instead of listing commit messages (often vague: "fix bug", "wip"), Standup Sync reads the actual diffs and infers what changed, then groups related commits and reports the accomplishments that matter — minor tweaks, formatting changes and reverts are left out (see [`plan/filtering.md`](plan/filtering.md) for the exact rules).

---

## Demo App

**Live demo:** [standup-sync.onrender.com](https://standup-sync.onrender.com). Go straight to the app at [/standup](https://standup-sync.onrender.com/standup).

> Hosted on Render's free plan: if the app has been idle, the first visit takes about 30 seconds to wake it up. Paste any public repository URL (or a private one with a Personal Access Token) and pick a date range.

## Video Demo

> Link will be added after recording.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| LLM | Anthropic **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`, used by the live demo) or **IBM watsonx.ai** (`mistralai/mistral-small-3-1-24b-instruct-2503`). Switch with `LLM_PROVIDER`; all calls go through `backend/llm_client.py` |
| Git access | `git` CLI via Python subprocess (blobless shallow clones of every branch) |
| Frontend | Plain HTML / CSS / JavaScript, no build step. VS Code–style UI with the Monokai theme, Codicons, JetBrains Mono |
| Testing | pytest (offline unit/API tests with the LLM stubbed, plus network tests against real public repos) |
| Deployment | Render (free web service, [`render.yaml`](render.yaml) blueprint) |
| Built with | **IBM Bob** (see [How IBM Bob was used](#how-ibm-bob-was-used)) and Claude Code |

---

## How IBM Bob was used

IBM Bob built the first working version of Standup Sync in three sessions on Sept 26, 2026 (1:48 pm – 11:44 pm). The full exports and screenshots of every session are in [`bob_sessions/`](bob_sessions/).

| Session | What Bob was asked | What Bob produced |
|---|---|---|
| **1. Build the pipeline** (`2307d219`, 1:48–5:51 pm, 32 prompts) | Assess the timeline from `AGENTS.md` and `plan/`; walk through the first steps; set up IBM watsonx.ai (project, runtime service, credentials); fix runtime errors; speed up generation; add Anthropic as an alternative LLM | The whole backend pipeline and first UI: git extraction, noise filter, diff analysis prompt, grouping, blocker detection, summary object, Slack/Email/Standup renderers, FastAPI app with live progress streaming, `index.html`, `.gitignore`, README. Used IBM docs search to guide the watsonx.ai setup, and debugged the watsonx and Anthropic clients (commits `c84e688`–`437bb98`) |
| **2. Cost and speed** (`8a459f48`, 5:55–6:32 pm, 12 prompts) | How many LLM calls run per click? Why is cloning slow? What does an LLM call cost? Why do summaries look like the commit messages? | Explained the pipeline's LLM calls and costs; switched to a bare, blobless clone (`--bare --filter=blob:none`) so only git history is downloaded; raised the diff limit to 4,000 characters so the LLM reads whole diffs (`c26e7c6`, `827fe4b`) |
| **3. Features and UI** (`2431acda`, 6:59–11:44 pm, 16 prompts) | Per-developer contribution stats; a developer/client tone toggle; which repository URLs work; private repositories; date-range presets; separating HTML, CSS and JS | Planned the stats UI (`plan/developer-stats-ui-plan.md`, on the `ui` branch), then built the Developer Stats table, client-facing output formats (`client_summary.txt`, `client_renderer.py`), tooltips, Personal Access Token support for GitHub/GitLab/Bitbucket/Azure DevOps, date presets with a custom range and validation, and split the frontend into HTML/CSS/JS (`e2b3c52`–`6ec6519`) |

From Sept 27 onward, development continued with Claude Code: the test suite and the bugs it found, all-branch analysis, the accomplishments-only filtering (`plan/filtering.md`), the LLM-written output formats (`plan/format.md`), the VS Code–style UI redesign (`plan/UI.md`) and deployment.

---

## Project Structure

```
standup-sync/
├── backend/
│   ├── main.py               # FastAPI app + pipeline orchestration
│   ├── git_extractor.py      # git log -p → structured commits
│   ├── noise_filter.py       # drop merges, lockfiles, whitespace diffs
│   ├── llm_client.py         # single LLM call entry point (watsonx.ai)
│   ├── diff_analyzer.py      # batch commits → LLM → per-commit summaries
│   ├── grouper.py            # cluster commits by directory/author
│   ├── summarizer.py         # assemble canonical summary object
│   └── renderers/
│       └── format_renderer.py # Slack / Email / Standup × developer / client (2 LLM calls)
├── frontend/
│   ├── landing.html, landing.css  # landing page (/)
│   ├── standup.html          # the app (/standup) — VS Code / Monokai look, see plan/UI.md
│   ├── theme.css             # Monokai tokens + editor chrome, shared by all pages
│   ├── standup.css, app.js   # app page styles and logic
│   ├── chrome.js             # shared editor chrome: command palette (⌘K)
│   └── logo.svg              # logo + favicon
├── prompts/                  # every LLM prompt used at runtime
│   ├── diff_analysis.txt     # per-commit summary + [MAJOR]/[MINOR] tag
│   ├── render_base.md        # shared frame for the format renderer
│   ├── slack.md, email.md, standup.md          # per-format length rules (plan/format.md)
│   └── audience_developer.md, audience_client.md  # audience/tone rules
├── plan/                     # architecture docs and task checklist
├── deliverables/             # hackathon submission artifacts
├── bob_sessions/             # IBM Bob session exports (JSON) + screenshots
├── tests/                    # pytest suite (see "Run the tests")
├── .env.example
├── requirements.txt
├── requirements-dev.txt      # + pytest, httpx
└── README.md
```

---

## Run Locally

### Prerequisites

- Python 3.11+
- `git` installed and on your PATH
- IBM watsonx.ai credentials (API key + Project ID)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/DonCastillo/ibm-hackathon.git
cd ibm-hackathon

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up credentials
cp .env.example .env
# Edit .env and fill in WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL
# (or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY). ALLOW_LOCAL_REPOS=1 lets you analyse local folders.

# 5. Start the server
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

### Run the tests

The LLM is stubbed in tests, so no credentials are needed and nothing is billed.

```bash
pip install -r requirements-dev.txt

pytest                 # offline unit/API tests + network tests against small public repos (~1 min)
pytest -m "not network"  # offline only (~5 s)
pytest -m slow -s      # opt-in: huge repos (react, vscode, …) — clone timing across hundreds of branches
```

See [`tests/tests.md`](tests/tests.md) for what was tested, bugs found and fixed, and known open issues.

| File | Covers |
|---|---|
| `tests/test_git_extractor.py` | All-branches extraction, date ranges, diff stats, shallow-clone completeness (no lost commits on busy repos), private-repo / token / SSH errors — using throwaway local repos |
| `tests/test_diff_analyzer.py` | Mapping LLM replies back to commits: truncated replies, intro lines, skipped/out-of-order numbers, per-batch token budget |
| `tests/test_api.py` | `/api/generate` SSE stream end to end: happy path, no commits, lock-file-only, invalid path, private repo |
| `tests/test_remote_repos.py` | Real public repos: frozen (`octocat/Hello-World`), active, quiet, `.git` URLs, SSH, bad token, unreachable host |

---

## Deploy

> **Security:** do not set `ALLOW_LOCAL_REPOS` on a public deployment. Without it, the server only accepts repository URLs, so visitors cannot read repos stored on the server's disk.

### Render (recommended for a quick public URL)

The repo includes a [`render.yaml`](render.yaml) blueprint, so Render picks up every setting automatically.

1. Push this repo to GitHub.
2. On [render.com](https://render.com): **New → Blueprint**, then select this repository.
3. When prompted, enter `ANTHROPIC_API_KEY`. To use IBM watsonx.ai instead, change `LLM_PROVIDER` to `watsonx` and add `WATSONX_API_KEY`, `WATSONX_PROJECT_ID` and `WATSONX_URL` in the service's **Environment** tab.
4. Click **Apply** and wait for the first build (a few minutes).
5. Open the service URL (e.g. `https://standup-sync.onrender.com`) in an incognito window and run one report on a public repository URL.

What the blueprint sets: Python 3.11 (from `.python-version`), build `pip install -r requirements.txt`, start `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, health check `/health`, auto-deploy on every push to `main`.

On the free plan the service sleeps when idle, so the first request after a while takes about 30 seconds.

### IBM Cloud Code Engine

```bash
ibmcloud ce application create \
  --name standup-sync \
  --image <your-container-image> \
  --env WATSONX_API_KEY=... \
  --env WATSONX_PROJECT_ID=... \
  --env WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

---

## Project Deliverables

For hackathon judges — links to all submission artifacts:

| Artifact | Link |
|---|---|
| Source code | [github.com/DonCastillo/ibm-hackathon](https://github.com/DonCastillo/ibm-hackathon) |
| Live demo | [standup-sync.onrender.com](https://standup-sync.onrender.com) (app: [/standup](https://standup-sync.onrender.com/standup)) |
| Video demo | _(Link added after recording)_ |
| Slide deck | `deliverables/slides.pdf` _(added before submission)_ |
| How IBM Bob was used | [README → How IBM Bob was used](#how-ibm-bob-was-used) |
| Bob session exports + screenshots | [`bob_sessions/`](bob_sessions/) |
| LLM prompts used at runtime | [`prompts/`](prompts/) — [`diff_analysis.txt`](prompts/diff_analysis.txt) (per-commit summaries), [`render_base.md`](prompts/render_base.md) + [`slack.md`](prompts/slack.md) / [`email.md`](prompts/email.md) / [`standup.md`](prompts/standup.md) + [`audience_developer.md`](prompts/audience_developer.md) / [`audience_client.md`](prompts/audience_client.md) (output formats) |
| Architecture doc | [`plan/architecture.md`](plan/architecture.md) |
| What counts as an accomplishment (noise filter + major/minor rules) | [`plan/filtering.md`](plan/filtering.md) |
