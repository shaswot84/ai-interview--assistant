"""Static fallback question bank used when the LLM API is unavailable.

Provides 10 questions per seniority level (5 technical + 5 behavioural).
"""

from schemas import Question, QuestionCategory, Seniority

# Pool of static questions indexed by seniority level
FALLBACK_QUESTIONS: dict[str, list[Question]] = {
    "Junior": [
        Question(id="f1", text="Explain the difference between a list and a tuple.", category=QuestionCategory.TECHNICAL),
        Question(id="f2", text="What is the difference between SQL and NoSQL databases?", category=QuestionCategory.TECHNICAL),
        Question(id="f3", text="Describe the OSI model layers.", category=QuestionCategory.TECHNICAL),
        Question(id="f4", text="Tell me about a time you resolved a conflict in a team.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f5", text="How do you prioritise tasks when you have multiple deadlines?", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f6", text="What is version control and why is it important?", category=QuestionCategory.TECHNICAL),
        Question(id="f7", text="Explain the concept of a RESTful API.", category=QuestionCategory.TECHNICAL),
        Question(id="f8", text="Describe a project you contributed to and your role.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f9", text="What is the difference between TCP and UDP?", category=QuestionCategory.TECHNICAL),
        Question(id="f10", text="How do you handle feedback on your code?", category=QuestionCategory.BEHAVIOURAL),
    ],
    "Mid": [
        Question(id="f11", text="Explain how you would design a scalable web application architecture.", category=QuestionCategory.TECHNICAL),
        Question(id="f12", text="What strategies do you use to optimise database query performance?", category=QuestionCategory.TECHNICAL),
        Question(id="f13", text="Describe the concept of idempotency in APIs and why it matters.", category=QuestionCategory.TECHNICAL),
        Question(id="f14", text="Tell me about a time you had to refactor a large codebase.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f15", text="Describe a situation where you had to balance speed and quality.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f16", text="How does your team handle deployment and CI/CD?", category=QuestionCategory.TECHNICAL),
        Question(id="f17", text="Explain microservices vs monolith architecture.", category=QuestionCategory.TECHNICAL),
        Question(id="f18", text="Tell me about a technical decision you disagreed with.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f19", text="What is eventual consistency and when would you use it?", category=QuestionCategory.TECHNICAL),
        Question(id="f20", text="How do you mentor junior developers on your team?", category=QuestionCategory.BEHAVIOURAL),
    ],
    "Senior": [
        Question(id="f21", text="Design a system that handles millions of requests per day.", category=QuestionCategory.TECHNICAL),
        Question(id="f22", text="How do you approach incident response and post-mortems?", category=QuestionCategory.TECHNICAL),
        Question(id="f23", text="Explain distributed consensus algorithms like Raft or Paxos.", category=QuestionCategory.TECHNICAL),
        Question(id="f24", text="Describe a time you drove a significant architectural change.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f25", text="How do you align technical strategy with business goals?", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f26", text="What patterns do you use for error handling in distributed systems?", category=QuestionCategory.TECHNICAL),
        Question(id="f27", text="How do you ensure observability in production systems?", category=QuestionCategory.TECHNICAL),
        Question(id="f28", text="Tell me about a cross-team initiative you led.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f29", text="Explain CAP theorem with real-world examples.", category=QuestionCategory.TECHNICAL),
        Question(id="f30", text="How do you handle competing priorities from multiple stakeholders?", category=QuestionCategory.BEHAVIOURAL),
    ],
    "Lead": [
        Question(id="f31", text="Describe how you would structure an engineering org for a 50-person team.", category=QuestionCategory.TECHNICAL),
        Question(id="f32", text="How do you balance technical debt against feature delivery?", category=QuestionCategory.TECHNICAL),
        Question(id="f33", text="What metrics do you use to measure engineering performance?", category=QuestionCategory.TECHNICAL),
        Question(id="f34", text="Tell me about a time you turned around a struggling team.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f35", text="How do you foster a culture of psychological safety?", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f36", text="Explain how you approach technology selection for a new product.", category=QuestionCategory.TECHNICAL),
        Question(id="f37", text="What is your approach to succession planning in engineering?", category=QuestionCategory.TECHNICAL),
        Question(id="f38", text="Describe a difficult personnel decision you had to make.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="f39", text="How do you ensure engineering scalability as the team grows?", category=QuestionCategory.TECHNICAL),
        Question(id="f40", text="Tell me about a time you influenced a company-wide decision.", category=QuestionCategory.BEHAVIOURAL),
    ],
}


def fallback_questions(profile, needed: int = 5) -> list[Question]:
    """Return up to `needed` static questions from the fallback bank for the given seniority.
    
    Prioritises technical questions (3) then behavioural (2).
    """
    key = profile.seniority.value if isinstance(profile.seniority, Seniority) else profile.seniority
    pool = FALLBACK_QUESTIONS.get(key, FALLBACK_QUESTIONS["Mid"])
    if len(pool) <= needed:
        return list(pool)
    technical = [q for q in pool if q.category == QuestionCategory.TECHNICAL]
    behavioural = [q for q in pool if q.category == QuestionCategory.BEHAVIOURAL]
    n_tech = min(3, len(technical))
    n_behav = min(needed - n_tech, len(behavioural))
    return technical[:n_tech] + behavioural[:n_behav]
