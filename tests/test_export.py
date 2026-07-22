"""Tests for Markdown and PDF export — output format, content, and file creation."""

from schemas import (
    Competency,
    Evaluation,
    LetterGrade,
    Question,
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
        Question(id="q1", text="What is REST?", category=Competency.API_DESIGN),
        Question(id="q2", text="Tell me about a conflict.", category=Competency.COMMUNICATION),
    ],
    transcript={
        "q1": "REST is an architectural style.",
        "q2": None,
    },
    evaluations={
        "q1": Evaluation(
            scores={"clarity": 8, "completeness": 7, "relevance": 9, "correctness": 8},
            strengths=["S1", "S2", "S3"], weaknesses=["W1", "W2", "W3"],
            grammar_correction="Fixed.",
            simplified_version="Simple.",
            actionable_feedback="Be specific.",
        ),
    },
    scorecard=Scorecard(
        overall_assessment="Solid performance.",
        hiring_recommendation="Hire",
        candidate_readiness="Ready for Senior level.",
        strongest_competencies=[{"competency": "API Design", "why": "Strong."}],
        weakest_competencies=[{"competency": "Trade-offs", "why": "Missed."}],
        recurring_patterns=["Good fundamentals."],
        key_concepts_missed=["Caching"],
        learning_roadmap=[{"priority": 1, "area": "Design", "reason": "Gap", "study": "Practice."}],
        learning_resources=[{"name": "DDIA", "description": "Book.", "url": "https://example.com"}],
        overall_score=82.0,
        grade=LetterGrade.B,
        question_table=[
            {"id": "q1", "text": "What is REST?", "category": "api_design",
             "score": 82, "hiring_decision": "Hire", "confidence": 0.85, "performance_label": "Strong"},
        ],
        dimension_averages={"clarity": 8.0, "completeness": 7.0, "relevance": 9.0, "correctness": 8.0},
        stats={"total_questions": 2, "answered": 1, "skipped": 1, "overall_score": 82.0},
        radar_interpretation="Strongest area: clarity.",
        confidence_notice="",
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
        assert "Correctness: 8/10" in md

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
