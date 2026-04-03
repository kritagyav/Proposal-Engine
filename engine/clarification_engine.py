"""
Clarification Engine — generates smart pre-generation questions from the RFP.

Flow:
  1. User uploads RFP
  2. This engine reads it and generates 6-8 targeted questions
  3. User answers (or skips) in the UI
  4. Answers are injected as context into the proposal generation prompts

Why this matters: answers to these questions are the single biggest driver
of proposal quality — they give the AI information that is not in the RFP.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_clarification_questions(rfp_text: str, client_context: dict) -> list[dict]:
    """
    Analyze the RFP and produce targeted clarification questions.

    Returns list of:
    {question, category, why_needed, default_if_skipped, placeholder}
    """
    prompt = f"""You are a Senior Director at Protiviti Middle East reviewing an RFP
before writing a proposal. Your goal: identify what the proposal team needs to know
that is NOT clearly answered in the RFP itself.

CLIENT CONTEXT:
- Client: {client_context.get('client_name', 'Not specified')}
- Sector: {client_context.get('sector', 'Not specified')}
- Engagement Type: {client_context.get('engagement_type', 'Not specified')}
- Geography: {client_context.get('geography', 'UAE')}
- Relationship: {client_context.get('relationship_history', 'Not specified')}

RFP CONTENT:
{rfp_text[:6000]}

Generate 6-8 targeted questions. Focus ONLY on gaps not answered in the RFP.
Each question must directly improve a specific part of the proposal if answered.

Categories (pick best fit):
- "Relationship" — history, contacts, politics, past issues
- "Scope" — ambiguous deliverables, unstated constraints, implicit expectations
- "Commercial" — budget signals, competitor landscape, decision factors
- "Strategic" — why now, internal sponsor, board-level context
- "Technical" — systems, data availability, tools in use
- "Stakeholder" — key stakeholders, sign-off process, internal resistance

Return JSON array:
[
  {{
    "question": "Specific, direct question for the proposal team",
    "category": "Category",
    "why_needed": "Which proposal section this improves and how",
    "default_if_skipped": "What assumption we will make if unanswered",
    "placeholder": "Example: 'We have supported this client since 2022 on...'"
  }}
]

Return only valid JSON. Do not include questions already answered in the RFP or context."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Clarification engine error: {e}")
        return []


def format_answers_as_context(questions: list[dict], answers: dict) -> str:
    """
    Format Q&A pairs as structured context for injection into generation prompts.
    answers: dict of {str(index): answer_string}
    """
    if not questions or not answers:
        return ""

    answered = []
    for i, q in enumerate(questions):
        answer = answers.get(str(i), "").strip()
        if answer:
            answered.append(
                f"Q ({q.get('category', 'Context')}): {q['question']}\n"
                f"A: {answer}"
            )

    if not answered:
        return ""

    return (
        "CLARIFICATION PROVIDED BY PROPOSAL TEAM "
        "(treat as high-confidence context, prioritize over generic assumptions):\n\n"
        + "\n\n".join(answered)
    )
