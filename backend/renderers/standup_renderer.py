"""
standup_renderer.py
Pure function: summary dict -> standup notes grouped by author.
"""

from collections import defaultdict

from backend.summarizer import omitted_note


def render(summary: dict) -> str:
    repo = summary["repo"]
    since = summary["range"]["since"]
    until = summary["range"]["until"]

    # Re-group commits by author instead of theme
    by_author: dict[str, list[dict]] = defaultdict(list)
    for group in summary["groups"]:
        for commit in group["commits"]:
            by_author[commit["author"]].append({
                **commit,
                "theme": group["theme"],
            })

    lines = [
        f"STANDUP NOTES — {repo}",
        f"{since} → {until}",
        "",
    ]

    for author, commits in sorted(by_author.items()):
        lines.append(f"👤 {author}")
        lines.append("  What I did:")
        for c in commits:
            lines.append(f"    • [{c['theme']}] {c.get('summary', c['message'])}")

        lines.append("")

    if note := omitted_note(summary):
        lines.append(note)

    return "\n".join(lines)
