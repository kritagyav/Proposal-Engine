"""
Web Research Module — powered by Perplexity sonar-pro
Purpose-built for deep research with cited sources.

Researches:
1. Client organization — strategy, initiatives, leadership, challenges
2. Sector context — UAE/KSA regulatory landscape, market conditions
3. Leading practices — what top firms include in similar engagements
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _get_perplexity_key():
    try:
        import streamlit as st
        return st.secrets.get("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY")
    except Exception:
        return os.getenv("PERPLEXITY_API_KEY")


def _get_client():
    key = _get_perplexity_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url="https://api.perplexity.ai")


def research_client_and_context(client_name: str, sector: str,
                                 geography: str, engagement_type: str) -> dict:
    """
    Run three research queries via Perplexity sonar-pro.
    Falls back to empty dicts gracefully if key not configured.
    """
    perplexity = _get_client()

    if not perplexity:
        print("  Perplexity API key not set — skipping web research.")
        return {
            "client_profile": {},
            "sector_context": {},
            "leading_practices": {},
        }

    print(f"  Researching client: {client_name} via Perplexity...")
    client_research = _research_client(perplexity, client_name, sector, geography)

    print(f"  Researching sector: {sector} in {geography} via Perplexity...")
    sector_research = _research_sector(perplexity, sector, geography)

    print(f"  Researching leading practices: {engagement_type} via Perplexity...")
    practice_research = _research_leading_practices(perplexity, engagement_type, sector, geography)

    return {
        "client_profile": client_research,
        "sector_context": sector_research,
        "leading_practices": practice_research,
    }


def _perplexity_search(client, query: str, system: str = None) -> dict:
    """
    Run a Perplexity sonar-pro search and return structured result.
    Returns raw text + citations.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
            temperature=0.2,
        )
        text = response.choices[0].message.content
        citations = getattr(response, "citations", []) or []
        return {"text": text, "citations": citations}
    except Exception as e:
        print(f"    Perplexity error: {e}")
        return {"text": "", "citations": []}


def _research_client(client, client_name: str, sector: str, geography: str) -> dict:
    system = (
        "You are a research analyst preparing a briefing for a senior consulting director. "
        "Be specific, factual, and cite sources. Focus on recent developments (last 2 years)."
    )
    query = (
        f"Research the organization '{client_name}' in the {sector} sector in {geography}. "
        f"Provide: (1) what they do and their core mandate, "
        f"(2) recent strategic initiatives or transformation programs announced in the last 2 years, "
        f"(3) leadership priorities based on public statements, "
        f"(4) known operational or governance challenges they face, "
        f"(5) key statistics about their scale or portfolio. "
        f"Be specific and factual with sources."
    )
    result = _perplexity_search(client, query, system)

    # Parse the narrative into structured fields using a second pass
    return _structure_client_research(result, client_name)


def _research_sector(client, sector: str, geography: str) -> dict:
    system = (
        "You are a sector analyst covering real estate and infrastructure in the GCC. "
        "Focus on factual, current information with sources."
    )
    query = (
        f"What is the current state of the {sector} sector in {geography} as of 2025-2026? "
        f"Cover: (1) key government policies and regulatory changes, "
        f"(2) relevant national programs (Vision 2031, Saudi Vision 2030, etc.), "
        f"(3) major sector challenges organizations face, "
        f"(4) transformation drivers pushing organizations to seek consulting support, "
        f"(5) market size or investment statistics. "
        f"Be specific with data points and sources."
    )
    result = _perplexity_search(client, query, system)
    return _structure_sector_research(result, sector, geography)


def _research_leading_practices(client, engagement_type: str, sector: str, geography: str) -> dict:
    system = (
        "You are a management consulting expert familiar with Big 4 and top-tier firm methodologies. "
        "Focus on what actually differentiates excellent proposals from average ones."
    )
    query = (
        f"What do leading management consulting firms (McKinsey, KPMG, PwC, Deloitte, BCG, Protiviti) "
        f"include in '{engagement_type}' engagements for the {sector} sector, "
        f"especially in {geography}? "
        f"Cover: (1) standard scope elements every firm includes, "
        f"(2) value-add components that differentiate top proposals, "
        f"(3) digital tools or accelerators commonly used, "
        f"(4) change management and capability building elements, "
        f"(5) GCC/MENA-specific considerations, "
        f"(6) common failure factors to avoid. "
        f"Be specific about what separates excellent from average engagements."
    )
    result = _perplexity_search(client, query, system)
    return _structure_practice_research(result, engagement_type)


def _structure_client_research(result: dict, client_name: str) -> dict:
    """Convert Perplexity narrative into structured fields."""
    text = result.get("text", "")
    citations = result.get("citations", [])

    if not text:
        return {}

    # Extract key sentences for each field using simple parsing
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    return {
        "organization_overview": _extract_paragraph(text, 0, 300),
        "mandate_and_role": _extract_paragraph(text, 0, 200),
        "strategic_context": _extract_paragraph(text, 300, 600),
        "recent_initiatives": _extract_list_items(text, ["initiative", "program", "launch", "announced", "strategy"]),
        "leadership_priorities": _extract_list_items(text, ["priorit", "focus", "goal", "objective", "vision"])[:4],
        "known_challenges": _extract_list_items(text, ["challenge", "issue", "problem", "gap", "need"])[:4],
        "key_statistics": _extract_list_items(text, ["billion", "million", "AED", "USD", "%", "thousand"])[:3],
        "full_research": text[:2000],
        "sources_used": [c if isinstance(c, str) else str(c) for c in citations[:5]],
    }


def _structure_sector_research(result: dict, sector: str, geography: str) -> dict:
    text = result.get("text", "")
    citations = result.get("citations", [])

    if not text:
        return {}

    return {
        "sector_overview": _extract_paragraph(text, 0, 300),
        "transformation_drivers": _extract_list_items(text, ["driver", "push", "demand", "trend", "digital", "transform"])[:4],
        "sector_challenges": _extract_list_items(text, ["challenge", "issue", "gap", "barrier", "shortage"])[:4],
        "national_programs": _extract_list_items(text, ["vision", "program", "initiative", "plan", "strategy", "2030", "2031", "2033"])[:4],
        "regulatory_landscape": _extract_list_items(text, ["regulat", "law", "policy", "mandate", "requirement", "authority"])[:3],
        "market_statistics": _extract_list_items(text, ["billion", "million", "AED", "USD", "%", "growth"])[:3],
        "full_research": text[:2000],
        "sources_used": [c if isinstance(c, str) else str(c) for c in citations[:5]],
    }


def _structure_practice_research(result: dict, engagement_type: str) -> dict:
    text = result.get("text", "")
    citations = result.get("citations", [])

    if not text:
        return {}

    return {
        "standard_scope": _extract_list_items(text, ["standard", "typical", "common", "usually", "always", "every"])[:4],
        "leading_practice_additions": _extract_list_items(text, ["leading", "best", "differentiat", "value-add", "advanced", "top"])[:5],
        "digital_accelerators": _extract_list_items(text, ["tool", "platform", "digital", "software", "system", "technology"])[:4],
        "change_management_elements": _extract_list_items(text, ["change", "adoption", "training", "capability", "culture"])[:3],
        "gcc_mena_specifics": _extract_list_items(text, ["GCC", "UAE", "Saudi", "MENA", "region", "local", "Arabic"])[:3],
        "common_pitfalls": _extract_list_items(text, ["fail", "avoid", "risk", "pitfall", "mistake", "common issue"])[:3],
        "full_research": text[:2000],
        "sources_used": [c if isinstance(c, str) else str(c) for c in citations[:5]],
    }


def _extract_paragraph(text: str, start: int, end: int) -> str:
    """Extract a segment of text, cleaned up."""
    segment = text[start:end].strip()
    # Remove markdown formatting
    segment = segment.replace("**", "").replace("##", "").replace("#", "")
    return segment


def _extract_list_items(text: str, keywords: list) -> list:
    """Extract sentences/lines that contain relevant keywords."""
    results = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip().lstrip("•-*123456789. ")
        line = line.replace("**", "").replace("##", "")
        if len(line) > 20 and any(kw.lower() in line.lower() for kw in keywords):
            results.append(line[:200])
    return results[:6]
