"""
Core intelligence: calls Claude API to generate proposal content.
Uses past proposals from vector DB as context + live web research.
"""
import json
import time
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, BLENDED_RATE_USD
from ingest.vector_store import search_similar_proposals
from engine.web_researcher import research_client_and_context
from engine.value_add_suggester import generate_value_add_suggestions, format_suggestions_for_slide
from engine.proposal_intelligence import extract_proposal_intelligence, format_intelligence_for_prompt

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call_claude(prompt: str, max_tokens: int = 4000, retries: int = 3) -> str:
    """Call Claude API with automatic retry on rate limit errors."""
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
                wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"  Rate limit hit. Waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise
        except Exception:
            raise


def _parse_json_response(text: str) -> dict | list:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_proposal(rfp_text: str, client_context: dict) -> dict:
    """
    Master function: generates all proposal content from RFP + context.
    Returns structured dict with all slide content + effort estimates.
    """
    # Step 1: Find relevant past proposals
    print("Searching past proposals for relevant context...")
    search_query = rfp_text[:2000]
    similar = search_similar_proposals(search_query, n_results=5)
    past_context = _format_past_proposals(similar)

    # Step 2: Extract RFP intelligence
    print("Analyzing RFP...")
    rfp_intel = _extract_rfp_intelligence(rfp_text, client_context)

    # Step 3: Web research — client profile, sector context, leading practices
    print("Researching client and sector context from web...")
    web_research = research_client_and_context(
        client_name=rfp_intel.get("client_name", client_context.get("client_name", "")),
        sector=rfp_intel.get("sector", client_context.get("sector", "")),
        geography=rfp_intel.get("geography", client_context.get("geography", "UAE")),
        engagement_type=rfp_intel.get("engagement_type", client_context.get("engagement_type", "")),
    )

    # Step 4: Deep-read past proposals — NotebookLM-style intelligence extraction
    print("Extracting intelligence from past proposals...")
    proposal_intel = extract_proposal_intelligence(rfp_intel, similar)
    intelligence_context = format_intelligence_for_prompt(proposal_intel)

    # Step 5: Generate technical proposal (enriched with web research + proposal intelligence)
    print("Generating technical proposal...")
    technical = _generate_technical_proposal(rfp_intel, past_context, client_context,
                                              web_research, intelligence_context)

    # Step 5: Generate value-add suggestions
    print("Generating leading practice value-add suggestions...")
    suggestions_raw = generate_value_add_suggestions(
        rfp_intel=rfp_intel,
        leading_practices=web_research.get("leading_practices", {}),
        current_scope=technical.get("scope_of_work", {}),
    )
    value_add_slide = format_suggestions_for_slide(suggestions_raw)

    # Step 6: Generate effort estimates
    print("Estimating effort and costs...")
    effort_model = _generate_effort_model(rfp_intel, technical)

    # Step 7: Generate commercial proposal
    print("Generating commercial proposal...")
    commercial = _generate_commercial_proposal(rfp_intel, effort_model, client_context)

    return {
        "rfp_intel": rfp_intel,
        "technical": technical,
        "effort_model": effort_model,
        "commercial": commercial,
        "web_research": web_research,
        "proposal_intelligence": proposal_intel,
        "value_add_suggestions": suggestions_raw,
        "value_add_slide": value_add_slide,
        "similar_proposals_used": [s["filename"] for s in similar],
    }


def _extract_rfp_intelligence(rfp_text: str, ctx: dict) -> dict:
    """Extract structured information from the RFP."""
    prompt = f"""You are a senior management consultant analyzing an RFP for Protiviti Middle East.
Extract structured intelligence from this RFP.

CLIENT CONTEXT PROVIDED:
- Client Name: {ctx.get('client_name', 'Not specified')}
- Sector: {ctx.get('sector', 'Not specified')}
- Relationship History: {ctx.get('relationship_history', 'Not specified')}
- Budget Range: {ctx.get('budget_range', 'Not specified')}
- Key Contacts: {ctx.get('key_contacts', 'Not specified')}
- Submission Deadline: {ctx.get('deadline', 'Not specified')}

RFP CONTENT:
{rfp_text[:8000]}

Return a JSON object with these fields:
{{
  "client_name": "...",
  "project_title": "...",
  "sector": "...",
  "core_problem": "2-3 sentence summary of what the client is trying to solve",
  "key_objectives": ["objective 1", "objective 2", ...],
  "scope_summary": "summary of what is in scope",
  "deliverables_mentioned": ["deliverable 1", ...],
  "timeline_mentioned": "any timeline or deadline mentioned",
  "evaluation_criteria": ["criteria 1", ...],
  "key_challenges": ["challenge 1", ...],
  "stakeholders_mentioned": ["stakeholder 1", ...],
  "geography": "UAE / KSA / Regional / etc",
  "engagement_type": "e.g. Operating Model, Governance Framework, Maturity Assessment, etc"
}}

Return only valid JSON, no other text."""

    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=2000))
    except Exception as e:
        return {"raw_analysis": str(e)}


def _generate_technical_proposal(rfp_intel: dict, past_context: str,
                                  ctx: dict, web_research: dict = None,
                                  intelligence_context: str = "") -> dict:
    """Generate full technical proposal slide content, enriched with web research."""
    web_research = web_research or {}
    client_profile = web_research.get("client_profile", {})
    sector_context = web_research.get("sector_context", {})

    # Trim web research to key fields only to stay within token limits
    client_summary = {
        "overview": client_profile.get("organization_overview", ""),
        "strategic_context": client_profile.get("strategic_context", ""),
        "leadership_priorities": client_profile.get("leadership_priorities", [])[:3],
        "known_challenges": client_profile.get("known_challenges", [])[:3],
        "recent_initiatives": [
            i.get("initiative", i) if isinstance(i, dict) else i
            for i in client_profile.get("recent_initiatives", [])[:3]
        ],
    }
    sector_summary = {
        "overview": sector_context.get("sector_overview", ""),
        "transformation_drivers": sector_context.get("transformation_drivers", [])[:3],
        "sector_challenges": sector_context.get("sector_challenges", [])[:3],
        "national_programs": [
            p.get("program", p) if isinstance(p, dict) else p
            for p in sector_context.get("national_programs", [])[:3]
        ],
    }

    # Truncate past context to avoid token overflow
    past_context_trimmed = past_context[:3000]

    prompt = f"""You are a Senior Director at Protiviti Middle East writing a technical proposal.
Protiviti's practice areas: Operating Model & Governance, ePMO, Maturity Assessments,
Enterprise Risk Management, Project Risk Management, Operational Efficiency & Optimization.
Geography: UAE and KSA. Industry: Real Estate & Infrastructure.

CLIENT RESEARCH SUMMARY:
{json.dumps(client_summary, indent=2)}

SECTOR CONTEXT SUMMARY:
{json.dumps(sector_summary, indent=2)}

RFP INTELLIGENCE:
{json.dumps(rfp_intel, indent=2)}

CLIENT CONTEXT:
- Relationship History: {ctx.get('relationship_history', 'New client')}
- Past Engagements: {ctx.get('past_engagements', 'None mentioned')}
- Key Differentiators to Emphasize: {ctx.get('differentiators', 'None specified')}

PROPOSAL INTELLIGENCE (extracted from past winning proposals):
{intelligence_context}

RELEVANT PAST PROPOSALS (excerpts):
{past_context_trimmed}

Generate a complete technical proposal with the following slides.
For each slide, provide a title and detailed bullet-point content.
Be specific, professional, and tailored to this client. Avoid generic consulting language.

Return a JSON object with this structure:
{{
  "cover": {{
    "title": "Proposal title",
    "subtitle": "e.g. Technical Proposal | Confidential",
    "client": "client name",
    "date": "Month Year"
  }},
  "executive_summary": {{
    "title": "Executive Summary",
    "our_understanding": "2-3 sentences",
    "our_approach": "2-3 sentences",
    "our_commitment": "1-2 sentences"
  }},
  "our_understanding": {{
    "title": "Our Understanding of Your Challenge",
    "key_drivers": ["driver 1", "driver 2", "driver 3"],
    "challenges_identified": ["challenge 1", "challenge 2"],
    "success_factors": ["factor 1", "factor 2"]
  }},
  "value_proposition": {{
    "title": "Our Value Proposition",
    "headline": "One powerful sentence",
    "value_points": [
      {{"point": "Value point 1", "detail": "Supporting detail"}},
      {{"point": "Value point 2", "detail": "Supporting detail"}},
      {{"point": "Value point 3", "detail": "Supporting detail"}}
    ],
    "protiviti_differentiators": ["differentiator 1", "differentiator 2"]
  }},
  "past_relationship": {{
    "title": "Our Relationship with [Client]",
    "relationship_narrative": "narrative based on context provided",
    "past_engagements": ["engagement 1", "engagement 2"],
    "continuity_benefit": "How prior knowledge benefits this engagement"
  }},
  "scope_of_work": {{
    "title": "Scope of Work & Deliverables",
    "phases": [
      {{
        "phase_name": "Phase 1: ...",
        "phase_objective": "...",
        "deliverables_l1": [
          {{
            "name": "Deliverable name",
            "description": "What this delivers",
            "sub_deliverables": ["L2 item 1", "L2 item 2", "L2 item 3"]
          }}
        ]
      }}
    ]
  }},
  "approach_methodology": {{
    "title": "Our Approach & Methodology",
    "approach_narrative": "2-3 sentences on overall approach",
    "methodology_steps": [
      {{"step": "Step name", "activities": ["activity 1", "activity 2"]}},
    ],
    "tools_and_accelerators": ["tool/framework 1", "tool/framework 2"]
  }},
  "engagement_governance": {{
    "title": "Engagement Governance",
    "governance_structure": "Description of steering committee, etc.",
    "reporting_cadence": ["Weekly status report", "Monthly steering committee", "etc."],
    "escalation_path": "Description",
    "raci_summary": [
      {{"activity": "activity name", "protiviti": "R/A/C/I", "client": "R/A/C/I"}}
    ],
    "quality_assurance": "QA approach"
  }},
  "project_team": {{
    "title": "Our Project Team",
    "team_narrative": "Why this team is right for this engagement",
    "team_members": [
      {{
        "role": "e.g. Engagement Director",
        "responsibilities": ["responsibility 1", "responsibility 2"],
        "relevant_experience": "Brief note"
      }}
    ]
  }},
  "timeline": {{
    "title": "Engagement Timeline",
    "total_duration": "e.g. 16 weeks",
    "phases": [
      {{
        "phase": "Phase 1: ...",
        "duration": "e.g. Weeks 1-4",
        "key_milestones": ["milestone 1", "milestone 2"],
        "key_deliverables": ["deliverable 1"]
      }}
    ]
  }},
  "relevant_experience": {{
    "title": "Our Relevant Experience",
    "narrative": "2 sentences",
    "case_studies": [
      {{
        "client_type": "e.g. Government Real Estate Authority",
        "engagement": "engagement title",
        "our_role": "what we did",
        "outcome": "result achieved"
      }}
    ]
  }},
  "why_protiviti": {{
    "title": "Why Protiviti",
    "headline": "One compelling sentence",
    "reasons": [
      {{"reason": "Reason headline", "detail": "Supporting detail"}}
    ]
  }},
  "key_assumptions": {{
    "title": "Key Assumptions & Dependencies",
    "assumptions": ["assumption 1", "assumption 2"],
    "client_dependencies": ["dependency 1", "dependency 2"],
    "out_of_scope": ["item 1", "item 2"]
  }}
}}

Return only valid JSON."""

    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=6000))
    except Exception as e:
        return {"error": str(e)}


def _generate_effort_model(rfp_intel: dict, technical: dict) -> dict:
    """Generate effort estimates per L2 deliverable."""
    scope = technical.get("scope_of_work", {})

    prompt = f"""You are a senior consultant estimating effort for a consulting engagement.
Blended rate: USD {BLENDED_RATE_USD}/hour.

ENGAGEMENT DETAILS:
{json.dumps(rfp_intel, indent=2)}

SCOPE & DELIVERABLES:
{json.dumps(scope, indent=2)}

Estimate the effort in hours for each L2 deliverable.
Base estimates on:
- Complexity of the deliverable
- Typical UAE/KSA consulting market benchmarks
- The number of stakeholders likely involved
- Documentation and review cycles

Return a JSON object:
{{
  "total_hours": 0,
  "total_fee_usd": 0,
  "phases": [
    {{
      "phase_name": "Phase 1: ...",
      "phase_hours": 0,
      "phase_fee_usd": 0,
      "deliverables": [
        {{
          "l1_name": "L1 Deliverable Name",
          "l1_hours": 0,
          "l1_fee_usd": 0,
          "sub_deliverables": [
            {{
              "l2_name": "L2 deliverable name",
              "hours": 0,
              "fee_usd": 0,
              "complexity": "low/medium/high",
              "week_start": 1,
              "week_end": 2,
              "rationale": "Brief note on why this estimate"
            }}
          ]
        }}
      ]
    }}
  ],
  "assumptions": ["assumption 1", "assumption 2"]
}}

Calculate fee_usd = hours × {BLENDED_RATE_USD}.
Return only valid JSON."""

    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=4000))
    except Exception as e:
        return {"error": str(e)}


def _generate_commercial_proposal(rfp_intel: dict, effort_model: dict, ctx: dict) -> dict:
    """Generate commercial proposal content."""
    prompt = f"""You are writing the commercial proposal for a Protiviti Middle East engagement.

EFFORT MODEL:
{json.dumps(effort_model, indent=2)}

CLIENT: {rfp_intel.get('client_name', 'Client')}
ENGAGEMENT: {rfp_intel.get('project_title', 'Consulting Engagement')}
BLENDED RATE: USD {BLENDED_RATE_USD}/hour

Generate commercial proposal content. Return JSON:
{{
  "cover": {{
    "title": "Commercial Proposal",
    "subtitle": "Confidential | Prepared for [Client]",
    "date": "Month Year"
  }},
  "commercial_summary": {{
    "total_fee_usd": 0,
    "total_hours": 0,
    "duration_weeks": 0,
    "payment_structure": "e.g. 30/40/30 milestone-based",
    "validity_days": 30
  }},
  "fee_by_phase": [
    {{
      "phase": "Phase name",
      "hours": 0,
      "fee_usd": 0,
      "percentage": "0%",
      "key_deliverables": ["deliverable 1"]
    }}
  ],
  "payment_milestones": [
    {{
      "milestone": "Milestone name",
      "trigger": "What triggers payment",
      "amount_usd": 0,
      "percentage": "0%",
      "due_week": 0
    }}
  ],
  "key_assumptions": ["assumption 1", "assumption 2"],
  "exclusions": ["exclusion 1", "exclusion 2"],
  "terms": {{
    "payment_terms": "e.g. 30 days from invoice",
    "variation_process": "description",
    "ip_ownership": "description",
    "confidentiality": "description"
  }}
}}

Return only valid JSON."""

    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=3000))
    except Exception as e:
        return {"error": str(e)}


def _format_past_proposals(similar: list[dict]) -> str:
    """Format retrieved proposals as context for Claude."""
    if not similar:
        return "No similar past proposals found in database."
    parts = []
    for i, prop in enumerate(similar, 1):
        parts.append(
            f"--- Past Proposal {i} (Relevance: {prop['score']}) ---\n"
            f"File: {prop['filename']}\n"
            f"Content excerpt:\n{prop['text_chunk'][:1500]}"
        )
    return "\n\n".join(parts)
