"""
Shared fixtures.

- `git_repo` builds throwaway local git repos with controlled branches, authors and dates.
- `fake_llm` stubs every LLM call so tests are free, fast and deterministic.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# backend.main mounts "frontend" relative to the working directory
os.chdir(ROOT)


class GitRepo:
    """A real git repo in a temp dir with helpers for dated commits on any branch."""

    def __init__(self, path: Path):
        self.path = path
        self._git("init", "-q", "-b", "main")

    def _git(self, *args: str, env: dict | None = None) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True, text=True, check=True,
            env={**os.environ, **(env or {})},
        )
        return result.stdout.strip()

    def commit(self, message: str, files: dict[str, str], author: str = "Alice", date: str | None = None) -> str:
        """Write files and commit them. `date` is any git date, e.g. '2026-09-20T10:00:00'."""
        for name, content in files.items():
            f = self.path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        self._git("add", "-A")
        env = {
            "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": f"{author.lower()}@example.com",
            "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": f"{author.lower()}@example.com",
        }
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self._git("commit", "-q", "-m", message, env=env)
        return self._git("rev-parse", "HEAD")

    def delete(self, name: str, message: str, author: str = "Alice") -> None:
        self._git("rm", "-q", name)
        self._git("commit", "-q", "-m", message, env={
            "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@example.com",
            "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": "a@example.com",
        })

    def branch(self, name: str) -> None:
        self._git("checkout", "-q", "-b", name)

    def checkout(self, name: str) -> None:
        self._git("checkout", "-q", name)

    def merge(self, name: str, date: str | None = None) -> None:
        env = {"GIT_COMMITTER_NAME": "Alice", "GIT_COMMITTER_EMAIL": "a@example.com",
               "GIT_AUTHOR_NAME": "Alice", "GIT_AUTHOR_EMAIL": "a@example.com"}
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self._git("merge", "-q", "--no-ff", "-m", f"Merge {name}", name, env=env)


@pytest.fixture
def git_repo(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    return GitRepo(repo_dir)


@pytest.fixture
def fake_llm(monkeypatch):
    """
    Replace the LLM with a stub that returns one numbered, impact-tagged summary
    per commit: [MINOR] if the commit message starts with "minor:", else [MAJOR].
    """
    calls = []

    def fake_generate(prompt: str, max_tokens: int = 200) -> str:
        calls.append(prompt)
        messages = re.findall(r"^Message: (.+)$", prompt, re.MULTILINE)
        if messages:
            return "\n".join(
                f"{i}. [{'MINOR' if m.startswith('minor:') else 'MAJOR'}] Summary of {m}."
                for i, m in enumerate(messages, 1)
            )
        return "Client-facing narrative."

    monkeypatch.setattr("backend.diff_analyzer.generate", fake_generate)
    monkeypatch.setattr("backend.renderers.client_renderer.generate", fake_generate)
    return calls
