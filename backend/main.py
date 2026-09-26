"""
main.py — FastAPI application entry point for Standup Sync.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import traceback

from backend.git_extractor import extract_commits
from backend.noise_filter import filter_commits
from backend.diff_analyzer import analyze_commits
from backend.grouper import group_commits
from backend.blocker_detector import detect_blockers
from backend.summarizer import build_summary
from backend.renderers import slack_renderer, email_renderer, standup_renderer

app = FastAPI(title="Standup Sync")

# Serve the frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class GenerateRequest(BaseModel):
    repo: str
    since: str = "24 hours ago"
    until: Optional[str] = None


@app.get("/")
def index():
    return FileResponse("frontend/index.html")


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """
    Full pipeline: git extraction → noise filter → LLM analysis →
    grouping → blocker detection → summary object → all three rendered formats.
    """
    try:
        # 1. Extract
        raw_commits = extract_commits(req.repo, req.since, req.until)
        if not raw_commits:
            raise HTTPException(
                status_code=404,
                detail=f"No commits found in '{req.repo}' since '{req.since}'. "
                       "Try a wider date range or check the repo path/URL."
            )

        # 2. Filter
        filtered = filter_commits(raw_commits)
        if not filtered:
            raise HTTPException(
                status_code=404,
                detail="All commits were filtered out (only merge commits, lock files, or "
                       "whitespace changes found). Try a wider date range."
            )

        # 3. Analyze (LLM)
        analyzed = analyze_commits(filtered)

        # 4. Group
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

        # 7. Render all three formats
        return {
            "summary": summary,
            "formats": {
                "slack": slack_renderer.render(summary),
                "email": email_renderer.render(summary),
                "standup": standup_renderer.render(summary),
            },
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@app.get("/health")
def health():
    return {"status": "ok"}
