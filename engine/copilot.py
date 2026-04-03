"""
Live Copilot — chat-based proposal refinement after generation.

Two modes:
1. Section Refine — user selects a section + gives instruction → returns updated JSON
2. General Chat — user asks questions or requests advice about the proposal

The copilot has full proposal context in every call so answers are specific,
not generic. It acts as a senior partner reviewing the work.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Maps UI display names → technical keys in proposal_data["technical"]
SECTION_KEYS = {
    "Executive Summary": "executive_summary",
    "Our Understanding": "our_understanding",
    "Value Proposition": "value_proposition",
    "Past Relationship": "past_relationship",
    "Scope of Work": "scope_of_work",
    "Approach & Methodology": "approach_methodology",
    "Engagement Governance": "engagement_governance",
    "Project Team": "project_team",
    "Timeline": "timeline",
    "Relevant Experience": "relevant_experience",
    "Why Protiviti": "why_protiviti",
    "Key Assumptions": "key_assumptions",
}


def refine_section(
    section_display_name: str,
    current_content: dict,
    instruction: str,
    proposal_data: dict,
) -> tuple[dict, str]:
    """
    Refine a specific proposal section based on user instruction.

    Returns:
        (updated_content dict, explanation string)
    """
    rfp_intel = proposal_data.get("rfp_intel", {})
    web_research = proposal_data.get("web_research", {})
    client_profile = web_research.get("client_profile", {})

    prompt = f"""You are a Senior Director at Protiviti Middle East refining a proposal section.
Act as a critical reviewer improving specific content — not a passive assistant.

FULL PROPOSAL CONTEXT:
- Client: {rfp_intel.get('client_name', '')}
- Project: {rfp_intel.get('project_title', '')}
- Sector: {rfp_intel.get('sector', '')}
- Engagement Type: {rfp_intel.get('engagement_type', '')}
- Geography: {rfp_intel.get('geography', 'UAE')}
- Core Problem: {rfp_intel.get('core_problem', '')}
- Client Overview: {client_profile.get('organization_overview', '')}
- Client Priorities: {', '.join(client_profile.get('leadership_priorities', [])[:3])}

SECTION: {section_display_name}

CURRENT CONTENT:
{json.dumps(current_content, indent=2)}

REFINEMENT INSTRUCTION:
{instruction}

Rules:
1. Keep what works — only change what the instruction requires
2. Maintain IDENTICAL JSON structure and key names
3. Make every sentence specific to this client — no generic consulting language
4. If the instruction asks to add depth, write 3-4 sentences not 1
5. If the instruction asks to change tone, revise all relevant fields
6. After the JSON, add a brief note (outside JSON) explaining what you changed

Return: valid JSON block first, then one sentence on what changed."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Split JSON from explanation
        explanation = ""
        json_text = raw
        if "```" in raw:
            parts = raw.split("```")
            json_text = parts[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
            # Anything after the closing ``` is explanation
            if len(parts) > 2:
                explanation = parts[2].strip()
        elif "\n\n" in raw:
            # Try to find JSON block then trailing text
            try:
                # Parse greedily — find last valid JSON
                brace_start = raw.index("{")
                brace_end = raw.rindex("}") + 1
                json_text = raw[brace_start:brace_end]
                explanation = raw[brace_end:].strip()
            except ValueError:
                pass

        updated = json.loads(json_text.strip())
        return updated, explanation or "Section updated."

    except Exception as e:
        print(f"Copilot refine error: {e}")
        return current_content, f"Could not apply refinement: {e}"


def chat_about_proposal(
    message: str,
    proposal_data: dict,
    chat_history: list[dict],
) -> str:
    """
    General chat — answer questions and give strategic advice about this proposal.
    Maintains conversation history for context continuity.

    chat_history: list of {"role": "user"|"assistant", "content": "..."}
    """
    rfp_intel = proposal_data.get("rfp_intel", {})
    effort = proposal_data.get("effort_model", {})
    tech = proposal_data.get("technical", {})

    system_prompt = f"""You are a Senior Consulting Partner at Protiviti Middle East reviewing
a proposal you personally oversaw. You have deep knowledge of this specific proposal.

PROPOSAL SNAPSHOT:
- Client: {rfp_intel.get('client_name', '')}
- Project: {rfp_intel.get('project_title', '')}
- Sector: {rfp_intel.get('sector', '')} | {rfp_intel.get('geography', 'UAE')}
- Engagement: {rfp_intel.get('engagement_type', '')}
- Total Fee: USD {effort.get('total_fee_usd', 0):,.0f} | {effort.get('total_hours', 0):,} hours
- Phases: {len(effort.get('phases', []))}
- Core Problem: {rfp_intel.get('core_problem', '')}

Your role: give direct, specific answers and advice. You are a senior partner,
not a generic AI. If asked to change something, explain exactly what to tell the AI.
If asked about competitiveness, give honest market perspective.
Be concise — senior partners don't write essays."""

    messages = []
    for h in chat_history[-8:]:  # Last 8 turns for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"Copilot error: {e}"
