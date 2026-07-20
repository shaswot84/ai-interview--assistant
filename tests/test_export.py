"""Tests for Markdown and PDF export — output format, content, and file creation."""

from schemas import (
    Evaluation,
    LetterGrade,
    Question,
    QuestionCategory,
    Scorecard,
    Seniority,
    SessionState,
    UserProfile,
)
from export import generate_markdown_transcript, generate_pdf

SAMPLE_STATE = SessionState(
    profile=UserProfile(
        role="Backend Engineer",
        seniority=Seniority.SENIOR,
        industry="FinTech",
        interview_type="technical",
    ),
    questions=[
        Question(id="q1", text="What is REST?", category=QuestionCategory.TECHNICAL),
        Question(id="q2", text="Tell me about a conflict.", category=QuestionCategory.BEHAVIOURAL),
    ],
    transcript={
        "q1": "REST is an architectural style.",
        "q2": None,
    },
    evaluations={
        "q1": Evaluation(
            clarity=8, completeness=7, relevance=9, grammar=6, impact=8,
            technical_depth=7, architecture_design=6, problem_solving=8, tradeoff_analysis=6,
            strengths=["S1", "S2", "S3"], weaknesses=["W1", "W2", "W3"],
            grammar_correction="Fixed.",
            simplified_version="Simple.",
            actionable_feedback="Be specific.",
        ),
    },
    scorecard=Scorecard(
        strengths=["Good communication"],
        improvements=["Be more concise"],
        model_answer="A comprehensive answer...",
        overall_assessment="Solid performance.",
        grade=LetterGrade.B,
    ),
)


class TestGenerateMarkdownTranscript:
    """Markdown transcript should include profile, Q&A, scores, and scorecard."""

    def test_includes_profile(self):
        md = generate_markdown_transcript(SAMPLE_STATE)
        assert "Backend Engineer" in md
        assert "Senior" in md
        assert "FinTech" in md

    def test_includes_questions_and_answers(self):
        md = generate_markdown_transcript(SAMPLE_STATE)
        assert "What is REST?" in md
        assert "REST is an architectural style." in md

    def test_shows_skipped(self):
        md = generate_markdown_transcript(SAMPLE_STATE)
        assert "Skipped" in md or "skipped" in md

    def test_includes_scores(self):
        md = generate_markdown_transcript(SAMPLE_STATE)
        assert "Clarity: 8/10" in md
        assert "Completeness: 7/10" in md

    def test_includes_scorecard(self):
        md = generate_markdown_transcript(SAMPLE_STATE)
        assert "**Grade:** B" in md
        assert "Solid performance." in md

    def test_handles_minimal_state(self):
        state = SessionState()
        md = generate_markdown_transcript(state)
        assert "Interview Transcript" in md


class TestGeneratePDF:
    """PDF export should produce a valid PDF binary file."""

    def test_creates_pdf_file(self, tmp_path):
        path = str(tmp_path / "test.pdf")
        result = generate_pdf(SAMPLE_STATE, path)
        assert result == path
        with open(path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"
