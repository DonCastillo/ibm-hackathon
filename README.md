# Standup Sync

An AI-powered web app that turns a git repository's commit history into human-readable standup notes, Slack updates, and email digests — powered by IBM watsonx.ai (Granite).

Instead of listing commit messages (often vague: "fix bug", "wip"), Standup Sync reads the actual diffs and infers what changed and why, then groups related commits and reports the accomplishments that matter — minor tweaks, formatting changes and reverts are left out.

---

## Demo App

> URL will be added after deployment.

## Video Demo

> Link will be added after recording.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| LLM | IBM watsonx.ai — `ibm/granite-3-8b-instruct` |
| Git access | `git` CLI via Python subprocess |
| Frontend | Plain HTML / CSS / JavaScript (no build step) |
| Deployment | (Render / Railway / IBM Code Engine — TBD) |

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
│   └── index.html            # single-page UI
├── prompts/                  # every LLM prompt used at runtime
│   ├── diff_analysis.txt     # per-commit summary + [MAJOR]/[MINOR] tag
│   ├── render_base.md        # shared frame for the format renderer
│   ├── slack.md, email.md, standup.md          # per-format length rules (plan/format.md)
│   └── audience_developer.md, audience_client.md  # audience/tone rules
├── plan/                     # architecture docs and task checklist
├── deliverables/             # hackathon submission artifacts
├── bob_sessions/             # Bob session screenshots
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

### Render (recommended for a quick public URL)

1. Push this repo to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`

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
| Live demo | _(URL added after deployment)_ |
| Video demo | _(Link added after recording)_ |
| Slide deck | `deliverables/slides.pdf` _(added before submission)_ |
| Bob session screenshots | [`bob_sessions/`](bob_sessions/) |
| LLM prompts used at runtime | [`prompts/`](prompts/) — [`diff_analysis.txt`](prompts/diff_analysis.txt) (per-commit summaries), [`render_base.md`](prompts/render_base.md) + [`slack.md`](prompts/slack.md) / [`email.md`](prompts/email.md) / [`standup.md`](prompts/standup.md) + [`audience_developer.md`](prompts/audience_developer.md) / [`audience_client.md`](prompts/audience_client.md) (output formats) |
| Architecture doc | [`plan/architecture.md`](plan/architecture.md) |
