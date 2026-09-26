"""
email_renderer.py
Pure function: summary dict -> email-formatted string (plain text).
"""


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

    if summary["blockers"]:
        lines.append("WATCH ITEMS")
        lines.append("-" * 40)
        for b in summary["blockers"]:
            if b["reason"] == "repeated_changes":
                lines.append(f"  - {b['target']}: modified repeatedly, possible rework or ongoing issue.")
            elif b["reason"] == "possible_struggle":
                lines.append(f"  - Commit {b['target'][:7]}: '{b.get('message', '')}' — may indicate a struggle.")
        lines.append("")

    lines.append("Best,")
    lines.append("Standup Sync")

    return "\n".join(lines)
