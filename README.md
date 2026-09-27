# Standup Sync

An AI-powered web app that turns a git repository's commit history into human-readable standup notes, Slack updates, and email digests — powered by IBM watsonx.ai (Granite).

Instead of listing commit messages (often vague: "fix bug", "wip"), Standup Sync reads the actual diffs and infers what changed and why, then groups related commits and flags likely blockers.

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
│   ├── blocker_detector.py   # flag repeated files, revert/wip patterns
│   ├── summarizer.py         # assemble canonical summary object
│   └── renderers/
│       ├── slack_renderer.py
│       ├── email_renderer.py
│       └── standup_renderer.py
├── frontend/
│   └── index.html            # single-page UI
├── prompts/
│   └── diff_analysis.txt     # LLM prompt template used at runtime
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

| File | Covers |
|---|---|
| `tests/test_git_extractor.py` | All-branches extraction, date ranges, diff stats, private-repo / token / SSH errors — using throwaway local repos |
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
| LLM prompts used at runtime | [`prompts/diff_analysis.txt`](prompts/diff_analysis.txt) |
| Architecture doc | [`plan/architecture.md`](plan/architecture.md) |
