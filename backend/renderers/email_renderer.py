"""
email_renderer.py
Pure function: summary dict -> email-formatted string (plain text).
"""

from backend.summarizer import omitted_note


def render(summary: dict) -> str:
    repo = summary["repo"]
    since = summary["range"]["since"]
    until = summary["range"]["until"]

    lines = [
        f"Subject: Project Update — {repo}",
        f"Period: {since} to {until}",
        "",
        "Hi team,",
        "",
        "Here's a summary of recent progress:",
        "",
    ]

    for group in summary["groups"]:
        theme = group["theme"].upper()
        authors = ", ".join(group["authors"])
        lines.append(f"[{theme}] — {authors}")
        for commit in group["commits"]:
            lines.append(f"  - {commit.get('summary', commit['message'])}")
        lines.append("")

    if note := omitted_note(summary):
        lines += [f"({note}.)", ""]

    lines.append("Best,")
    lines.append("Standup Sync")

    return "\n".join(lines)
