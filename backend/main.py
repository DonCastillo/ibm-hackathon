"""
main.py — FastAPI application entry point for Standup Sync.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import traceback

from backend.git_extractor import extract_commits
from backend.noise_filter import filter_commits
from backend.diff_analyzer import analyze_commits
from backend.grouper import group_commits
from backend.blocker_detector import detect_blockers
from backend.summarizer import build_summary
from backend.renderers import slack_renderer, email_renderer, standup_renderer, client_renderer

app = FastAPI(title="Standup Sync")

# Serve the frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class GenerateRequest(BaseModel):
    repo: str
    since: str = "24 hours ago"
    until: Optional[str] = None
    token: Optional[str] = None


def _event(event: str, data: dict) -> str:
    """Format a Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/")
def index():
    return FileResponse("frontend/index.html")


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """
    Full pipeline streamed as Server-Sent Events so the UI updates in real time.
    Events: progress | raw_log | result | error
    """
    def stream():
        try:
            # 1. Extract
            yield _event("progress", {"step": "clone", "message": "Cloning / reading repo…"})
            raw_commits = extract_commits(req.repo, req.since, req.until, req.token)
            if not raw_commits:
                yield _event("error", {
                    "detail": f"No commits found in '{req.repo}' since '{req.since}'. "
                              "Try a wider date range or check the repo path/URL."
                })
                return

            # Send raw log immediately so the "before" panel appears early
            raw_log = [f"{c['hash'][:7]} {c['author']} — {c['message']}" for c in raw_commits]
            yield _event("raw_log", {"lines": raw_log})

            # 2. Filter
            yield _event("progress", {"step": "filter", "message": f"Filtering {len(raw_commits)} commits…"})
            filtered = filter_commits(raw_commits)
            if not filtered:
                yield _event("error", {
                    "detail": "All commits were filtered out (only merge commits, lock files, or "
                              "whitespace changes found). Try a wider date range."
                })
                return

            # 3. Analyze (LLM)
            yield _event("progress", {
                "step": "llm",
                "message": f"Analysing {len(filtered)} commits with LLM (this is the slow part)…"
            })
            analyzed = analyze_commits(filtered)

            # 4. Group
            yield _event("progress", {"step": "group", "message": "Grouping commits…"})
            groups = group_commits(analyzed)

            # 5. Detect blockers
            blockers = detect_blockers(analyzed)

            # 6. Assemble summary
            summary = build_summary(
                repo=req.repo,
                since=req.since,
                until=req.until,
                groups=groups,
                blockers=blockers,
                raw_commits=raw_commits,
            )

            # 7. Render and stream final result
            yield _event("progress", {"step": "render", "message": "Rendering output…"})
            formats_dev = {
                "slack":   slack_renderer.render(summary),
                "email":   email_renderer.render(summary),
                "standup": standup_renderer.render(summary),
            }
            formats_client = client_renderer.render_all(summary)
            yield _event("result", {
                "summary": summary,
                "formats": formats_dev,
                "formats_client": formats_client,
            })

        except Exception:
            yield _event("error", {"detail": traceback.format_exc()})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}
