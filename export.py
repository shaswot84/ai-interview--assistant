"""Export utilities — generates Markdown transcripts and PDF documents with radar charts."""

import re

import plotly.io as pio

from schemas import SessionState


def _md_to_html(md: str) -> str:
    """Convert a small subset of Markdown to inline HTML for WeasyPrint."""
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
    """Wrap body HTML in a full <html> document with basic styling."""
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


def generate_scorecard_markdown(state: SessionState) -> str:
    """Build a Markdown export of the full scorecard (mirrors _show_scorecard UI).

    Starts from 'Interview Complete' and ends at 'Recommended Resources'.
    Preserves headings, tables, bullet points, scores, feedback, and recommendations.
    """
    sc = state.scorecard
    if sc is None:
        return "# No scorecard available."

    lines: list[str] = []
    lines.append("# \U0001f3c6 Interview Complete")
    lines.append("")
    lines.append(f"**Final Grade:** {sc.grade.value}  |  **Overall Score:** {sc.overall_score:.0f}/100")
    lines.append("")
    if sc.hiring_recommendation:
        lines.append(f"**Hiring Recommendation:** {sc.hiring_recommendation}")
        lines.append("")
    if sc.confidence_notice:
        lines.append(sc.confidence_notice)
        lines.append("")

    if sc.overall_assessment:
        lines.append("## \U0001f4ca Overall Assessment")
        lines.append("")
        lines.append(sc.overall_assessment)
        lines.append("")

    if sc.candidate_readiness:
        lines.append("## \U0001f3af Candidate Readiness")
        lines.append("")
        lines.append(sc.candidate_readiness)
        lines.append("")

    stats = sc.stats
    if stats:
        lines.append("## \U0001f4c8 Interview Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Questions | {stats.get('total_questions', 0)} ({stats.get('answered', 0)} answered, {stats.get('skipped', 0)} skipped) |")
        lines.append(f"| Average Score | {stats.get('overall_score', 0):.0f}/100 |")
        lines.append(f"| Highest | {stats.get('highest_score', 0)} |  | Lowest | {stats.get('lowest_score', 0)} |")
        lines.append(f"| Avg Confidence | {stats.get('avg_confidence', 0):.2f} |")
        type_dist = stats.get("type_distribution", {})
        if type_dist:
            types_str = ", ".join(f"{t}: {n}" for t, n in sorted(type_dist.items()))
            lines.append(f"| Types | {types_str} |")
        lines.append("")

    qtable = sc.question_table
    if qtable:
        lines.append("## \U0001f4cb Question-by-Question")
        lines.append("")
        lines.append("| # | Question | Category | Score | Rating |")
        lines.append("|---|----------|----------|-------|--------|")
        for row in qtable:
            emoji = {"Excellent": "\u2705", "Strong": "\u2705", "Adequate": "\u26a0\ufe0f", "Weak": "\u274c", "Poor": "\u274c"}.get(
                row["performance_label"], ""
            )
            text = row["text"][:80] + ("..." if len(row["text"]) > 80 else "")
            lines.append(
                f"| {row['id'][1:]} | {text} | {row['category']} | "
                f"{row['score']}/100 | {emoji} {row['performance_label']} |"
            )
        lines.append("")

    if sc.strongest_competencies:
        lines.append("## \u2705 Strongest Competencies")
        lines.append("")
        for comp in sc.strongest_competencies:
            lines.append(f"- **{comp.get('competency', '')}**: {comp.get('why', '')}")
        lines.append("")

    if sc.weakest_competencies:
        lines.append("## \u274c Weakest Competencies")
        lines.append("")
        for comp in sc.weakest_competencies:
            lines.append(f"- **{comp.get('competency', '')}**: {comp.get('why', '')}")
        lines.append("")

    if sc.recurring_patterns:
        lines.append("## \U0001f501 Recurring Patterns")
        lines.append("")
        for pat in sc.recurring_patterns:
            lines.append(f"- {pat}")
        lines.append("")

    if sc.key_concepts_missed:
        lines.append("## \U0001f511 Key Concepts Missed")
        lines.append("")
        for concept in sc.key_concepts_missed:
            lines.append(f"- {concept}")
        lines.append("")

    if sc.radar_interpretation:
        lines.append("## \U0001f4e1 Radar Chart Interpretation")
        lines.append("")
        lines.append(f"> {sc.radar_interpretation}")
        lines.append("")

    if sc.learning_roadmap:
        lines.append("## \U0001f4da Learning Roadmap")
        lines.append("")
        for item in sc.learning_roadmap:
            lines.append(f"### Priority {item.get('priority', '?')} \u2014 {item.get('area', '')}")
            lines.append("")
            lines.append(f"{item.get('reason', '')}  |  Study: *{item.get('study', '')}*")
            lines.append("")

    if sc.learning_resources:
        lines.append("## \U0001f4d6 Recommended Resources")
        lines.append("")
        for res in sc.learning_resources:
            url = res.get("url", "")
            name = res.get("name", "")
            desc = res.get("description", "")
            lines.append(f"- [{name}]({url}) \u2014 {desc}")
        lines.append("")

    return "\n".join(lines)


def generate_markdown_transcript(state: SessionState) -> str:
    """Build a Markdown transcript string from the session state (profile, Q&A, scorecard)."""
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
        if eval_ and eval_.scores:
            parts = [f"{k.capitalize()}: {v}/10" for k, v in eval_.scores.items()]
            lines.append(f"**Scores:** {' | '.join(parts)}")
        lines.append("")

    if state.scorecard:
        lines.append("---")
        lines.append("## Scorecard")
        lines.append(f"**Grade:** {state.scorecard.grade.value}")
        lines.append(f"**Overall Score:** {state.scorecard.overall_score:.0f}/100")
        if state.scorecard.hiring_recommendation:
            lines.append(f"**Hiring Recommendation:** {state.scorecard.hiring_recommendation}")
        lines.append(f"**Overall Assessment:** {state.scorecard.overall_assessment}")
        lines.append("")
        if state.scorecard.strongest_competencies:
            lines.append("### Strongest Competencies")
            for c in state.scorecard.strongest_competencies:
                lines.append(f"- **{c.get('competency', '')}**: {c.get('why', '')}")
            lines.append("")
        if state.scorecard.weakest_competencies:
            lines.append("### Weakest Competencies")
            for c in state.scorecard.weakest_competencies:
                lines.append(f"- **{c.get('competency', '')}**: {c.get('why', '')}")
            lines.append("")
        if state.scorecard.recurring_patterns:
            lines.append("### Recurring Patterns")
            for p in state.scorecard.recurring_patterns:
                lines.append(f"- {p}")
            lines.append("")
        if state.scorecard.key_concepts_missed:
            lines.append("### Key Concepts Missed")
            for k in state.scorecard.key_concepts_missed:
                lines.append(f"- {k}")
            lines.append("")
        if state.scorecard.learning_roadmap:
            lines.append("### Learning Roadmap")
            for item in state.scorecard.learning_roadmap:
                lines.append(f"- **P{item.get('priority', '?')} — {item.get('area', '')}**: {item.get('study', '')}")
            lines.append("")
        if state.scorecard.learning_resources:
            lines.append("### Recommended Resources")
            for r in state.scorecard.learning_resources:
                lines.append(f"- [{r.get('name', '')}]({r.get('url', '')}) — {r.get('description', '')}")
            lines.append("")

    return "\n".join(lines)


def _radar_chart_html(state: SessionState) -> str:
    """Render the radar chart as a base64-embedded PNG <img> tag for PDF inclusion."""
    if not state.evaluations:
        return ""
    from scoring import prepare_radar_chart_data, render_radar_chart
    import base64, io
    data = prepare_radar_chart_data(state.evaluations)
    fig = render_radar_chart(data)
    img_bytes = pio.to_image(fig, format="png", width=600, height=400, scale=2)
    b64 = base64.b64encode(img_bytes).decode()
    return f'<div style="text-align:center;margin:2em 0;"><img src="data:image/png;base64,{b64}" alt="Radar Chart" style="max-width:100%;height:auto;"></div>'


def generate_pdf(state: SessionState, path: str) -> str:
    """Generate a PDF at `path` from the session state via WeasyPrint."""
    from weasyprint import HTML

    md = generate_markdown_transcript(state)
    body = _md_to_html(md)
    radar = _radar_chart_html(state)
    html = _html_document(body + radar)
    HTML(string=html).write_pdf(path)
    return path
