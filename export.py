import re

from schemas import SessionState


def _md_to_html(md: str) -> str:
    html_parts: list[str] = []
    for line in md.split("\n"):
        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{line[3:]}</h2>")
        elif re.match(r"^\*\*(.+)\*\*$", line.strip()):
            inner = line.strip()[2:-2]
            html_parts.append(f"<p><strong>{inner}</strong></p>")
        elif "**" in line:
            html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            html_parts.append(f"<p>{html}</p>")
        elif line.strip() == "":
            html_parts.append("<br>")
        else:
            html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)


def _html_document(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 800px; margin: 2em auto; padding: 0 1em; line-height: 1.6; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #3B82F6; padding-bottom: 0.3em; }}
  h2 {{ color: #1a1a2e; margin-top: 1.5em; }}
  strong {{ color: #1a1a2e; }}
  p {{ color: #333; margin: 0.5em 0; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def generate_markdown_transcript(state: SessionState) -> str:
    lines: list[str] = ["# Interview Transcript", ""]
    if state.profile:
        lines.append(f"**Role:** {state.profile.role}")
        lines.append(f"**Seniority:** {state.profile.seniority.value}")
        lines.append(f"**Industry:** {state.profile.industry}")
        lines.append("")

    for q in state.questions:
        lines.append(f"## {q.text}")
        answer = state.transcript.get(q.id)
        if answer:
            lines.append(f"**Answer:** {answer}")
        else:
            lines.append("*(Skipped)*")
        eval_ = state.evaluations.get(q.id)
        if eval_:
            dims = ["Clarity", "Completeness", "Relevance", "Grammar", "Impact"]
            scores = [f"{d}: {getattr(eval_, d.lower())}/10" for d in dims]
            lines.append(f"**Scores:** {' | '.join(scores)}")
        lines.append("")

    if state.scorecard:
        lines.append("---")
        lines.append("## Scorecard")
        lines.append(f"**Grade:** {state.scorecard.grade.value}")
        lines.append(f"**Overall Assessment:** {state.scorecard.overall_assessment}")
        lines.append("")
        lines.append("### Strengths")
        for s in state.scorecard.strengths:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("### Areas for Improvement")
        for s in state.scorecard.improvements:
            lines.append(f"- {s}")

    return "\n".join(lines)


def generate_pdf(state: SessionState, path: str) -> str:
    from weasyprint import HTML

    md = generate_markdown_transcript(state)
    body = _md_to_html(md)
    html = _html_document(body)
    HTML(string=html).write_pdf(path)
    return path
