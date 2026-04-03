"""
Leading Practice & Value-Add Suggester

Compares the RFP scope against:
- Global leading practice research (from web)
- Past Protiviti proposals
- Engagement type benchmarks

Returns a list of suggested additions with:
- What to add
- Why (client benefit + commercial opportunity)
- Effort estimate
- Whether to include in base scope or propose as optional add-on
"""
import json
import time
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, BLENDED_RATE_USD

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call_claude(prompt: str, max_tokens: int = 4000, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < retries - 1:
                wait = 60 * (attempt + 1)
                print(f"  Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception:
            raise


def generate_value_add_suggestions(
    rfp_intel: dict,
    leading_practices: dict,
    current_scope: dict,
) -> list[dict]:
    """
    Generate value-add suggestions by comparing proposed scope
    against leading practices and client context.

    Returns list of suggestion dicts.
    """

    prompt = f"""You are a Senior Director at Protiviti Middle East reviewing a proposal scope.
Your goal: identify what leading consulting firms include in similar engagements
that would genuinely benefit this client — beyond what they asked for.

ENGAGEMENT TYPE: {rfp_intel.get('engagement_type', '')}
CLIENT: {rfp_intel.get('client_name', '')}
SECTOR: {rfp_intel.get('sector', '')}
GEOGRAPHY: {rfp_intel.get('geography', 'UAE')}

CURRENT PROPOSED SCOPE (summary):
{json.dumps(current_scope, indent=2)[:2000]}

LEADING PRACTICE RESEARCH:
{json.dumps(leading_practices, indent=2)[:1500]}

CLIENT CONTEXT:
- Core problem: {rfp_intel.get('core_problem', '')}
- Key challenges: {rfp_intel.get('key_challenges', [])}
- Key objectives: {rfp_intel.get('key_objectives', [])}

Identify 5-8 specific additions that would:
1. Genuinely benefit the client (not just increase fees)
2. Differentiate Protiviti's proposal from competitors
3. Reflect what leading firms include in similar engagements
4. Be relevant to UAE/KSA market context

For each suggestion, classify as:
- "base_scope": Include in the main proposal (strengthens the core offering)
- "optional_addon": Propose as an optional enhancement with separate fee
- "future_phase": Position as a natural follow-on engagement

Return a JSON array:
[
  {{
    "title": "Short name for this addition",
    "category": "base_scope / optional_addon / future_phase",
    "description": "What this involves — 2-3 sentences",
    "client_benefit": "Why the client needs this — specific to their context",
    "protiviti_angle": "How this plays to our strengths",
    "leading_practice_basis": "What global firms do and why",
    "suggested_deliverables": ["deliverable 1", "deliverable 2"],
    "estimated_hours": 0,
    "estimated_fee_usd": 0,
    "effort_level": "low / medium / high",
    "risk_if_excluded": "What could go wrong without this",
    "slide_talking_point": "One punchy sentence to use in the proposal"
  }}
]

Calculate estimated_fee_usd = estimated_hours × {BLENDED_RATE_USD}.
Be specific and practical. Avoid generic consulting suggestions.
Return only valid JSON array."""

    try:
        text = _call_claude(prompt, max_tokens=3000).strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Value-add suggestion error: {e}")
        return []


def format_suggestions_for_slide(suggestions: list[dict]) -> dict:
    """
    Format suggestions into a proposal slide structure.
    Groups by category for display.
    """
    base_scope = [s for s in suggestions if s.get("category") == "base_scope"]
    optional = [s for s in suggestions if s.get("category") == "optional_addon"]
    future = [s for s in suggestions if s.get("category") == "future_phase"]

    total_optional_fee = sum(s.get("estimated_fee_usd", 0) for s in optional)

    return {
        "title": "Our Recommended Enhancements",
        "intro": "Based on leading practice research and our experience in the region, "
                 "we recommend the following enhancements to maximize the value of this engagement.",
        "included_in_scope": [
            {
                "title": s["title"],
                "talking_point": s["slide_talking_point"],
                "benefit": s["client_benefit"],
            }
            for s in base_scope
        ],
        "optional_addons": [
            {
                "title": s["title"],
                "description": s["description"],
                "fee_usd": s.get("estimated_fee_usd", 0),
                "benefit": s["client_benefit"],
            }
            for s in optional
        ],
        "future_phases": [
            {
                "title": s["title"],
                "rationale": s["client_benefit"],
            }
            for s in future
        ],
        "total_optional_fee_usd": total_optional_fee,
    }
