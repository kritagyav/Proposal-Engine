"""
Web Research Module
Uses Claude's built-in web search tool to research:
1. The client organization — recent news, strategy, leadership, projects
2. UAE/KSA sector context — regulatory changes, market conditions, trends
3. Leading practices — what top firms are doing for this engagement type

Returns structured research that enriches proposal slides.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}


def research_client_and_context(client_name: str, sector: str,
                                 geography: str, engagement_type: str) -> dict:
    """
    Run three parallel research threads:
    1. Client profile & current priorities
    2. Sector context in UAE/KSA
    3. Leading practices for this engagement type
    Returns unified research dict.
    """
    print(f"  Researching client: {client_name}...")
    client_research = _research_client(client_name, sector, geography)

    print(f"  Researching sector context: {sector} in {geography}...")
    sector_research = _research_sector(sector, geography)

    print(f"  Researching leading practices: {engagement_type}...")
    practice_research = _research_leading_practices(engagement_type, sector, geography)

    return {
        "client_profile": client_research,
        "sector_context": sector_research,
        "leading_practices": practice_research,
    }


def _research_client(client_name: str, sector: str, geography: str) -> dict:
    """Research the specific client organization."""
    prompt = f"""Research the organization "{client_name}" in the {sector} sector in {geography}.

Search for:
1. What they do — core mandate, mission, key projects
2. Recent strategic initiatives, transformation programs, or announcements (last 2 years)
3. Leadership priorities — what their CEO/leadership is publicly focused on
4. Known challenges or pain points they face
5. Any relevant tenders, programs, or initiatives that relate to consulting needs

After researching, return a JSON object:
{{
  "organization_overview": "2-3 sentence description of who they are",
  "mandate_and_role": "Their core mandate in the sector",
  "recent_initiatives": [
    {{"initiative": "name", "description": "what it is", "relevance": "why it matters for our proposal"}}
  ],
  "leadership_priorities": ["priority 1", "priority 2", "priority 3"],
  "known_challenges": ["challenge 1", "challenge 2", "challenge 3"],
  "strategic_context": "2-3 sentence narrative about their current strategic moment",
  "key_statistics": ["stat 1 with source", "stat 2 with source"],
  "sources_used": ["source 1", "source 2"]
}}

Return only valid JSON."""

    return _run_web_search_prompt(prompt)


def _research_sector(sector: str, geography: str) -> dict:
    """Research the sector landscape in UAE/KSA."""
    prompt = f"""Research the current state of the {sector} sector in {geography}.
Focus on the last 18 months.

Search for:
1. Key government policies and regulatory changes affecting this sector
2. Major sector-wide challenges and transformation drivers
3. Relevant national programs (e.g. UAE Vision 2031, Saudi Vision 2030 initiatives)
4. Market size, investment levels, or growth statistics
5. Common operational or governance challenges organizations in this sector face

Return a JSON object:
{{
  "sector_overview": "2-3 sentence overview",
  "regulatory_landscape": [
    {{"regulation": "name", "impact": "how it affects organizations"}}
  ],
  "national_programs": [
    {{"program": "name", "relevance": "how it creates consulting demand"}}
  ],
  "sector_challenges": ["challenge 1", "challenge 2", "challenge 3", "challenge 4"],
  "transformation_drivers": ["driver 1", "driver 2", "driver 3"],
  "market_statistics": ["statistic with source", "statistic with source"],
  "sources_used": ["source 1", "source 2"]
}}

Return only valid JSON."""

    return _run_web_search_prompt(prompt)


def _research_leading_practices(engagement_type: str, sector: str, geography: str) -> dict:
    """Research global leading practices for this engagement type."""
    prompt = f"""Research global and regional leading practices for "{engagement_type}" engagements
in the {sector} sector, with specific relevance to {geography}.

Search for:
1. What leading global consulting firms (McKinsey, KPMG, PwC, Deloitte, BCG)
   include in similar engagements beyond the basic scope
2. Common value-add components that differentiate top-tier proposals
3. Digital tools, platforms, or technology accelerators used in such engagements
4. Change management and capability building components typically included
5. Benchmarks and maturity frameworks used globally for this engagement type
6. Common pitfalls or failure factors in similar engagements
7. Emerging trends relevant to this type of work in the GCC/MENA region

Return a JSON object:
{{
  "standard_scope": ["what every firm includes"],
  "leading_practice_additions": [
    {{
      "addition": "Name of value-add",
      "description": "What it involves",
      "why_it_matters": "Client benefit",
      "effort_impact": "low/medium/high additional effort"
    }}
  ],
  "digital_accelerators": [
    {{"tool": "tool/platform name", "use_case": "how it applies"}}
  ],
  "change_management_elements": ["element 1", "element 2"],
  "capability_building": ["what to include for client sustainability"],
  "common_pitfalls": ["pitfall 1", "pitfall 2"],
  "gcc_mena_specifics": ["region-specific consideration 1", "consideration 2"],
  "benchmark_frameworks": ["framework 1", "framework 2"],
  "sources_used": ["source 1", "source 2"]
}}

Return only valid JSON."""

    return _run_web_search_prompt(prompt)


def _run_web_search_prompt(prompt: str) -> dict:
    """
    Run a prompt with web search enabled.
    Claude will search the web as needed and return structured JSON.
    """
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract the final text response (after tool use)
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text = block.text
                break

        if not final_text:
            return {"error": "No text response from web research"}

        # Clean and parse JSON
        text = final_text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError:
        return {"raw_research": final_text if 'final_text' in locals() else "Research failed"}
    except Exception as e:
        print(f"    Web research error: {e}")
        return {"error": str(e)}
