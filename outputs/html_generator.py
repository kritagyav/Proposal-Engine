"""
Generates styled HTML output for Technical and Commercial proposals.
HTML is the primary output — PPT and PDF are generated on demand from here.
"""
import os
from config import OUTPUTS_PATH, BLENDED_RATE_USD


def generate_proposal_html(proposal_data: dict, client_name: str) -> str:
    """
    Generate a single HTML file containing both Technical and Commercial proposals.
    Returns the file path.
    """
    tech = proposal_data.get("technical", {})
    commercial = proposal_data.get("commercial", {})
    effort = proposal_data.get("effort_model", {})
    rfp = proposal_data.get("rfp_intel", {})
    web_research = proposal_data.get("web_research", {})
    value_add = proposal_data.get("value_add_slide", {})
    similar = proposal_data.get("similar_proposals_used", [])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proposal — {client_name}</title>
<style>
  :root {{
    --red: #C8102E;
    --dark: #2C2C2C;
    --gray: #555555;
    --light: #F5F5F5;
    --mid: #E0E0E0;
    --white: #FFFFFF;
    --green: #1A7A3C;
    --font: 'Segoe UI', Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: var(--font); color: var(--dark); background: #FAFAFA; }}

  /* Navigation */
  .nav {{
    position: sticky; top: 0; background: var(--dark); z-index: 100;
    display: flex; align-items: center; padding: 0 2rem; height: 52px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }}
  .nav-brand {{ color: var(--red); font-size: 1rem; font-weight: 700; margin-right: 2rem; }}
  .nav-links {{ display: flex; gap: 0.5rem; flex: 1; overflow-x: auto; }}
  .nav-link {{
    color: #AAA; text-decoration: none; font-size: 0.78rem; padding: 0.4rem 0.8rem;
    border-radius: 3px; white-space: nowrap; transition: all 0.2s;
  }}
  .nav-link:hover {{ background: rgba(200,16,46,0.2); color: white; }}

  /* Download bar */
  .download-bar {{
    background: var(--dark); border-top: 2px solid var(--red);
    padding: 0.75rem 2rem; display: flex; align-items: center; gap: 1rem;
    position: sticky; top: 52px; z-index: 99;
  }}
  .download-bar span {{ color: #AAA; font-size: 0.8rem; margin-right: 0.5rem; }}
  .dl-btn {{
    padding: 0.4rem 1.2rem; border-radius: 3px; font-size: 0.82rem;
    font-weight: 600; cursor: pointer; border: none; text-decoration: none;
    display: inline-block;
  }}
  .dl-btn-primary {{ background: var(--red); color: white; }}
  .dl-btn-secondary {{ background: transparent; color: #CCC; border: 1px solid #555; }}
  .dl-btn:hover {{ opacity: 0.85; }}

  /* Sections */
  .proposal-section {{ max-width: 1100px; margin: 0 auto; padding: 3rem 2rem; }}
  .section-divider {{
    background: var(--red); color: white; padding: 3rem 2.5rem;
    margin: 2rem 0; page-break-before: always;
  }}
  .section-divider .num {{ font-size: 4rem; font-weight: 900; opacity: 0.3; line-height: 1; }}
  .section-divider .title {{ font-size: 2rem; font-weight: 700; margin-top: 0.5rem; }}

  /* Cover */
  .cover {{
    background: var(--dark); color: white; padding: 5rem 3rem;
    min-height: 500px; display: flex; flex-direction: column; justify-content: center;
    border-left: 8px solid var(--red);
  }}
  .cover .label {{ color: var(--red); font-size: 0.85rem; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 1.5rem; }}
  .cover h1 {{ font-size: 2.8rem; font-weight: 700; line-height: 1.2; margin-bottom: 1rem; }}
  .cover .subtitle {{ color: #AAA; font-size: 1.1rem; margin-bottom: 2rem; }}
  .cover .meta {{ color: #CCC; font-size: 0.9rem; border-top: 1px solid #444; padding-top: 1.5rem; }}
  .cover .practice {{ color: #888; font-size: 0.78rem; margin-top: 3rem;
    letter-spacing: 1px; text-transform: uppercase; }}

  /* Slide card */
  .slide {{
    background: white; border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin: 1.5rem 0; overflow: hidden; page-break-inside: avoid;
  }}
  .slide-header {{
    padding: 1.2rem 1.8rem; border-bottom: 3px solid var(--red);
    display: flex; align-items: center; gap: 1rem;
  }}
  .slide-header h2 {{ font-size: 1.15rem; font-weight: 700; color: var(--dark); }}
  .slide-body {{ padding: 1.5rem 1.8rem; }}

  /* Content elements */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
  .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; }}
  .col-title {{ color: var(--red); font-size: 0.82rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.75rem;
    border-bottom: 2px solid var(--red); padding-bottom: 0.4rem; }}
  ul.bullets {{ list-style: none; padding: 0; }}
  ul.bullets li {{ padding: 0.35rem 0; padding-left: 1.2rem; position: relative;
    font-size: 0.9rem; color: var(--gray); border-bottom: 1px solid #F0F0F0; }}
  ul.bullets li::before {{ content: "•"; color: var(--red); position: absolute;
    left: 0; font-weight: bold; }}
  .narrative {{ font-size: 0.95rem; color: var(--gray); line-height: 1.7;
    margin-bottom: 1rem; }}

  /* Phase blocks */
  .phase-block {{
    border-left: 4px solid var(--red); margin: 1.2rem 0; padding: 1rem 1.2rem;
    background: #FFF8F8; border-radius: 0 4px 4px 0;
  }}
  .phase-name {{ font-size: 1rem; font-weight: 700; color: var(--red); margin-bottom: 0.5rem; }}
  .phase-obj {{ font-size: 0.85rem; color: var(--gray); margin-bottom: 0.8rem; }}
  .deliverable {{ margin: 0.6rem 0 0.6rem 1rem; }}
  .deliv-name {{ font-size: 0.9rem; font-weight: 600; color: var(--dark); }}
  .deliv-desc {{ font-size: 0.82rem; color: var(--gray); margin: 0.2rem 0; }}
  .sub-deliv {{ font-size: 0.8rem; color: #777; padding: 0.15rem 0 0.15rem 1rem;
    border-left: 2px solid var(--mid); margin: 0.1rem 0; }}

  /* Stats row */
  .stats-row {{ display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap; }}
  .stat-box {{
    background: var(--light); border-radius: 6px; padding: 1rem 1.5rem;
    text-align: center; flex: 1; min-width: 120px; border-top: 3px solid var(--red);
  }}
  .stat-val {{ font-size: 1.6rem; font-weight: 700; color: var(--red); }}
  .stat-label {{ font-size: 0.75rem; color: var(--gray); text-transform: uppercase;
    letter-spacing: 0.5px; margin-top: 0.2rem; }}

  /* Value-add cards */
  .vadd-included {{ background: #F0FFF4; border: 1px solid #A8D5B5;
    border-radius: 5px; padding: 0.8rem 1rem; margin: 0.5rem 0; }}
  .vadd-optional {{ background: #FFF8F0; border: 1px solid #F0C080;
    border-radius: 5px; padding: 0.8rem 1rem; margin: 0.5rem 0; }}
  .vadd-title {{ font-weight: 700; font-size: 0.9rem; }}
  .vadd-detail {{ font-size: 0.82rem; color: var(--gray); margin-top: 0.3rem; }}
  .vadd-fee {{ color: var(--red); font-weight: 700; }}
  .badge {{
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 3px;
    font-size: 0.72rem; font-weight: 700; margin-left: 0.5rem;
  }}
  .badge-green {{ background: #D4EDDA; color: #155724; }}
  .badge-orange {{ background: #FFF3CD; color: #856404; }}

  /* Governance RACI */
  .raci-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 0.8rem; }}
  .raci-table th {{ background: var(--red); color: white; padding: 0.5rem 0.8rem;
    text-align: left; }}
  .raci-table td {{ padding: 0.4rem 0.8rem; border-bottom: 1px solid var(--mid); }}
  .raci-table tr:nth-child(even) {{ background: var(--light); }}

  /* Effort table */
  .effort-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  .effort-table th {{ background: var(--dark); color: white; padding: 0.6rem 0.8rem;
    text-align: left; }}
  .effort-table td {{ padding: 0.45rem 0.8rem; border-bottom: 1px solid var(--mid); }}
  .effort-table tr.phase-row td {{ background: #F0F0F0; font-weight: 700; color: var(--dark); }}
  .effort-table tr.total-row td {{ background: var(--red); color: white; font-weight: 700;
    font-size: 0.9rem; }}
  .effort-table tr:hover td {{ background: #FFF0F0; }}
  .text-right {{ text-align: right; }}
  .text-center {{ text-align: center; }}

  /* Timeline */
  .timeline-phase {{ margin: 1rem 0; }}
  .tl-header {{ display: flex; justify-content: space-between; align-items: center;
    background: var(--light); padding: 0.6rem 1rem; border-left: 4px solid var(--red);
    margin-bottom: 0.3rem; }}
  .tl-phase-name {{ font-weight: 700; font-size: 0.9rem; }}
  .tl-duration {{ color: var(--red); font-weight: 600; font-size: 0.85rem; }}
  .tl-milestones {{ font-size: 0.8rem; color: var(--gray); padding: 0.3rem 1rem; }}

  /* Experience cards */
  .case-card {{ background: var(--light); border-radius: 6px; padding: 1.2rem;
    border-top: 3px solid var(--red); }}
  .case-client {{ font-size: 0.75rem; color: var(--gray); text-transform: uppercase;
    letter-spacing: 0.5px; }}
  .case-title {{ font-size: 0.95rem; font-weight: 700; color: var(--dark); margin: 0.3rem 0; }}
  .case-role {{ font-size: 0.82rem; color: var(--gray); }}
  .case-outcome {{ font-size: 0.82rem; color: var(--red); font-weight: 600;
    margin-top: 0.5rem; }}

  /* Commercial */
  .fee-row {{ display: flex; justify-content: space-between; align-items: center;
    padding: 0.7rem 1rem; border-bottom: 1px solid var(--mid); }}
  .fee-row:last-child {{ border-bottom: none; }}
  .fee-row.total {{ background: var(--red); color: white; font-weight: 700;
    border-radius: 4px; margin-top: 0.5rem; }}
  .fee-amount {{ font-weight: 700; color: var(--red); }}
  .fee-row.total .fee-amount {{ color: white; }}
  .milestone-card {{
    background: var(--light); border-radius: 5px; padding: 0.8rem 1.2rem;
    margin: 0.5rem 0; display: flex; justify-content: space-between; align-items: center;
    border-left: 4px solid var(--red);
  }}
  .milestone-num {{ color: var(--red); font-weight: 700; font-size: 1.1rem; width: 2rem; }}
  .milestone-info {{ flex: 1; }}
  .milestone-name {{ font-weight: 600; font-size: 0.9rem; }}
  .milestone-trigger {{ font-size: 0.8rem; color: var(--gray); }}
  .milestone-amount {{ font-size: 1.1rem; font-weight: 700; color: var(--red); }}

  /* Sources */
  .sources {{ font-size: 0.72rem; color: #AAA; margin-top: 1rem;
    padding-top: 0.5rem; border-top: 1px solid var(--mid); }}

  /* Footer */
  .doc-footer {{
    background: var(--dark); color: #888; text-align: center;
    padding: 1.5rem; font-size: 0.75rem; margin-top: 3rem;
  }}
  .confidential-banner {{
    background: #FFF3CD; border: 1px solid #F0C080; color: #856404;
    text-align: center; padding: 0.6rem; font-size: 0.8rem; font-weight: 600;
  }}

  @media print {{
    .nav, .download-bar {{ display: none !important; }}
    .slide {{ box-shadow: none; border: 1px solid var(--mid); }}
    .section-divider {{ page-break-before: always; }}
    body {{ background: white; }}
  }}
</style>
</head>
<body>

<!-- Navigation -->
<nav class="nav">
  <span class="nav-brand">PROTIVITI</span>
  <div class="nav-links">
    <a class="nav-link" href="#cover">Cover</a>
    <a class="nav-link" href="#exec-summary">Exec Summary</a>
    <a class="nav-link" href="#client-overview">Client Overview</a>
    <a class="nav-link" href="#understanding">Understanding</a>
    <a class="nav-link" href="#value-prop">Value Proposition</a>
    <a class="nav-link" href="#scope">Scope of Work</a>
    <a class="nav-link" href="#value-add">Enhancements</a>
    <a class="nav-link" href="#approach">Approach</a>
    <a class="nav-link" href="#governance">Governance</a>
    <a class="nav-link" href="#team">Team</a>
    <a class="nav-link" href="#timeline">Timeline</a>
    <a class="nav-link" href="#experience">Experience</a>
    <a class="nav-link" href="#commercial">Commercial</a>
    <a class="nav-link" href="#costing">Costing</a>
  </div>
</nav>

<!-- Download bar -->
<div class="download-bar">
  <span>Download as:</span>
  <a class="dl-btn dl-btn-primary" onclick="window.print()">PDF (Print)</a>
  <a class="dl-btn dl-btn-secondary" id="dl-html" href="#" onclick="downloadHTML()">HTML File</a>
  <span style="margin-left:auto;color:#888;font-size:0.75rem;">
    Generated by Protiviti ME Proposal Engine
  </span>
</div>

<div class="confidential-banner">
  STRICTLY CONFIDENTIAL — Prepared exclusively for {client_name}
</div>

<!-- ============================================================ -->
<!-- TECHNICAL PROPOSAL -->
<!-- ============================================================ -->

{_html_cover(tech.get("cover", {}), client_name)}

<div class="proposal-section">

{_html_exec_summary(tech.get("executive_summary", {}))}
{_html_client_overview(web_research.get("client_profile", {}), rfp)}
{_html_sector_context(web_research.get("sector_context", {}), rfp)}
{_html_understanding(tech.get("our_understanding", {}))}
{_html_value_proposition(tech.get("value_proposition", {}))}
{_html_past_relationship(tech.get("past_relationship", {}))}
{_html_scope(tech.get("scope_of_work", {}))}
{_html_value_add(value_add)}
{_html_approach(tech.get("approach_methodology", {}))}
{_html_governance(tech.get("engagement_governance", {}))}
{_html_team(tech.get("project_team", {}))}
{_html_timeline(tech.get("timeline", {}))}
{_html_experience(tech.get("relevant_experience", {}))}
{_html_why_protiviti(tech.get("why_protiviti", {}))}
{_html_assumptions(tech.get("key_assumptions", {}))}

</div>

<!-- ============================================================ -->
<!-- COMMERCIAL PROPOSAL -->
<!-- ============================================================ -->

<div class="section-divider" id="commercial">
  <div class="num">★</div>
  <div class="title">Commercial Proposal</div>
</div>

<div class="proposal-section">
{_html_commercial_summary(commercial.get("commercial_summary", {}), effort)}
{_html_fee_by_phase(commercial.get("fee_by_phase", []), effort)}
{_html_costing_table(effort)}
{_html_payment_milestones(commercial.get("payment_milestones", []))}
{_html_commercial_assumptions(commercial)}
{_html_terms(commercial.get("terms", {}))}
</div>

{_html_footer(client_name, similar)}

<script>
function downloadHTML() {{
  const blob = new Blob([document.documentElement.outerHTML], {{type: 'text/html'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'Proposal_{client_name.replace(" ", "_")}.html';
  a.click();
}}
// Smooth scroll for nav links
document.querySelectorAll('.nav-link').forEach(link => {{
  link.addEventListener('click', e => {{
    e.preventDefault();
    const target = document.querySelector(link.getAttribute('href'));
    if (target) target.scrollIntoView({{behavior: 'smooth', block: 'start'}});
  }});
}});
</script>
</body>
</html>"""

    filename = f"Proposal_{client_name.replace(' ', '_')}.html"
    output_path = os.path.join(OUTPUTS_PATH, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ── Section renderers ─────────────────────────────────────────────────────────

def _html_cover(cover: dict, client_name: str) -> str:
    return f"""
<div class="cover" id="cover">
  <div class="label">Technical Proposal</div>
  <h1>{cover.get("title", "Technical Proposal")}</h1>
  <div class="subtitle">{cover.get("subtitle", "Confidential")}</div>
  <div class="meta">
    <strong>Prepared for:</strong> {cover.get("client", client_name)}<br>
    <strong>Date:</strong> {cover.get("date", "")}
  </div>
  <div class="practice">Protiviti Middle East · Real Estate &amp; Infrastructure Practice</div>
</div>"""


def _html_exec_summary(data: dict) -> str:
    if not data:
        return ""
    outcomes_html = "".join([f"<li>{o}</li>" for o in data.get("key_outcomes", [])])
    return f"""
<div class="slide" id="exec-summary">
  <div class="slide-header"><h2>Executive Summary</h2></div>
  <div class="slide-body">
    <div class="two-col">
      <div>
        <div class="col-title">Our Understanding</div>
        <p class="narrative">{data.get("our_understanding", "")}</p>
        <div class="col-title" style="margin-top:1rem">Our Approach</div>
        <p class="narrative">{data.get("our_approach", "")}</p>
      </div>
      <div>
        <div class="col-title">Our Commitment</div>
        <p class="narrative">{data.get("our_commitment", "")}</p>
        {f'<div class="col-title" style="margin-top:1rem">Key Outcomes</div><ul class="bullets">{outcomes_html}</ul>' if outcomes_html else ""}
      </div>
    </div>
  </div>
</div>"""


def _html_client_overview(profile: dict, rfp: dict) -> str:
    if not profile or profile.get("error"):
        return ""
    initiatives = profile.get("recent_initiatives", [])
    init_html = "".join([
        f'<li>{i.get("initiative", i) if isinstance(i, dict) else i}</li>'
        for i in initiatives[:4]
    ])
    priorities = "".join([f"<li>{p}</li>" for p in profile.get("leadership_priorities", [])[:4]])
    stats = "  ·  ".join(profile.get("key_statistics", [])[:3])
    sources = ", ".join(profile.get("sources_used", [])[:3])
    return f"""
<div class="slide" id="client-overview">
  <div class="slide-header"><h2>About {rfp.get("client_name", "the Client")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{profile.get("organization_overview", "")}</p>
    <div class="three-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Core Mandate</div>
        <p class="narrative" style="font-size:0.85rem">{profile.get("mandate_and_role", "")}</p>
      </div>
      <div>
        <div class="col-title">Recent Initiatives</div>
        <ul class="bullets">{init_html}</ul>
      </div>
      <div>
        <div class="col-title">Leadership Priorities</div>
        <ul class="bullets">{priorities}</ul>
      </div>
    </div>
    {f'<p style="color:#888;font-size:0.8rem;margin-top:1rem">📊 {stats}</p>' if stats else ""}
    {f'<div class="sources">Sources: {sources}</div>' if sources else ""}
  </div>
</div>"""


def _html_sector_context(sector: dict, rfp: dict) -> str:
    if not sector or sector.get("error"):
        return ""
    drivers = "".join([f"<li>{d}</li>" for d in sector.get("transformation_drivers", [])[:4]])
    challenges = "".join([f"<li>{c}</li>" for c in sector.get("sector_challenges", [])[:4]])
    programs = sector.get("national_programs", [])
    prog_html = "".join([
        f'<li>{p.get("program", p) if isinstance(p, dict) else p}</li>'
        for p in programs[:4]
    ])
    stats = "  ·  ".join(sector.get("market_statistics", [])[:2])
    sources = ", ".join(sector.get("sources_used", [])[:3])
    return f"""
<div class="slide">
  <div class="slide-header">
    <h2>{rfp.get("sector", "Sector")} Landscape — {rfp.get("geography", "UAE")}</h2>
  </div>
  <div class="slide-body">
    <p class="narrative">{sector.get("sector_overview", "")}</p>
    <div class="three-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Transformation Drivers</div>
        <ul class="bullets">{drivers}</ul>
      </div>
      <div>
        <div class="col-title">National Programs</div>
        <ul class="bullets">{prog_html}</ul>
      </div>
      <div>
        <div class="col-title">Key Challenges</div>
        <ul class="bullets">{challenges}</ul>
      </div>
    </div>
    {f'<p style="color:#888;font-size:0.8rem;margin-top:1rem">📊 {stats}</p>' if stats else ""}
    {f'<div class="sources">Sources: {sources}</div>' if sources else ""}
  </div>
</div>"""


def _html_understanding(data: dict) -> str:
    if not data:
        return ""
    raw_drivers = data.get("key_drivers", [])
    drivers = "".join([
        f'<li><strong>{d["driver"]}</strong> — {d["detail"]}</li>' if isinstance(d, dict) else f"<li>{d}</li>"
        for d in raw_drivers
    ])
    raw_challenges = data.get("challenges_identified", [])
    challenges = "".join([
        f'<li><strong>{c["challenge"]}</strong> — {c["implication"]}</li>' if isinstance(c, dict) else f"<li>{c}</li>"
        for c in raw_challenges
    ])
    raw_factors = data.get("success_factors", [])
    factors = "".join([
        f'<li><strong>{f["factor"]}</strong> — {f["why"]}</li>' if isinstance(f, dict) else f"<li>{f}</li>"
        for f in raw_factors
    ])
    narrative = data.get("context_narrative", "")
    perspective = data.get("our_perspective", "")
    return f"""
<div class="slide" id="understanding">
  <div class="slide-header"><h2>{data.get("title", "Our Understanding")}</h2></div>
  <div class="slide-body">
    {f'<p class="narrative">{narrative}</p>' if narrative else ""}
    <div class="three-col" style="margin-top:1rem">
      <div><div class="col-title">Key Drivers</div><ul class="bullets">{drivers}</ul></div>
      <div><div class="col-title">Challenges Identified</div><ul class="bullets">{challenges}</ul></div>
      <div><div class="col-title">Success Factors</div><ul class="bullets">{factors}</ul></div>
    </div>
    {f'<p class="narrative" style="margin-top:1rem;font-style:italic;border-left:3px solid var(--red);padding-left:1rem">{perspective}</p>' if perspective else ""}
  </div>
</div>"""


def _html_value_proposition(data: dict) -> str:
    if not data:
        return ""
    vp_html = ""
    for vp in data.get("value_points", []):
        proof = vp.get("proof_point", "")
        vp_html += f"""
        <div style="padding:0.8rem 0;border-bottom:1px solid #EEE">
          <div style="font-weight:700;color:var(--dark)">► {vp.get("point","")}</div>
          <div style="font-size:0.85rem;color:var(--gray);margin-top:0.2rem">{vp.get("detail","")}</div>
          {f'<div style="font-size:0.78rem;color:var(--red);margin-top:0.2rem;font-style:italic">✓ {proof}</div>' if proof else ""}
        </div>"""
    diff = "".join([f"<li>{d}</li>" for d in data.get("protiviti_differentiators", [])])
    return f"""
<div class="slide" id="value-prop">
  <div class="slide-header"><h2>{data.get("title","Our Value Proposition")}</h2></div>
  <div class="slide-body">
    <p style="font-size:1.05rem;font-weight:600;color:var(--red);margin-bottom:1rem">
      {data.get("headline","")}
    </p>
    <div class="two-col">
      <div>{vp_html}</div>
      <div>
        <div class="col-title">Our Differentiators</div>
        <ul class="bullets">{diff}</ul>
      </div>
    </div>
  </div>
</div>"""


def _html_past_relationship(data: dict) -> str:
    if not data or not data.get("relationship_narrative"):
        return ""
    raw_eng = data.get("past_engagements", [])
    engagements = "".join([
        f'<li><strong>{e.get("engagement","")}</strong> ({e.get("year","")}) — {e.get("outcome","")}</li>'
        if isinstance(e, dict) else f"<li>{e}</li>"
        for e in raw_eng
    ])
    return f"""
<div class="slide">
  <div class="slide-header"><h2>{data.get("title","Our Relationship")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("relationship_narrative","")}</p>
    <div class="two-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Past Engagements</div>
        <ul class="bullets">{engagements}</ul>
      </div>
      <div>
        <div class="col-title">Continuity Benefit</div>
        <p class="narrative">{data.get("continuity_benefit","")}</p>
      </div>
    </div>
  </div>
</div>"""


def _html_scope(scope: dict) -> str:
    if not scope:
        return ""
    phases_html = ""
    for phase in scope.get("phases", []):
        delivs_html = ""
        for d in phase.get("deliverables_l1", []):
            subs = "".join([f'<div class="sub-deliv">↳ {s}</div>' for s in d.get("sub_deliverables", [])])
            delivs_html += f"""
            <div class="deliverable">
              <div class="deliv-name">■ {d.get("name","")}</div>
              <div class="deliv-desc">{d.get("description","")}</div>
              {subs}
            </div>"""
        phases_html += f"""
        <div class="phase-block">
          <div class="phase-name">{phase.get("phase_name","")}</div>
          <div class="phase-obj">{phase.get("phase_objective","")}</div>
          {delivs_html}
        </div>"""
    return f"""
<div class="slide" id="scope">
  <div class="slide-header"><h2>Scope of Work &amp; Deliverables</h2></div>
  <div class="slide-body">{phases_html}</div>
</div>"""


def _html_value_add(data: dict) -> str:
    if not data:
        return ""
    included_html = ""
    for item in data.get("included_in_scope", []):
        included_html += f"""
        <div class="vadd-included">
          <div class="vadd-title">✓ {item.get("title","")} <span class="badge badge-green">Included</span></div>
          <div class="vadd-detail">{item.get("talking_point", item.get("benefit",""))}</div>
        </div>"""
    optional_html = ""
    for item in data.get("optional_addons", []):
        fee = item.get("fee_usd", 0)
        optional_html += f"""
        <div class="vadd-optional">
          <div class="vadd-title">+ {item.get("title","")}
            <span class="badge badge-orange">Optional</span>
            <span class="vadd-fee">USD {fee:,.0f}</span>
          </div>
          <div class="vadd-detail">{item.get("benefit","")}</div>
        </div>"""
    future = data.get("future_phases", [])
    future_text = " · ".join([f.get("title","") for f in future]) if future else ""
    return f"""
<div class="slide" id="value-add">
  <div class="slide-header"><h2>{data.get("title","Our Recommended Enhancements")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("intro","")}</p>
    <div class="two-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Included in Scope — Leading Practice Additions</div>
        {included_html}
      </div>
      <div>
        <div class="col-title">Optional Enhancements</div>
        {optional_html}
        {f'<p style="margin-top:1rem;font-size:0.82rem;color:var(--gray)"><strong>Future phases:</strong> {future_text}</p>' if future_text else ""}
      </div>
    </div>
  </div>
</div>"""


def _html_approach(data: dict) -> str:
    if not data:
        return ""
    # Guiding principles
    principles_html = ""
    for p in data.get("guiding_principles", []):
        if isinstance(p, dict):
            principles_html += f'<li><strong>{p.get("principle","")}</strong> — {p.get("description","")}</li>'
        else:
            principles_html += f"<li>{p}</li>"
    # Methodology steps
    steps_html = ""
    for i, step in enumerate(data.get("methodology_steps", []), 1):
        acts = " · ".join(step.get("activities", []))
        desc = step.get("description", "")
        steps_html += f"""
        <div style="padding:0.6rem 0;border-bottom:1px solid #EEE">
          <div style="font-weight:700;color:var(--dark)">{i}. {step.get("step","")}</div>
          {f'<div style="font-size:0.85rem;color:var(--gray);margin-top:0.2rem">{desc}</div>' if desc else ""}
          {f'<div style="font-size:0.78rem;color:#999;margin-top:0.2rem">{acts}</div>' if acts else ""}
        </div>"""
    # Tools — handle both string and {tool, use_case, benefit} object
    raw_tools = data.get("tools_and_accelerators", [])
    tools = "".join([
        f'<li><strong>{t.get("tool","")}</strong> — {t.get("use_case","")}</li>'
        if isinstance(t, dict) else f"<li>{t}</li>"
        for t in raw_tools
    ])
    return f"""
<div class="slide" id="approach">
  <div class="slide-header"><h2>{data.get("title","Our Approach &amp; Methodology")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("approach_narrative","")}</p>
    {f'<div class="col-title" style="margin-top:1rem">Guiding Principles</div><ul class="bullets">{principles_html}</ul>' if principles_html else ""}
    <div class="two-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Methodology Steps</div>
        {steps_html}
      </div>
      <div>
        <div class="col-title">Tools &amp; Accelerators</div>
        <ul class="bullets">{tools}</ul>
        {f'<div class="col-title" style="margin-top:1rem">Knowledge Transfer</div><p class="narrative">{data.get("knowledge_transfer","")}</p>' if data.get("knowledge_transfer") else ""}
      </div>
    </div>
  </div>
</div>"""


def _html_governance(data: dict) -> str:
    if not data:
        return ""
    # governance_structure can be a dict or a string
    gov_struct = data.get("governance_structure", "")
    if isinstance(gov_struct, dict):
        gov_html = "".join([
            f'<li><strong>{k.replace("_"," ").title()}:</strong> {v}</li>'
            for k, v in gov_struct.items()
        ])
        gov_narrative = f'<ul class="bullets">{gov_html}</ul>'
    else:
        gov_narrative = f'<p class="narrative">{gov_struct}</p>' if gov_struct else ""
    # reporting_cadence — handle both string and {report, frequency, audience, content} objects
    raw_cadence = data.get("reporting_cadence", [])
    cadence = "".join([
        f'<li><strong>{c.get("report","")}</strong> ({c.get("frequency","")}) → {c.get("audience","")} — {c.get("content","")}</li>'
        if isinstance(c, dict) else f"<li>{c}</li>"
        for c in raw_cadence
    ])
    raci = data.get("raci_summary", [])
    raci_html = ""
    if raci:
        rows = "".join([
            f"<tr><td>{r.get('activity','')}</td><td class='text-center'>{r.get('protiviti','')}</td><td class='text-center'>{r.get('client','')}</td></tr>"
            for r in raci[:6]
        ])
        raci_html = f"""
        <table class="raci-table" style="margin-top:1rem">
          <thead><tr><th>Activity</th><th>Protiviti</th><th>Client</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""
    return f"""
<div class="slide" id="governance">
  <div class="slide-header"><h2>{data.get("title","Engagement Governance")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("governance_narrative","")}</p>
    {gov_narrative}
    <div class="two-col" style="margin-top:1rem">
      <div>
        <div class="col-title">Reporting Cadence</div>
        <ul class="bullets">{cadence}</ul>
        <div class="col-title" style="margin-top:1rem">Quality Assurance</div>
        <p class="narrative">{data.get("quality_assurance","")}</p>
      </div>
      <div>
        <div class="col-title">RACI Summary</div>
        {raci_html}
      </div>
    </div>
  </div>
</div>"""


def _html_team(data: dict) -> str:
    if not data:
        return ""
    members_html = ""
    for m in data.get("team_members", [])[:4]:
        resps = "".join([f"<li>{r}</li>" for r in m.get("responsibilities", [])])
        members_html += f"""
        <div style="background:var(--light);padding:1rem;border-radius:5px;border-top:3px solid var(--red)">
          <div style="font-weight:700;color:var(--red);font-size:0.9rem">{m.get("role","")}</div>
          <div style="font-size:0.78rem;color:var(--gray);margin:0.3rem 0">{m.get("relevant_experience","")}</div>
          <ul class="bullets" style="margin-top:0.5rem">{resps}</ul>
        </div>"""
    cols = min(len(data.get("team_members", [])), 3)
    grid = f"grid-template-columns: repeat({max(cols,1)}, 1fr)"
    return f"""
<div class="slide" id="team">
  <div class="slide-header"><h2>{data.get("title","Our Project Team")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("team_narrative","")}</p>
    <div style="display:grid;{grid};gap:1rem;margin-top:1rem">{members_html}</div>
  </div>
</div>"""


def _html_timeline(data: dict) -> str:
    if not data:
        return ""
    phases_html = ""
    for phase in data.get("phases", []):
        milestones = " · ".join(phase.get("key_milestones", []))
        deliverables = " · ".join(phase.get("key_deliverables", []))
        phases_html += f"""
        <div class="timeline-phase">
          <div class="tl-header">
            <span class="tl-phase-name">{phase.get("phase","")}</span>
            <span class="tl-duration">{phase.get("duration","")}</span>
          </div>
          <div class="tl-milestones">
            {f"<strong>Milestones:</strong> {milestones}" if milestones else ""}
            {f" &nbsp;|&nbsp; <strong>Deliverables:</strong> {deliverables}" if deliverables else ""}
          </div>
        </div>"""
    return f"""
<div class="slide" id="timeline">
  <div class="slide-header"><h2>{data.get("title","Engagement Timeline")}</h2></div>
  <div class="slide-body">
    <p style="color:var(--red);font-weight:700;margin-bottom:1rem">
      Total Duration: {data.get("total_duration","")}
    </p>
    {phases_html}
  </div>
</div>"""


def _html_experience(data: dict) -> str:
    if not data:
        return ""
    cases_html = ""
    for cs in data.get("case_studies", [])[:3]:
        cases_html += f"""
        <div class="case-card">
          <div class="case-client">{cs.get("client_type","")}</div>
          <div class="case-title">{cs.get("engagement","")}</div>
          <div class="case-role">{cs.get("our_role","")}</div>
          <div class="case-outcome">→ {cs.get("outcome","")}</div>
        </div>"""
    cols = min(len(data.get("case_studies", [])), 3)
    return f"""
<div class="slide" id="experience">
  <div class="slide-header"><h2>{data.get("title","Our Relevant Experience")}</h2></div>
  <div class="slide-body">
    <p class="narrative">{data.get("narrative","")}</p>
    <div style="display:grid;grid-template-columns:repeat({max(cols,1)},1fr);gap:1rem;margin-top:1rem">
      {cases_html}
    </div>
  </div>
</div>"""


def _html_why_protiviti(data: dict) -> str:
    if not data:
        return ""
    reasons_html = ""
    for r in data.get("reasons", []):
        reasons_html += f"""
        <div style="padding:0.7rem 0;border-bottom:1px solid #EEE">
          <div style="font-weight:700">◆ {r.get("reason","")}</div>
          <div style="font-size:0.85rem;color:var(--gray);margin-top:0.2rem">{r.get("detail","")}</div>
        </div>"""
    return f"""
<div class="slide">
  <div class="slide-header"><h2>{data.get("title","Why Protiviti")}</h2></div>
  <div class="slide-body">
    <p style="font-size:1.05rem;font-weight:600;color:var(--red);margin-bottom:1rem">
      {data.get("headline","")}
    </p>
    {reasons_html}
  </div>
</div>"""


def _html_assumptions(data: dict) -> str:
    if not data:
        return ""
    assumptions = "".join([f"<li>{a}</li>" for a in data.get("assumptions", [])])
    deps = "".join([f"<li>{d}</li>" for d in data.get("client_dependencies", [])])
    oos = "".join([f"<li>{o}</li>" for o in data.get("out_of_scope", [])])
    return f"""
<div class="slide">
  <div class="slide-header"><h2>{data.get("title","Key Assumptions &amp; Dependencies")}</h2></div>
  <div class="slide-body">
    <div class="three-col">
      <div><div class="col-title">Key Assumptions</div><ul class="bullets">{assumptions}</ul></div>
      <div><div class="col-title">Client Dependencies</div><ul class="bullets">{deps}</ul></div>
      <div><div class="col-title">Out of Scope</div><ul class="bullets">{oos}</ul></div>
    </div>
  </div>
</div>"""


def _html_commercial_summary(summary: dict, effort: dict) -> str:
    total_fee = effort.get("total_fee_usd", summary.get("total_fee_usd", 0))
    total_hours = effort.get("total_hours", summary.get("total_hours", 0))
    phases = len(effort.get("phases", []))
    return f"""
<div class="slide" id="commercial-summary">
  <div class="slide-header"><h2>Commercial Summary</h2></div>
  <div class="slide-body">
    <div class="stats-row">
      <div class="stat-box">
        <div class="stat-val">USD {total_fee:,.0f}</div>
        <div class="stat-label">Total Engagement Fee</div>
      </div>
      <div class="stat-box">
        <div class="stat-val">{total_hours:,}</div>
        <div class="stat-label">Total Hours</div>
      </div>
      <div class="stat-box">
        <div class="stat-val">{phases}</div>
        <div class="stat-label">Phases</div>
      </div>
      <div class="stat-box">
        <div class="stat-val">USD {BLENDED_RATE_USD}</div>
        <div class="stat-label">Blended Rate / Hour</div>
      </div>
      <div class="stat-box">
        <div class="stat-val">{summary.get("validity_days", 30)}</div>
        <div class="stat-label">Validity (Days)</div>
      </div>
    </div>
    <p style="color:var(--gray);font-size:0.85rem;margin-top:1rem">
      Payment structure: {summary.get("payment_structure","Milestone-based")}
    </p>
  </div>
</div>"""


def _html_fee_by_phase(fee_phases: list, effort: dict) -> str:
    phases = effort.get("phases", fee_phases)
    total = effort.get("total_fee_usd", 1)
    rows_html = ""
    for phase in phases:
        name = phase.get("phase_name", phase.get("phase", ""))
        fee = phase.get("phase_fee_usd", phase.get("fee_usd", 0))
        hours = phase.get("phase_hours", phase.get("hours", 0))
        pct = round(fee / total * 100) if total else 0
        rows_html += f"""
        <div class="fee-row">
          <div>
            <div style="font-weight:600">{name}</div>
            <div style="font-size:0.8rem;color:var(--gray)">{hours:,} hours</div>
          </div>
          <div class="fee-amount">USD {fee:,.0f} <span style="color:var(--gray);font-weight:400;font-size:0.8rem">({pct}%)</span></div>
        </div>"""
    return f"""
<div class="slide" id="fee-phases">
  <div class="slide-header"><h2>Fee by Phase</h2></div>
  <div class="slide-body">
    {rows_html}
    <div class="fee-row total">
      <div>TOTAL ENGAGEMENT</div>
      <div class="fee-amount">USD {total:,.0f}</div>
    </div>
  </div>
</div>"""


def _html_costing_table(effort: dict) -> str:
    total = effort.get("total_fee_usd", 1)
    rows_html = ""
    for phase in effort.get("phases", []):
        phase_name = phase.get("phase_name", "")
        rows_html += f'<tr class="phase-row"><td colspan="5">{phase_name}</td></tr>'
        for deliv in phase.get("deliverables", []):
            for l2 in deliv.get("sub_deliverables", []):
                fee = l2.get("fee_usd", 0)
                pct = round(fee / total * 100, 1) if total else 0
                rows_html += f"""
                <tr>
                  <td style="color:var(--gray);font-size:0.8rem">{deliv.get("l1_name","")}</td>
                  <td>{l2.get("l2_name","")}</td>
                  <td class="text-center">{l2.get("hours",0)}</td>
                  <td class="text-right">USD {fee:,.0f}</td>
                  <td class="text-center">{pct}%</td>
                </tr>"""
    return f"""
<div class="slide" id="costing">
  <div class="slide-header"><h2>Detailed Effort &amp; Cost Model (L2)</h2></div>
  <div class="slide-body">
    <table class="effort-table">
      <thead>
        <tr>
          <th>L1 Deliverable</th><th>L2 Deliverable</th>
          <th class="text-center">Hours</th>
          <th class="text-right">Fee (USD)</th>
          <th class="text-center">% Total</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
        <tr class="total-row">
          <td colspan="2">TOTAL</td>
          <td class="text-center">{effort.get("total_hours",0):,}</td>
          <td class="text-right">USD {effort.get("total_fee_usd",0):,.0f}</td>
          <td class="text-center">100%</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>"""


def _html_payment_milestones(milestones: list) -> str:
    if not milestones:
        return ""
    cards_html = ""
    for i, m in enumerate(milestones, 1):
        amount = m.get("amount_usd", 0)
        cards_html += f"""
        <div class="milestone-card">
          <div class="milestone-num">#{i}</div>
          <div class="milestone-info">
            <div class="milestone-name">{m.get("milestone","")}</div>
            <div class="milestone-trigger">{m.get("trigger","")} · Week {m.get("due_week","")}</div>
          </div>
          <div class="milestone-amount">USD {amount:,.0f} <span style="font-size:0.8rem;color:var(--gray)">{m.get("percentage","")}</span></div>
        </div>"""
    return f"""
<div class="slide" id="payment">
  <div class="slide-header"><h2>Payment Milestones</h2></div>
  <div class="slide-body">{cards_html}</div>
</div>"""


def _html_commercial_assumptions(commercial: dict) -> str:
    assumptions = "".join([f"<li>{a}</li>" for a in commercial.get("key_assumptions", [])])
    exclusions = "".join([f"<li>{e}</li>" for e in commercial.get("exclusions", [])])
    return f"""
<div class="slide">
  <div class="slide-header"><h2>Key Assumptions &amp; Exclusions</h2></div>
  <div class="slide-body">
    <div class="two-col">
      <div><div class="col-title">Key Assumptions</div><ul class="bullets">{assumptions}</ul></div>
      <div><div class="col-title">Exclusions</div><ul class="bullets">{exclusions}</ul></div>
    </div>
  </div>
</div>"""


def _html_terms(terms: dict) -> str:
    if not terms:
        return ""
    items = [
        ("Payment Terms", terms.get("payment_terms", "")),
        ("Variation Process", terms.get("variation_process", "")),
        ("IP Ownership", terms.get("ip_ownership", "")),
        ("Confidentiality", terms.get("confidentiality", "")),
    ]
    rows = "".join([
        f"<tr><td style='font-weight:600;color:var(--red);width:180px'>{k}</td><td>{v}</td></tr>"
        for k, v in items if v
    ])
    return f"""
<div class="slide">
  <div class="slide-header"><h2>Terms of Engagement</h2></div>
  <div class="slide-body">
    <table style="width:100%;border-collapse:collapse">
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def _html_footer(client_name: str, similar: list) -> str:
    refs = ", ".join(similar[:5]) if similar else "None"
    return f"""
<div class="doc-footer">
  <strong style="color:var(--red)">PROTIVITI MIDDLE EAST</strong> · Real Estate &amp; Infrastructure Practice<br>
  Generated by Proposal Engine · Strictly Confidential · Prepared for {client_name}<br>
  <span style="font-size:0.7rem;margin-top:0.3rem;display:block">
    Reference proposals used: {refs}
  </span>
</div>"""
