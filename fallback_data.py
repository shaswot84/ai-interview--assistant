"""Static fallback question bank used when the LLM API is unavailable.

Provides 10 questions per seniority level, each targeting a distinct competency,
ordered easiest → hardest, with realistic scenarios replacing cliché definitions.
"""

from schemas import Competency, Question, QuestionConfig, QuestionType, Seniority

_BEHAVIOURAL_COMPETENCIES = {Competency.COMMUNICATION, Competency.LEADERSHIP, Competency.OWNERSHIP}


# Pool of static questions indexed by seniority level
FALLBACK_QUESTIONS: dict[str, list[Question]] = {
    "Junior": [
        Question(id="f1", text="Explain the difference between a list and a tuple in Python.", category=Competency.ALGORITHMS),
        Question(id="f2", text="How would you debug a program that crashes only on startup?", category=Competency.DEBUGGING),
        Question(id="f3", text="How would you test a function that validates email addresses?", category=Competency.TESTING),
        Question(id="f4", text="Tell me about a time you resolved a conflict in a team.", category=Competency.COMMUNICATION),
        Question(id="f5", text="How do you prioritise tasks when you have multiple deadlines?", category=Competency.PROBLEM_SOLVING),
        Question(id="f6", text="What is version control and why is it important?", category=Competency.OWNERSHIP),
        Question(id="f7", text="How would you design an API endpoint to process payment notifications?", category=Competency.API_DESIGN),
        Question(id="f8", text="Describe a project you contributed to and your role in its success.", category=Competency.LEADERSHIP),
        Question(id="f9", text="What factors would you consider when choosing between TCP and UDP for a chat application?", category=Competency.TRADEOFF_ANALYSIS),
        Question(id="f10", text="How can you protect a web application from SQL injection attacks?", category=Competency.SECURITY),
    ],
    "Mid": [
        Question(id="f11", text="Design a scalable web application architecture for an e-commerce platform.", category=Competency.SYSTEM_DESIGN),
        Question(id="f12", text="How would you optimise a slow database query in a production system?", category=Competency.PERFORMANCE),
        Question(id="f13", text="Describe the concept of idempotency in APIs and why it matters.", category=Competency.API_DESIGN),
        Question(id="f14", text="Tell me about a time you had to refactor a large codebase.", category=Competency.OWNERSHIP),
        Question(id="f15", text="Describe a situation where you had to balance speed and quality.", category=Competency.TRADEOFF_ANALYSIS),
        Question(id="f16", text="How would you roll out a deployment that affects thousands of users?", category=Competency.RELIABILITY_ENGINEERING),
        Question(id="f17", text="How would you debug a performance regression after a production deployment?", category=Competency.DEBUGGING),
        Question(id="f18", text="Tell me about a technical decision you disagreed with and how you handled it.", category=Competency.LEADERSHIP),
        Question(id="f19", text="What is eventual consistency and when would you use it?", category=Competency.DISTRIBUTED_SYSTEMS),
        Question(id="f20", text="How do you mentor junior developers on your team?", category=Competency.COMMUNICATION),
    ],
    "Senior": [
        Question(id="f21", text="Design a system that handles millions of requests per day with high availability.", category=Competency.SYSTEM_DESIGN),
        Question(id="f22", text="How do you approach incident response and post-mortems?", category=Competency.RELIABILITY_ENGINEERING),
        Question(id="f23", text="Explain how you would implement distributed consensus in a multi-region system.", category=Competency.CONCURRENCY),
        Question(id="f24", text="Describe a time you drove a significant architectural change.", category=Competency.LEADERSHIP),
        Question(id="f25", text="How do you align technical strategy with business goals?", category=Competency.COMMUNICATION),
        Question(id="f26", text="What patterns do you use for error handling in distributed systems?", category=Competency.DISTRIBUTED_SYSTEMS),
        Question(id="f27", text="How do you ensure observability in production systems?", category=Competency.OBSERVABILITY),
        Question(id="f28", text="Tell me about a cross-team initiative you led and the outcome.", category=Competency.OWNERSHIP),
        Question(id="f29", text="Explain CAP theorem with real-world examples and tradeoffs.", category=Competency.TRADEOFF_ANALYSIS),
        Question(id="f30", text="How would you diagnose and fix a memory leak in a production service?", category=Competency.DEBUGGING),
    ],
    "Lead": [
        Question(id="f31", text="Describe how you would structure an engineering org for a 50-person team.", category=Competency.LEADERSHIP),
        Question(id="f32", text="How do you balance technical debt against feature delivery?", category=Competency.TRADEOFF_ANALYSIS),
        Question(id="f33", text="What metrics do you use to measure engineering performance?", category=Competency.PERFORMANCE),
        Question(id="f34", text="Tell me about a time you turned around a struggling team.", category=Competency.COMMUNICATION),
        Question(id="f35", text="How do you foster a culture of psychological safety?", category=Competency.OWNERSHIP),
        Question(id="f36", text="Explain how you approach technology selection for a new product.", category=Competency.SYSTEM_DESIGN),
        Question(id="f37", text="What is your approach to succession planning in engineering?", category=Competency.LEADERSHIP),
        Question(id="f38", text="Describe a difficult personnel decision you had to make.", category=Competency.PROBLEM_SOLVING),
        Question(id="f39", text="How do you ensure engineering scalability as the team grows?", category=Competency.DISTRIBUTED_SYSTEMS),
        Question(id="f40", text="Tell me about a time you influenced a company-wide decision.", category=Competency.COMMUNICATION),
    ],
}


def _is_technical(category: Competency) -> bool:
    """Return True if the competency is a technical (non-behavioural) one."""
    return category not in _BEHAVIOURAL_COMPETENCIES


def fallback_questions(profile, needed: int = 5, question_config: QuestionConfig | None = None) -> list[Question]:
    """Return up to `needed` static questions from the fallback bank for the given seniority.

    Each question targets a distinct competency. When a config is supplied,
    distributes questions according to the requested types.
    """
    key = profile.seniority.value if isinstance(profile.seniority, Seniority) else profile.seniority
    pool = FALLBACK_QUESTIONS.get(key, FALLBACK_QUESTIONS["Mid"])
    if len(pool) <= needed:
        return list(pool)

    technical = [q for q in pool if _is_technical(q.category)]
    behavioural = [q for q in pool if not _is_technical(q.category)]

    if question_config is None:
        n_tech = min(3, len(technical))
        n_behav = min(needed - n_tech, len(behavioural))
        return technical[:n_tech] + behavioural[:n_behav]

    counts = question_config.counts()
    result = []
    tech_idx = 0
    behav_idx = 0
    for qt, count in counts.items():
        for _ in range(count):
            if qt in (QuestionType.OPEN_ENDED, QuestionType.CODING, QuestionType.SYSTEM_DESIGN, QuestionType.MCQ, QuestionType.YES_NO, QuestionType.DEBUGGING):
                q = technical[tech_idx % len(technical)]
                tech_idx += 1
                q.question_type = qt
            elif qt == QuestionType.BEHAVIORAL:
                q = behavioural[behav_idx % len(behavioural)]
                behav_idx += 1
                q.question_type = qt
            result.append(q)
    return result
