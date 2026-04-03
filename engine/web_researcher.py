"""
Web Research Module — powered by Claude's built-in web search tool.
No separate API key needed — uses the same Anthropic key.

Researches:
1. Client organization — strategy, initiatives, leadership, challenges
2. Sector context — UAE/KSA regulatory landscape, market conditions
3. Leading practices — what top firms include in similar engagements
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}


def research_client_and_context(client_name: str, sector: str,
                                 geography: str, engagement_type: str) -> dict:
    """
    Run three research queries using Claude's web search tool.
    """
    print(f"  Researching client: {client_name}...")
    client_research = _research_client(client_name, sector, geography)

    print(f"  Researching sector: {sector} in {geography}...")
    sector_research = _research_sector(sector, geography)

    print(f"  Researching leading practices: {engagement_type}...")
    practice_research = _research_leading_practices(engagement_type, sector, geography)

    return {
        "client_profile": client_research,
        "sector_context": sector_research,
        "leading_practices": practice_research,
    }


def _research_client(client_name: str, sector: str, geography: str) -> dict:
    prompt = f"""Research the organization "{client_name}" in the {sector} sector in {geography}.
Find: (1) core mandate and what they do, (2) recent strategic initiatives (last 2 years),
(3) leadership priorities, (4) known challenges, (5) key statistics.

Return JSON:
{{
  "organization_overview": "2-3 sentences",
  "mandate_and_role": "core mandate",
  "strategic_context": "current strategic moment",
  "recent_initiatives": ["initiative 1", "initiative 2", "initiative 3"],
  "leadership_priorities": ["priority 1", "priority 2", "priority 3"],
  "known_challenges": ["challenge 1", "challenge 2", "challenge 3"],
  "key_statistics": ["stat 1", "stat 2"],
  "sources_used": ["source 1", "source 2"]
}}
Return only valid JSON."""
    return _run_web_search(prompt)


def _research_sector(sector: str, geography: str) -> dict:
    prompt = f"""Research the current state of the {sector} sector in {geography} (2025-2026).
Find: (1) key regulatory changes, (2) national programs (Vision 2031, etc.),
(3) sector challenges, (4) transformation drivers, (5) market statistics.

Return JSON:
{{
  "sector_overview": "2-3 sentences",
  "transformation_drivers": ["driver 1", "driver 2", "driver 3"],
  "sector_challenges": ["challenge 1", "challenge 2", "challenge 3"],
  "national_programs": ["program 1", "program 2", "program 3"],
  "regulatory_landscape": ["regulation 1", "regulation 2"],
  "market_statistics": ["stat 1", "stat 2"],
  "sources_used": ["source 1", "source 2"]
}}
Return only valid JSON."""
    return _run_web_search(prompt)


def _research_leading_practices(engagement_type: str, sector: str, geography: str) -> dict:
    prompt = f"""What do leading consulting firms (McKinsey, KPMG, PwC, Deloitte, BCG) include
in "{engagement_type}" engagements for the {sector} sector in {geography}?
Find: (1) standard scope, (2) value-add differentiators, (3) digital tools used,
(4) change management elements, (5) GCC-specific considerations, (6) common pitfalls.

Return JSON:
{{
  "standard_scope": ["element 1", "element 2"],
  "leading_practice_additions": ["addition 1", "addition 2", "addition 3"],
  "digital_accelerators": ["tool 1", "tool 2"],
  "change_management_elements": ["element 1", "element 2"],
  "gcc_mena_specifics": ["consideration 1", "consideration 2"],
  "common_pitfalls": ["pitfall 1", "pitfall 2"],
  "sources_used": ["source 1", "source 2"]
}}
Return only valid JSON."""
    return _run_web_search(prompt)


def _run_web_search(prompt: str) -> dict:
    """Run a prompt with Claude's web search tool enabled."""
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract final text response (after tool use)
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text = block.text

        if not final_text:
            return {}

        text = final_text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text.strip())

    except json.JSONDecodeError:
        return {"raw_research": final_text if 'final_text' in locals() else ""}
    except Exception as e:
        print(f"    Web research error: {e}")
        return {}
