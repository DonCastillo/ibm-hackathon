"""
slack_renderer.py
Pure function: summary dict -> Slack-formatted string.
"""

from backend.summarizer import omitted_note


def render(summary: dict) -> str:
    repo = summary["repo"]
    since = summary["range"]["since"]
    until = summary["range"]["until"]

    lines = [
        f"*📋 Standup Sync — `{repo}`*",
        f"_{since}  →  {until}_",
        "",
    ]

    for group in summary["groups"]:
        theme = group["theme"]
        authors = ", ".join(group["authors"])
        lines.append(f"*{theme}* _(by {authors})_")
        for commit in group["commits"]:
            lines.append(f"  • {commit.get('summary', commit['message'])}")
        lines.append("")

    if note := omitted_note(summary):
        lines += [f"_{note}_", ""]

    if summary["blockers"]:
        lines.append("*⚠️ Possible blockers*")
        for b in summary["blockers"]:
            if b["reason"] == "repeated_changes":
                lines.append(f"  • `{b['target']}` was modified in 3+ commits — may indicate rework")
            elif b["reason"] == "possible_struggle":
                lines.append(f"  • Commit `{b['target'][:7]}` flagged: _{b.get('message', '')}_ ")
        lines.append("")

    return "\n".join(lines)
