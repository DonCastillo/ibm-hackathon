"""
main.py — FastAPI application entry point for Standup Sync.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging

from backend.git_extractor import extract_commits, RepoAccessError
from backend.noise_filter import filter_commits
from backend.diff_analyzer import analyze_commits
from backend.grouper import group_commits
from backend.summarizer import build_summary, format_log_line
from backend.renderers import format_renderer

app = FastAPI(title="Standup Sync")
logger = logging.getLogger("standup_sync")

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
            raw_log = [format_log_line(c) for c in raw_commits]
            yield _event("raw_log", {"lines": raw_log})

            # 2. Filter
            yield _event("progress", {"step": "filter", "message": f"Filtering {len(raw_commits)} commits…"})
            filtered = filter_commits(raw_commits)
            if not filtered:
                yield _event("error", {
                    "detail": "All commits were filtered out (only merge commits, reverts, lock files, "
                              "or whitespace changes found). Try a wider date range."
                })
                return

            # 3. Analyze (LLM)
            yield _event("progress", {
                "step": "llm",
                "message": f"Analysing {len(filtered)} commits with LLM (this is the slow part)…"
            })
            analyzed = analyze_commits(filtered)

            # 4. Group — reports list only major updates. If nothing was tagged
            # major, show everything rather than an empty report.
            yield _event("progress", {"step": "group", "message": "Grouping commits…"})
            highlights = [c for c in analyzed if c["impact"] == "major"] or analyzed
            groups = group_commits(highlights)

            # 5. Assemble summary
            summary = build_summary(
                repo=req.repo,
                since=req.since,
                until=req.until,
                groups=groups,
                raw_commits=raw_commits,
                omitted_minor=len(analyzed) - len(highlights),
            )

            # 6. Render and stream final result
            yield _event("progress", {"step": "render", "message": "Writing Slack, email and standup updates…"})
            # One LLM call per audience (developer + client), run in parallel
            formats_dev, formats_client = format_renderer.render_all(summary)
            yield _event("result", {
                "summary": summary,
                "formats": formats_dev,
                "formats_client": formats_client,
            })

        except RepoAccessError as e:
            yield _event("error", {"detail": str(e), "code": "repo_access"})

        except ValueError as e:
            # Invalid input, e.g. a local path that isn't a git repository
            yield _event("error", {"detail": str(e)})

        except Exception as e:
            # Full traceback goes to the server log only; the UI gets one readable line
            logger.exception("Report generation failed for %s", req.repo)
            first_line = (str(e).strip().splitlines() or [type(e).__name__])[0][:300]
            yield _event("error", {
                "detail": f"Something went wrong while generating the report: {first_line}"
            })

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}
