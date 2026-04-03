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


def generate_proposal(rfp_text: str, client_context: dict, clarification_context: str = "") -> dict:
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
                                              web_research, intelligence_context,
                                              clarification_context)

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
                                  intelligence_context: str = "",
                                  clarification_context: str = "") -> dict:
    """
    Generate the technical proposal section by section.
    Each section gets a dedicated focused call — produces full depth.
    """
    web_research = web_research or {}
    client_profile = web_research.get("client_profile", {})
    sector_context = web_research.get("sector_context", {})

    # Shared context block injected into every section prompt
    base_context = f"""ENGAGEMENT CONTEXT:
- Client: {rfp_intel.get('client_name', '')}
- Project: {rfp_intel.get('project_title', '')}
- Engagement Type: {rfp_intel.get('engagement_type', '')}
- Sector: {rfp_intel.get('sector', '')}
- Geography: {rfp_intel.get('geography', 'UAE')}
- Core Problem: {rfp_intel.get('core_problem', '')}
- Key Objectives: {', '.join(rfp_intel.get('key_objectives', []))}
- Deliverables Mentioned in RFP: {', '.join(rfp_intel.get('deliverables_mentioned', []))}
- Key Challenges: {', '.join(rfp_intel.get('key_challenges', []))}
- Stakeholders: {', '.join(rfp_intel.get('stakeholders_mentioned', []))}
- Timeline: {rfp_intel.get('timeline_mentioned', 'Not specified')}
- Relationship History: {ctx.get('relationship_history', 'New client')}
- Past Engagements: {ctx.get('past_engagements', 'None')}
- Differentiators to Emphasize: {ctx.get('differentiators', 'None')}

CLIENT RESEARCH:
- Overview: {client_profile.get('organization_overview', '')}
- Strategic Context: {client_profile.get('strategic_context', '')}
- Leadership Priorities: {', '.join(client_profile.get('leadership_priorities', [])[:3])}
- Known Challenges: {', '.join(client_profile.get('known_challenges', [])[:3])}
- Recent Initiatives: {', '.join([i.get('initiative', i) if isinstance(i, dict) else i for i in client_profile.get('recent_initiatives', [])[:3]])}

SECTOR CONTEXT:
- {sector_context.get('sector_overview', '')}
- Drivers: {', '.join(sector_context.get('transformation_drivers', [])[:3])}
- National Programs: {', '.join([p.get('program', p) if isinstance(p, dict) else p for p in sector_context.get('national_programs', [])[:3]])}

PROPOSAL INTELLIGENCE FROM PAST WINS:
{intelligence_context}

PAST PROPOSAL EXCERPTS:
{past_context[:2000]}

{f"CLARIFICATION FROM PROPOSAL TEAM (high-priority context):{chr(10)}{clarification_context}" if clarification_context else ""}"""

    print("  Generating: Executive Summary & Understanding...")
    section1 = _gen_section1(base_context, rfp_intel, ctx)

    print("  Generating: Value Proposition & Relationship...")
    section2 = _gen_section2(base_context, rfp_intel, ctx)

    print("  Generating: Scope of Work (detailed)...")
    section3 = _gen_scope(base_context, rfp_intel)

    print("  Generating: Approach & Methodology...")
    section4 = _gen_approach(base_context, rfp_intel)

    print("  Generating: Governance, Team & Timeline...")
    section5 = _gen_delivery(base_context, rfp_intel)

    print("  Generating: Experience, Why Protiviti & Assumptions...")
    section6 = _gen_credibility(base_context, rfp_intel, past_context)

    # Merge all sections
    return {
        "cover": {
            "title": f"{rfp_intel.get('project_title', 'Technical Proposal')}",
            "subtitle": "Technical Proposal | Confidential",
            "client": rfp_intel.get("client_name", ""),
            "date": "April 2026",
        },
        **section1,
        **section2,
        **section3,
        **section4,
        **section5,
        **section6,
    }


def _gen_section1(base_context: str, rfp_intel: dict, ctx: dict) -> dict:
    """Executive Summary + Our Understanding."""
    prompt = f"""You are a Senior Director at Protiviti Middle East writing a high-quality technical proposal.
Protiviti Middle East specializes in: Operating Model & Governance Frameworks, ePMO & PMO Setup,
Maturity Assessments (organizational, departmental, functional), Enterprise Risk Management,
Project Risk Management, Policies & Procedures, Operational Efficiency & Optimization.
We have deep UAE and KSA real estate and infrastructure sector experience.

{base_context}

Generate TWO sections with rich, specific, client-tailored content.
Do NOT use generic consulting language. Reference the client's actual situation.

Return JSON:
{{
  "executive_summary": {{
    "our_understanding": "4-5 sentences explaining what we understand the client is trying to achieve, the specific challenges they face, and the strategic context. Reference their actual situation from the research above.",
    "our_approach": "4-5 sentences describing how Protiviti will tackle this — specific methodology, phasing logic, and what makes our approach right for this client.",
    "our_commitment": "2-3 sentences on what success looks like and our commitment to outcomes — not activities.",
    "key_outcomes": ["Specific outcome 1 we will deliver", "Specific outcome 2", "Specific outcome 3", "Specific outcome 4"]
  }},
  "our_understanding": {{
    "title": "Our Understanding of Your Challenge",
    "context_narrative": "3-4 sentences setting the strategic context — what is happening in this client's world that makes this engagement necessary now.",
    "key_drivers": [
      {{"driver": "Driver headline", "detail": "2-3 sentences explaining this driver and why it matters to this client specifically"}},
      {{"driver": "Driver headline", "detail": "2-3 sentences"}},
      {{"driver": "Driver headline", "detail": "2-3 sentences"}},
      {{"driver": "Driver headline", "detail": "2-3 sentences"}}
    ],
    "challenges_identified": [
      {{"challenge": "Challenge headline", "implication": "What this means for the client if not addressed"}},
      {{"challenge": "Challenge headline", "implication": "What this means"}},
      {{"challenge": "Challenge headline", "implication": "What this means"}}
    ],
    "success_factors": [
      {{"factor": "Success factor", "why": "Why this is critical for this specific engagement"}},
      {{"factor": "Success factor", "why": "Why this is critical"}},
      {{"factor": "Success factor", "why": "Why this is critical"}}
    ],
    "our_perspective": "2-3 sentences sharing Protiviti's specific perspective on this challenge based on our regional experience."
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=3000))
    except Exception as e:
        return {"executive_summary": {}, "our_understanding": {}}


def _gen_section2(base_context: str, rfp_intel: dict, ctx: dict) -> dict:
    """Value Proposition + Past Relationship."""
    prompt = f"""You are a Senior Director at Protiviti Middle East writing a technical proposal.

{base_context}

Generate TWO sections. Be specific and differentiated — avoid generic consulting language.
Every statement should be directly connected to this client's situation.

Return JSON:
{{
  "value_proposition": {{
    "title": "Our Value Proposition",
    "headline": "One powerful, specific sentence capturing what Protiviti uniquely delivers for this client",
    "value_points": [
      {{
        "point": "Value point headline",
        "detail": "3-4 sentences explaining this value point specifically — how we deliver it, what it means for this client, and what evidence we have from similar engagements",
        "proof_point": "A specific example or outcome from a past engagement"
      }},
      {{
        "point": "Value point headline",
        "detail": "3-4 sentences",
        "proof_point": "Specific example"
      }},
      {{
        "point": "Value point headline",
        "detail": "3-4 sentences",
        "proof_point": "Specific example"
      }},
      {{
        "point": "Value point headline",
        "detail": "3-4 sentences",
        "proof_point": "Specific example"
      }}
    ],
    "protiviti_differentiators": [
      "Differentiator 1 — specific to Protiviti ME, not generic",
      "Differentiator 2",
      "Differentiator 3",
      "Differentiator 4",
      "Differentiator 5"
    ],
    "what_sets_us_apart": "2-3 sentences on what genuinely distinguishes Protiviti for this engagement vs. competitors"
  }},
  "past_relationship": {{
    "title": "Our Relationship with {rfp_intel.get('client_name', 'the Client')}",
    "relationship_narrative": "3-4 sentences describing the relationship history, trust built, and how prior knowledge of the client's organization directly benefits this engagement. If new client, describe our approach to onboarding quickly.",
    "past_engagements": [
      {{"engagement": "Engagement title", "year": "Year", "outcome": "What was delivered and the result"}},
      {{"engagement": "Engagement title", "year": "Year", "outcome": "What was delivered"}}
    ],
    "continuity_benefit": "3-4 sentences on how prior relationship knowledge — of their people, culture, processes, and challenges — accelerates this engagement and reduces client effort.",
    "client_investment_protection": "2 sentences on how we build on prior work rather than starting from scratch."
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=3000))
    except Exception as e:
        return {"value_proposition": {}, "past_relationship": {}}


def _gen_scope(base_context: str, rfp_intel: dict) -> dict:
    """Scope of Work — most detailed section."""
    prompt = f"""You are a Senior Director at Protiviti Middle East designing the scope of work.

{base_context}

Design a DETAILED scope of work with 3-4 phases. Each phase must have:
- 2-4 L1 deliverables
- Each L1 must have 4-6 specific L2 sub-deliverables (not vague — describe exactly what each document/output is)

The scope must directly address every deliverable and objective mentioned in the RFP.
Be prescriptive and specific — a client should be able to understand exactly what they will receive.

Return JSON:
{{
  "scope_of_work": {{
    "title": "Scope of Work & Deliverables",
    "scope_narrative": "3-4 sentences summarizing the overall scope and the logic of how the phases build on each other.",
    "phases": [
      {{
        "phase_name": "Phase 1: [Specific Name]",
        "phase_objective": "2-3 sentences on what this phase achieves and why it comes first.",
        "duration": "e.g. Weeks 1-4",
        "deliverables_l1": [
          {{
            "name": "L1 Deliverable Name",
            "description": "2-3 sentences on what this deliverable is, who it is for, and what decision or action it enables.",
            "format": "e.g. PowerPoint report, Word document, Workshop",
            "sub_deliverables": [
              "L2: Specific sub-deliverable — describe what it contains",
              "L2: Specific sub-deliverable — describe what it contains",
              "L2: Specific sub-deliverable — describe what it contains",
              "L2: Specific sub-deliverable — describe what it contains",
              "L2: Specific sub-deliverable — describe what it contains"
            ]
          }}
        ],
        "phase_milestone": "The key milestone/sign-off at the end of this phase"
      }}
    ],
    "in_scope_summary": ["In-scope item 1", "In-scope item 2", "In-scope item 3"],
    "out_of_scope": ["Out of scope item 1", "Out of scope item 2", "Out of scope item 3"]
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=4000))
    except Exception as e:
        return {"scope_of_work": {}}


def _gen_approach(base_context: str, rfp_intel: dict) -> dict:
    """Approach & Methodology."""
    prompt = f"""You are a Senior Director at Protiviti Middle East writing the methodology section.

{base_context}

Write a DETAILED approach and methodology section. This should explain HOW we work,
not just what we deliver. Reference specific Protiviti frameworks, tools, and methodologies.
Show intellectual rigor — a client reading this should feel confident we know exactly how to do this.

Return JSON:
{{
  "approach_methodology": {{
    "title": "Our Approach & Methodology",
    "approach_narrative": "4-5 sentences describing our overall approach philosophy — how we balance analysis with pragmatism, how we engage stakeholders, how we ensure outputs are implementable not just theoretical.",
    "guiding_principles": [
      {{"principle": "Principle name", "description": "2-3 sentences on what this means in practice for this engagement"}},
      {{"principle": "Principle name", "description": "2-3 sentences"}},
      {{"principle": "Principle name", "description": "2-3 sentences"}},
      {{"principle": "Principle name", "description": "2-3 sentences"}}
    ],
    "methodology_steps": [
      {{
        "step": "Step name (e.g. Current State Diagnostic)",
        "description": "3-4 sentences on what we do in this step, how we do it, and what output it produces",
        "activities": [
          "Specific activity 1 — describe what it involves",
          "Specific activity 2",
          "Specific activity 3",
          "Specific activity 4"
        ],
        "techniques": ["Technique/tool used", "Technique/tool used"]
      }}
    ],
    "stakeholder_engagement": "3-4 sentences on how we engage client stakeholders throughout — workshops, interviews, reviews, validations.",
    "quality_control": "3-4 sentences on how we ensure quality — peer review, Director sign-off, client feedback loops.",
    "tools_and_accelerators": [
      {{"tool": "Tool/framework name", "use_case": "How we use this specifically in this engagement", "benefit": "What it saves or improves"}},
      {{"tool": "Tool/framework name", "use_case": "How we use this", "benefit": "Benefit"}},
      {{"tool": "Tool/framework name", "use_case": "How we use this", "benefit": "Benefit"}}
    ],
    "knowledge_transfer": "2-3 sentences on how we ensure the client's team can own and sustain the outputs after we leave."
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=3500))
    except Exception as e:
        return {"approach_methodology": {}}


def _gen_delivery(base_context: str, rfp_intel: dict) -> dict:
    """Engagement Governance + Team + Timeline."""
    prompt = f"""You are a Senior Director at Protiviti Middle East writing the delivery sections.

{base_context}

Write THREE detailed sections. Be specific — give the client a clear picture of how the engagement
will be managed, who will do the work, and when things will happen.

Return JSON:
{{
  "engagement_governance": {{
    "title": "Engagement Governance",
    "governance_narrative": "3-4 sentences on the governance philosophy — how we keep the engagement on track, how decisions are made, how issues are escalated.",
    "governance_structure": {{
      "steering_committee": "Who sits on it, what it does, how often it meets",
      "working_group": "Day-to-day working team composition and meeting cadence",
      "protiviti_leadership": "How Protiviti senior leadership stays engaged"
    }},
    "reporting_cadence": [
      {{"report": "Report name", "frequency": "Weekly/monthly/etc", "audience": "Who receives it", "content": "What it covers"}},
      {{"report": "Report name", "frequency": "Frequency", "audience": "Audience", "content": "Content"}},
      {{"report": "Report name", "frequency": "Frequency", "audience": "Audience", "content": "Content"}}
    ],
    "escalation_path": "Step-by-step description of how issues are escalated — from working team to Protiviti Director to client senior leadership.",
    "raci_summary": [
      {{"activity": "Specific activity", "protiviti": "R", "client": "A"}},
      {{"activity": "Specific activity", "protiviti": "R", "client": "C"}},
      {{"activity": "Specific activity", "protiviti": "A", "client": "R"}},
      {{"activity": "Specific activity", "protiviti": "C", "client": "R"}},
      {{"activity": "Specific activity", "protiviti": "R", "client": "I"}},
      {{"activity": "Specific activity", "protiviti": "I", "client": "R"}}
    ],
    "quality_assurance": "3-4 sentences on QA — how deliverables are reviewed internally before submission, Director sign-off process, client review cycles.",
    "risk_management": "2-3 sentences on how engagement risks are identified, tracked, and mitigated."
  }},
  "project_team": {{
    "title": "Our Project Team",
    "team_narrative": "3-4 sentences on why this specific team is right for this engagement — their combined experience, regional knowledge, and sector expertise.",
    "team_members": [
      {{
        "role": "Engagement Director",
        "title": "Senior Director, Protiviti Middle East",
        "responsibilities": [
          "Overall engagement accountability and quality",
          "Executive-level client relationship management",
          "Strategic direction and methodology oversight",
          "Senior review of all deliverables before submission"
        ],
        "relevant_experience": "3-4 sentences on relevant experience for this specific engagement — sectors, engagement types, similar clients."
      }},
      {{
        "role": "Engagement Manager",
        "title": "Manager / Senior Manager",
        "responsibilities": [
          "Day-to-day engagement management",
          "Stakeholder coordination and workshop facilitation",
          "Quality review of team outputs",
          "Client point of contact for working-level matters"
        ],
        "relevant_experience": "3-4 sentences on relevant experience."
      }},
      {{
        "role": "Senior Consultant",
        "title": "Senior Consultant",
        "responsibilities": [
          "Primary analysis and deliverable development",
          "Stakeholder interviews and data gathering",
          "Document drafting and review",
          "Benchmarking and research"
        ],
        "relevant_experience": "3-4 sentences on relevant experience."
      }},
      {{
        "role": "Consultant / Analyst",
        "title": "Consultant",
        "responsibilities": [
          "Data collection and analysis support",
          "Document formatting and production",
          "Research and benchmarking support",
          "Action tracking and project coordination"
        ],
        "relevant_experience": "2-3 sentences on relevant experience."
      }}
    ],
    "subject_matter_experts": "2-3 sentences on any SME support available from Protiviti's global network that can be called upon for specialist input."
  }},
  "timeline": {{
    "title": "Engagement Timeline",
    "total_duration": "X weeks",
    "timeline_narrative": "2-3 sentences on the overall timeline logic and key assumptions.",
    "phases": [
      {{
        "phase": "Phase 1: [Name]",
        "duration": "Weeks X-Y",
        "key_activities": ["Activity 1", "Activity 2", "Activity 3"],
        "key_milestones": ["Milestone 1", "Milestone 2"],
        "key_deliverables": ["Deliverable 1", "Deliverable 2"],
        "client_inputs_required": ["What we need from the client in this phase"]
      }}
    ],
    "critical_path": "2-3 sentences on what drives the timeline and key dependencies that could affect it.",
    "mobilisation": "2-3 sentences on how quickly we can mobilise after contract signature."
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=4000))
    except Exception as e:
        return {"engagement_governance": {}, "project_team": {}, "timeline": {}}


def _gen_credibility(base_context: str, rfp_intel: dict, past_context: str) -> dict:
    """Relevant Experience + Why Protiviti + Assumptions."""
    prompt = f"""You are a Senior Director at Protiviti Middle East writing the credibility sections.

{base_context}

PAST PROPOSALS (for case study inspiration):
{past_context[:1500]}

Write THREE sections that build confidence and close the proposal strongly.
Case studies must feel real and specific — draw from the past proposals above.

Return JSON:
{{
  "relevant_experience": {{
    "title": "Our Relevant Experience",
    "narrative": "3-4 sentences on Protiviti ME's track record in this specific engagement type and sector, with specific reference to UAE/KSA clients.",
    "regional_credentials": "2-3 sentences specifically on our GCC/UAE/KSA market presence and depth.",
    "case_studies": [
      {{
        "client_type": "e.g. Government Real Estate Authority, UAE",
        "engagement": "Specific engagement title",
        "context": "2 sentences on what the client needed and why",
        "our_role": "3-4 sentences on exactly what Protiviti did — be specific about methodology, deliverables, team",
        "outcome": "2-3 sentences on specific, measurable outcomes achieved",
        "relevance": "1-2 sentences on why this case study is directly relevant to this proposal"
      }},
      {{
        "client_type": "Client type",
        "engagement": "Engagement title",
        "context": "2 sentences",
        "our_role": "3-4 sentences",
        "outcome": "2-3 sentences on outcomes",
        "relevance": "1-2 sentences"
      }},
      {{
        "client_type": "Client type",
        "engagement": "Engagement title",
        "context": "2 sentences",
        "our_role": "3-4 sentences",
        "outcome": "2-3 sentences",
        "relevance": "1-2 sentences"
      }}
    ]
  }},
  "why_protiviti": {{
    "title": "Why Protiviti",
    "headline": "One compelling, specific sentence — not generic",
    "closing_narrative": "3-4 sentences making the case for why Protiviti is the right choice — combining regional expertise, sector depth, team quality, and track record.",
    "reasons": [
      {{
        "reason": "Reason headline",
        "detail": "3-4 sentences with specific evidence — numbers, client names (anonymised), outcomes, or capabilities that prove this reason"
      }},
      {{
        "reason": "Reason headline",
        "detail": "3-4 sentences with specific evidence"
      }},
      {{
        "reason": "Reason headline",
        "detail": "3-4 sentences with specific evidence"
      }},
      {{
        "reason": "Reason headline",
        "detail": "3-4 sentences with specific evidence"
      }},
      {{
        "reason": "Reason headline",
        "detail": "3-4 sentences with specific evidence"
      }}
    ]
  }},
  "key_assumptions": {{
    "title": "Key Assumptions & Dependencies",
    "assumptions": [
      "Assumption 1 — be specific about what we are assuming and why it matters",
      "Assumption 2",
      "Assumption 3",
      "Assumption 4",
      "Assumption 5"
    ],
    "client_dependencies": [
      "What the client must provide/do — be specific about timing and format",
      "Client dependency 2",
      "Client dependency 3",
      "Client dependency 4"
    ],
    "out_of_scope": [
      "Out of scope item 1 — be specific",
      "Out of scope item 2",
      "Out of scope item 3",
      "Out of scope item 4"
    ],
    "variation_trigger": "2-3 sentences on what would trigger a scope variation and how it would be handled."
  }}
}}
Return only valid JSON."""
    try:
        return _parse_json_response(_call_claude(prompt, max_tokens=4000))
    except Exception as e:
        return {"relevant_experience": {}, "why_protiviti": {}, "key_assumptions": {}}


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
