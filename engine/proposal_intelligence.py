"""
Proposal Intelligence Layer — NotebookLM-style deep analysis of past proposals.

Instead of just retrieving similar proposals, this module:
1. Extracts winning patterns from past proposals
2. Identifies fee benchmarks for similar engagements
3. Pulls language that resonates (value propositions, differentiators)
4. Flags what competitors are typically proposing
5. Surfaces client-specific insights from past work

Claude reads the actual proposal text and extracts structured intelligence.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from ingest.vector_store import search_similar_proposals, _load_index

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_proposal_intelligence(rfp_intel: dict, similar_proposals: list[dict]) -> dict:
    """
    Deep-read the most relevant past proposals and extract:
    - Winning patterns (structure, language, positioning)
    - Fee benchmarks for this type of engagement
    - Strong value proposition language used before
    - Engagement governance models that worked
    - Team structures for similar scope
    """
    if not similar_proposals:
        return {}

    # Build full text context from similar proposals
    proposal_texts = []
    for p in similar_proposals[:5]:
        filename = p.get("filename", "")
        # Get full text from index (not just the chunk)
        full_text = _get_full_proposal_text(filename)
        if full_text:
            proposal_texts.append(
                f"--- PROPOSAL: {filename} ---\n{full_text[:3000]}"
            )

    if not proposal_texts:
        return {}

    combined = "\n\n".join(proposal_texts)

    prompt = f"""You are analyzing Protiviti Middle East's past winning proposals.
Your job is to extract CONCRETE, REUSABLE intelligence — not summaries.
Quote actual language where possible. A proposal writer should be able to copy-paste from your output.

NEW ENGAGEMENT:
- Client: {rfp_intel.get('client_name', '')}
- Type: {rfp_intel.get('engagement_type', '')}
- Sector: {rfp_intel.get('sector', '')}
- Geography: {rfp_intel.get('geography', 'UAE')}
- Core Problem: {rfp_intel.get('core_problem', '')}

PAST PROPOSALS:
{combined}

Extract concrete, specific intelligence. Quote directly from the proposals — do not paraphrase into generics.

Return a JSON object:
{{
  "fee_benchmarks": {{
    "similar_engagements": [
      {{"proposal": "filename", "engagement_type": "type", "estimated_fee_range": "USD X-Y", "duration": "X weeks", "team_size": "X people"}}
    ],
    "recommended_fee_range": "USD X - USD Y based on past engagements",
    "fee_positioning_advice": "how to position the fee for this client"
  }},
  "winning_language": {{
    "strong_value_props": ["compelling phrase 1 from past proposals", "phrase 2"],
    "differentiator_statements": ["statement 1", "statement 2"],
    "executive_summary_patterns": "what structure/tone works best based on past proposals"
  }},
  "scope_intelligence": {{
    "typical_phases_for_this_type": ["phase 1", "phase 2", "phase 3"],
    "deliverables_that_resonate": ["deliverable 1", "deliverable 2"],
    "scope_gaps_to_watch": ["what clients often ask for that wasn't in scope", "risk area"]
  }},
  "governance_patterns": {{
    "typical_team_structure": "e.g. 1 Director + 2 Managers + 2 Consultants",
    "reporting_structure_used": "what reporting worked well",
    "client_involvement_model": "typical client side involvement"
  }},
  "client_specific_insights": {{
    "past_work_with_client": "any past engagements with this specific client mentioned",
    "client_preferences": "any client-specific preferences or sensitivities observed",
    "relationship_notes": "relationship context"
  }},
  "red_flags": ["risk 1 to watch for", "risk 2"],
  "confidence_level": "high/medium/low based on how relevant the past proposals are"
}}

Return only valid JSON."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"  Proposal intelligence extraction error: {e}")
        return {}


def _get_full_proposal_text(filename: str) -> str:
    """Retrieve full proposal text from the index."""
    index = _load_index()
    for p in index.get("proposals", []):
        if p["filename"] == filename:
            return p.get("text", "")
    return ""


def format_intelligence_for_prompt(intelligence: dict) -> str:
    """Format extracted intelligence as context for proposal generation."""
    if not intelligence:
        return "No past proposal intelligence available."

    parts = []

    fee = intelligence.get("fee_benchmarks", {})
    if fee.get("recommended_fee_range"):
        parts.append(f"FEE BENCHMARK: {fee['recommended_fee_range']}")
        parts.append(f"Fee positioning: {fee.get('fee_positioning_advice', '')}")

    lang = intelligence.get("winning_language", {})
    if lang.get("strong_value_props"):
        parts.append("PROVEN VALUE PROPOSITIONS from past proposals:")
        for vp in lang["strong_value_props"][:3]:
            parts.append(f"  - {vp}")

    scope = intelligence.get("scope_intelligence", {})
    if scope.get("deliverables_that_resonate"):
        parts.append("DELIVERABLES THAT RESONATED with similar clients:")
        for d in scope["deliverables_that_resonate"][:3]:
            parts.append(f"  - {d}")

    gov = intelligence.get("governance_patterns", {})
    if gov.get("typical_team_structure"):
        parts.append(f"TYPICAL TEAM STRUCTURE: {gov['typical_team_structure']}")

    client_intel = intelligence.get("client_specific_insights", {})
    if client_intel.get("past_work_with_client"):
        parts.append(f"CLIENT HISTORY: {client_intel['past_work_with_client']}")

    if intelligence.get("red_flags"):
        parts.append("WATCH OUT FOR:")
        for flag in intelligence["red_flags"][:2]:
            parts.append(f"  - {flag}")

    return "\n".join(parts) if parts else "Limited intelligence available from past proposals."
