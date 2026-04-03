"""
Proposal OS — Protiviti Middle East
Unified proposal development platform powered by Claude AI.

Pages:
  1. Generate Proposal — upload RFP, clarify, generate, refine with Copilot
  2. Proposal Library — manage past proposals (RAG knowledge base)
  3. CV Library — manage consultant CVs
  4. Settings — configuration
"""
import streamlit as st
import os
import json
from pathlib import Path

st.set_page_config(
    page_title="Proposal OS | Protiviti ME",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Protiviti brand styling
st.markdown("""
<style>
    .main { background-color: #FAFAFA; }
    .stButton > button {
        background-color: #C8102E; color: white;
        font-weight: bold; border-radius: 4px;
        border: none; padding: 0.6rem 2rem;
    }
    .stButton > button:hover { background-color: #A00D25; }
    .stButton > button:disabled { background-color: #CCC; color: #888; }
    h1, h2, h3 { color: #404040; }
    .metric-box {
        background: white; border-left: 4px solid #C8102E;
        padding: 1rem; border-radius: 4px; margin: 0.5rem 0;
    }
    .copilot-msg-user {
        background: #FFF0F2; border-left: 3px solid #C8102E;
        padding: 0.6rem 1rem; border-radius: 4px; margin: 0.3rem 0;
        font-size: 0.9rem;
    }
    .copilot-msg-ai {
        background: #F8F8F8; border-left: 3px solid #999;
        padding: 0.6rem 1rem; border-radius: 4px; margin: 0.3rem 0;
        font-size: 0.9rem;
    }
    .clarification-q {
        background: white; border: 1px solid #E0E0E0;
        border-radius: 6px; padding: 0.8rem 1rem; margin: 0.5rem 0;
    }
    .q-category {
        font-size: 0.72rem; font-weight: bold; color: #C8102E;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .q-why { font-size: 0.78rem; color: #888; margin-top: 0.2rem; }
    .section-select-card {
        background: white; border: 1px solid #E0E0E0;
        border-radius: 5px; padding: 0.5rem 0.8rem;
        cursor: pointer; font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    with st.sidebar:
        try:
            st.image(
                "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/"
                "Protiviti_logo.svg/320px-Protiviti_logo.svg.png",
                width=180,
            )
        except Exception:
            st.markdown("### PROTIVITI")
        st.markdown("**Proposal OS**")
        st.markdown("*Real Estate & Infrastructure Practice*")
        st.divider()

        page = st.radio("Navigation", [
            "Generate Proposal",
            "Proposal Library",
            "CV Library",
            "Settings",
        ])

        # Quick stats in sidebar
        st.divider()
        _show_sidebar_stats()

    if page == "Generate Proposal":
        show_generate_page()
    elif page == "Proposal Library":
        show_library_page()
    elif page == "CV Library":
        show_cv_library_page()
    elif page == "Settings":
        show_settings_page()


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE PROPOSAL PAGE
# ══════════════════════════════════════════════════════════════════════════════

def show_generate_page():
    st.title("Generate Proposal")
    st.markdown(
        "Upload an RFP → answer AI clarification questions → generate "
        "Technical + Commercial + Costing → refine with Copilot."
    )
    st.divider()

    # ── If a proposal is already generated, show it first ────────────────────
    if "proposal_data" in st.session_state:
        _show_proposal_results()
        st.divider()
        st.markdown("### Generate a New Proposal")

    # ── Input form ────────────────────────────────────────────────────────────
    with st.expander("RFP Upload & Client Context", expanded=("proposal_data" not in st.session_state)):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("1. Upload RFP")
            rfp_file = st.file_uploader(
                "Upload RFP document",
                type=["pdf", "docx", "doc", "pptx"],
                key="rfp_uploader",
            )

            st.subheader("2. Client Context")
            client_name = st.text_input(
                "Client Name *",
                placeholder="e.g. Dubai Land Department",
                key="client_name_input",
            )
            sector = st.selectbox("Sector", [
                "Government Real Estate Authority",
                "Private Real Estate Developer",
                "Infrastructure / Utilities",
                "Construction & Engineering",
                "Investment & Asset Management",
                "Other",
            ], key="sector_input")
            geography = st.selectbox(
                "Geography",
                ["UAE", "KSA", "Regional (UAE + KSA)", "Other GCC"],
                key="geo_input",
            )
            engagement_type = st.selectbox("Engagement Type", [
                "Operating Model & Governance",
                "Policies & Procedures",
                "ePMO / PMO Setup",
                "Maturity Assessment",
                "Enterprise Risk Management",
                "Project Risk Management",
                "Operational Efficiency",
                "Strategy & Transformation",
                "Other",
            ], key="eng_type_input")

        with col2:
            st.subheader("3. Relationship & Commercial")
            relationship_history = st.text_area(
                "Relationship History",
                placeholder="e.g. Protiviti has supported this client since 2021. "
                            "Key contact: Ahmed Al-Rashidi, Head of Strategy.",
                height=100,
                key="rel_input",
            )
            past_engagements = st.text_area(
                "Past Engagements",
                placeholder="e.g. PMO Framework (2022), Risk Register (2023)",
                height=70,
                key="past_eng_input",
            )
            budget_range = st.text_input(
                "Indicative Budget",
                placeholder="e.g. USD 150,000–200,000",
                key="budget_input",
            )
            deadline = st.text_input(
                "Submission Deadline",
                placeholder="e.g. 15 April 2026",
                key="deadline_input",
            )
            key_contacts = st.text_input(
                "Key Client Contacts",
                placeholder="e.g. Ahmed Al-Rashidi (Head of Strategy)",
                key="contacts_input",
            )
            differentiators = st.text_area(
                "Key Differentiators to Emphasize",
                placeholder="e.g. UAE market knowledge, prior relationship, sector depth",
                height=70,
                key="diff_input",
            )

            # CV selection
            _cv_selector_widget()

    client_context = {
        "client_name": st.session_state.get("client_name_input", ""),
        "sector": st.session_state.get("sector_input", "Government Real Estate Authority"),
        "geography": st.session_state.get("geo_input", "UAE"),
        "engagement_type": st.session_state.get("eng_type_input", "Operating Model & Governance"),
        "relationship_history": st.session_state.get("rel_input", ""),
        "past_engagements": st.session_state.get("past_eng_input", ""),
        "budget_range": st.session_state.get("budget_input", ""),
        "deadline": st.session_state.get("deadline_input", ""),
        "key_contacts": st.session_state.get("contacts_input", ""),
        "differentiators": st.session_state.get("diff_input", ""),
        "selected_cvs": st.session_state.get("selected_cvs", []),
    }

    rfp_file = st.session_state.get("rfp_uploader")
    client_name = client_context["client_name"].strip()

    # ── Step 2: Clarification Engine ──────────────────────────────────────────
    _show_clarification_panel(rfp_file, client_context)

    # ── Generate button ───────────────────────────────────────────────────────
    st.divider()
    ready = rfp_file is not None and client_name != ""
    if not ready:
        st.info("Upload an RFP and enter the client name to enable generation.")

    col_btn, col_tip = st.columns([2, 3])
    with col_btn:
        generate_clicked = st.button(
            "Generate Proposal Package",
            disabled=not ready,
            use_container_width=True,
            key="generate_btn",
        )

    with col_tip:
        if ready:
            clarification_done = bool(st.session_state.get("clarification_answers"))
            if clarification_done:
                st.success(
                    f"{len(st.session_state.get('clarification_questions', []))} "
                    "clarification answers will be included in generation."
                )
            else:
                st.info("Tip: Run the Clarification Check above to improve proposal quality.")

    if generate_clicked and ready:
        clarification_context = _get_clarification_context()
        _run_generation(rfp_file, client_context, clarification_context)


def _show_clarification_panel(rfp_file, client_context: dict):
    """Clarification Engine UI — generates and collects pre-generation questions."""
    with st.expander("AI Clarification Check (Recommended)", expanded=False):
        st.markdown(
            "Before generating, the AI reviews the RFP and asks targeted questions. "
            "Answers are injected into the generation prompts for higher quality output."
        )

        col_clar, _ = st.columns([2, 3])
        with col_clar:
            run_clar = st.button(
                "Generate Clarification Questions",
                key="clar_btn",
                disabled=(rfp_file is None or not client_context.get("client_name", "").strip()),
            )

        if run_clar and rfp_file:
            with st.spinner("Analyzing RFP for clarification gaps..."):
                from engine.rfp_parser import extract_rfp_text
                from engine.clarification_engine import generate_clarification_questions
                rfp_text = extract_rfp_text(rfp_file)
                rfp_file.seek(0)  # Reset for later use
                questions = generate_clarification_questions(rfp_text, client_context)
                st.session_state["clarification_questions"] = questions
                st.session_state["clarification_answers"] = {}

        questions = st.session_state.get("clarification_questions", [])
        if questions:
            st.markdown(f"**{len(questions)} questions identified.** Answer what you know — skip anything uncertain.")
            answers = st.session_state.get("clarification_answers", {})
            for i, q in enumerate(questions):
                st.markdown(
                    f'<div class="clarification-q">'
                    f'<div class="q-category">{q.get("category", "")}</div>'
                    f'<strong>{q.get("question", "")}</strong>'
                    f'<div class="q-why">Why needed: {q.get("why_needed", "")} | '
                    f'Default if skipped: <em>{q.get("default_if_skipped", "")}</em></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                answer = st.text_area(
                    "Your answer:",
                    value=answers.get(str(i), ""),
                    placeholder=q.get("placeholder", ""),
                    height=70,
                    key=f"clar_answer_{i}",
                    label_visibility="collapsed",
                )
                st.session_state.setdefault("clarification_answers", {})[str(i)] = answer


def _get_clarification_context() -> str:
    """Format clarification Q&A into context string for generation."""
    from engine.clarification_engine import format_answers_as_context
    questions = st.session_state.get("clarification_questions", [])
    answers = st.session_state.get("clarification_answers", {})
    return format_answers_as_context(questions, answers)


def _cv_selector_widget():
    """Compact CV selection widget embedded in the form."""
    from engine.cv_engine import get_all_cvs
    cvs = get_all_cvs()
    if not cvs:
        st.caption("No CVs in library. Add them in the CV Library page.")
        return
    cv_options = {f"{cv.get('name', cv['filename'])} — {cv.get('title', '')}": cv["filename"]
                  for cv in cvs}
    selected_labels = st.multiselect(
        "Attach Consultant CVs (optional)",
        options=list(cv_options.keys()),
        key="cv_multiselect",
        help="Selected CVs will be included in the project team section",
    )
    st.session_state["selected_cvs"] = [cv_options[lbl] for lbl in selected_labels]


def _run_generation(rfp_file, client_context: dict, clarification_context: str = ""):
    """Core generation pipeline — called when user clicks Generate."""
    from engine.rfp_parser import extract_rfp_text
    from engine.proposal_generator import generate_proposal
    from outputs.html_generator import generate_proposal_html

    client_name = client_context["client_name"]

    with st.status("Generating your proposal package...", expanded=True) as status:
        st.write("Parsing RFP document...")
        rfp_text = extract_rfp_text(rfp_file)
        if not rfp_text.strip():
            st.error("Could not extract text from the RFP. Check the file format.")
            return

        st.write("Searching proposal library for relevant context...")
        st.write("Researching client and sector from the web...")
        st.write("Extracting intelligence from past proposals...")
        st.write("Generating proposal sections (this takes 3-5 minutes)...")
        proposal_data = generate_proposal(rfp_text, client_context, clarification_context)

        # Inject selected CVs into team section
        _inject_selected_cvs(proposal_data, client_context.get("selected_cvs", []))

        st.write("Building HTML proposal...")
        html_path = generate_proposal_html(proposal_data, client_name)

        status.update(label="Proposal ready!", state="complete")

    # Store in session state
    st.session_state["proposal_data"] = proposal_data
    st.session_state["client_name"] = client_name
    st.session_state["html_path"] = html_path
    # Clear old download files so they regenerate
    for key in ["tech_path", "comm_path", "excel_path", "word_path"]:
        st.session_state.pop(key, None)
    # Clear copilot history
    st.session_state["copilot_history"] = []

    st.rerun()


def _inject_selected_cvs(proposal_data: dict, selected_cv_filenames: list):
    """Replace AI-generated team members with real CVs where selected."""
    if not selected_cv_filenames:
        return
    from engine.cv_engine import get_cv_by_filename, format_cv_for_team_slide

    team = proposal_data.get("technical", {}).get("project_team", {})
    existing_members = team.get("team_members", [])

    # Build CV team members
    cv_members = []
    roles = ["Engagement Director", "Engagement Manager", "Senior Consultant", "Consultant / Analyst"]
    for i, filename in enumerate(selected_cv_filenames[:4]):
        cv = get_cv_by_filename(filename)
        if cv:
            role = roles[i] if i < len(roles) else "Consultant"
            cv_members.append(format_cv_for_team_slide(cv, role_override=role))

    if cv_members:
        # Overlay CV members on top of AI-generated members
        merged = cv_members + existing_members[len(cv_members):]
        team["team_members"] = merged[:4]


def _show_proposal_results():
    """Show the generated proposal — metrics, downloads, preview, and Copilot."""
    proposal_data = st.session_state["proposal_data"]
    client_name = st.session_state["client_name"]
    html_path = st.session_state["html_path"]

    effort = proposal_data.get("effort_model", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Fee", f"USD {effort.get('total_fee_usd', 0):,.0f}")
    col2.metric("Total Hours", f"{effort.get('total_hours', 0):,}")
    col3.metric("Phases", len(effort.get("phases", [])))
    col4.metric("Value-Adds Identified", len(proposal_data.get("value_add_suggestions", [])))

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_preview, tab_download, tab_refine, tab_copilot = st.tabs([
        "Preview", "Download", "Refine Section", "Copilot Chat"
    ])

    with tab_preview:
        st.caption("Full proposal preview. Scroll to review before downloading.")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        import streamlit.components.v1 as components
        components.html(html_content, height=900, scrolling=True)

    with tab_download:
        _download_tab(proposal_data, client_name, html_path)

    with tab_refine:
        _refine_tab(proposal_data, client_name)

    with tab_copilot:
        _copilot_tab(proposal_data)


def _download_tab(proposal_data: dict, client_name: str, html_path: str):
    st.subheader("Download Your Proposal")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**HTML (Primary)**")
        with open(html_path, "rb") as f:
            st.download_button(
                "Download HTML",
                data=f, file_name=Path(html_path).name,
                mime="text/html", use_container_width=True, type="primary",
            )
        st.caption("Open in browser → Print → Save as PDF")

    with col2:
        st.markdown("**Word Document**")
        if st.button("Generate Word Doc", use_container_width=True, key="gen_word"):
            with st.spinner("Building Word document..."):
                from outputs.word_generator import generate_word
                word_path = generate_word(proposal_data, client_name)
                st.session_state["word_path"] = word_path
            st.rerun()
        if "word_path" in st.session_state:
            with open(st.session_state["word_path"], "rb") as f:
                st.download_button(
                    "Download .docx", data=f,
                    file_name=Path(st.session_state["word_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

    with col3:
        st.markdown("**PowerPoint**")
        if st.button("Generate PowerPoint", use_container_width=True, key="gen_ppt"):
            with st.spinner("Building PPT files..."):
                from outputs.ppt_generator import generate_technical_ppt
                from outputs.commercial_ppt import generate_commercial_ppt
                tech_path = generate_technical_ppt(proposal_data, client_name)
                comm_path = generate_commercial_ppt(proposal_data, client_name)
                st.session_state["tech_path"] = tech_path
                st.session_state["comm_path"] = comm_path
            st.rerun()
        if "tech_path" in st.session_state:
            with open(st.session_state["tech_path"], "rb") as f:
                st.download_button(
                    "Technical Proposal.pptx", data=f,
                    file_name=Path(st.session_state["tech_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
            with open(st.session_state["comm_path"], "rb") as f:
                st.download_button(
                    "Commercial Proposal.pptx", data=f,
                    file_name=Path(st.session_state["comm_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )

    with col4:
        st.markdown("**Excel Costing**")
        if st.button("Generate Excel", use_container_width=True, key="gen_excel"):
            with st.spinner("Building Excel model..."):
                from outputs.excel_generator import generate_excel
                excel_path = generate_excel(
                    proposal_data["effort_model"], client_name,
                    proposal_data["rfp_intel"].get("project_title", "Engagement"),
                )
                st.session_state["excel_path"] = excel_path
            st.rerun()
        if "excel_path" in st.session_state:
            with open(st.session_state["excel_path"], "rb") as f:
                st.download_button(
                    "Costing Annexure.xlsx", data=f,
                    file_name=Path(st.session_state["excel_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    # Intelligence panel
    st.divider()
    col_intel1, col_intel2 = st.columns(2)
    with col_intel1:
        intel = proposal_data.get("proposal_intelligence", {})
        if intel.get("fee_benchmarks", {}).get("recommended_fee_range"):
            st.info(f"Fee Benchmark: {intel['fee_benchmarks']['recommended_fee_range']}")
    with col_intel2:
        similar = proposal_data.get("similar_proposals_used", [])
        if similar:
            st.caption(f"Generated using {len(similar)} similar past proposals as context: "
                       + ", ".join(similar[:3]))


def _refine_tab(proposal_data: dict, client_name: str):
    """Section-level AI refinement — user selects a section and gives instructions."""
    from engine.copilot import SECTION_KEYS, refine_section

    st.subheader("Refine a Proposal Section")
    st.markdown(
        "Select any section, describe what to change, and the AI will "
        "rewrite it while keeping the rest of the proposal intact."
    )

    col_sel, col_instr = st.columns([1, 2])
    with col_sel:
        section_name = st.selectbox(
            "Select section to refine",
            options=list(SECTION_KEYS.keys()),
            key="refine_section_select",
        )

    with col_instr:
        instruction = st.text_area(
            "What should change?",
            placeholder=(
                "Examples:\n"
                "• Make the executive summary more assertive and outcome-focused\n"
                "• Add more detail on digital transformation tools in the approach\n"
                "• Make scope Phase 2 more specific about deliverable formats\n"
                "• Strengthen the Why Protiviti section with more regional evidence"
            ),
            height=120,
            key="refine_instruction",
        )

    col_btn, col_note = st.columns([1, 2])
    with col_btn:
        refine_clicked = st.button(
            "Apply Refinement",
            key="refine_btn",
            disabled=not instruction.strip(),
            use_container_width=True,
        )

    if refine_clicked and instruction.strip():
        section_key = SECTION_KEYS[section_name]
        current = proposal_data.get("technical", {}).get(section_key, {})

        with st.spinner(f"Refining {section_name}..."):
            updated, explanation = refine_section(
                section_name, current, instruction, proposal_data
            )

        # Update session state
        st.session_state["proposal_data"]["technical"][section_key] = updated
        st.session_state.pop("html_path", None)  # Regenerate HTML

        # Regenerate HTML
        from outputs.html_generator import generate_proposal_html
        html_path = generate_proposal_html(st.session_state["proposal_data"], client_name)
        st.session_state["html_path"] = html_path
        # Clear download files so they regenerate with updated content
        for key in ["tech_path", "comm_path", "word_path"]:
            st.session_state.pop(key, None)

        st.success(f"{section_name} updated. {explanation}")
        st.rerun()

    # Show refinement history
    if "refinement_log" not in st.session_state:
        st.session_state["refinement_log"] = []
    if st.session_state.get("refinement_log"):
        with st.expander("Refinement history"):
            for entry in reversed(st.session_state["refinement_log"][-5:]):
                st.markdown(f"- **{entry['section']}**: {entry['instruction']}")


def _copilot_tab(proposal_data: dict):
    """Persistent chat with a senior partner who knows the full proposal."""
    from engine.copilot import chat_about_proposal

    st.subheader("Proposal Copilot")
    st.markdown(
        "Chat with an AI Senior Partner who has read the full proposal. "
        "Ask strategic questions, request feedback, or explore alternatives."
    )

    # Initialize history
    if "copilot_history" not in st.session_state:
        st.session_state["copilot_history"] = []

    # Display history
    history = st.session_state["copilot_history"]
    for msg in history:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="copilot-msg-user"><strong>You:</strong> {msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="copilot-msg-ai"><strong>Senior Partner:</strong> {msg["content"]}</div>',
                unsafe_allow_html=True,
            )

    # Input
    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_msg = st.text_input(
            "Ask anything about this proposal...",
            placeholder=(
                "e.g. 'Is our fee competitive for this scope?' | "
                "'How can we strengthen the scope vs competitors?' | "
                "'What's the riskiest assumption in this proposal?'"
            ),
            key="copilot_input",
            label_visibility="collapsed",
        )
    with col_send:
        send = st.button("Send", key="copilot_send", use_container_width=True)

    if send and user_msg.strip():
        with st.spinner("Senior Partner is reviewing..."):
            reply = chat_about_proposal(user_msg, proposal_data, history)

        st.session_state["copilot_history"].append({"role": "user", "content": user_msg})
        st.session_state["copilot_history"].append({"role": "assistant", "content": reply})
        st.rerun()

    if history:
        if st.button("Clear chat", key="clear_chat"):
            st.session_state["copilot_history"] = []
            st.rerun()

    # Suggested prompts
    if not history:
        st.markdown("**Try these:**")
        prompts = [
            "Is this proposal competitive? What would make it stronger?",
            "What are the biggest risks in this proposal?",
            "How should I position the fee in the cover meeting?",
            "What leading practice additions could differentiate us?",
            "Is the scope realistic for the timeline we proposed?",
        ]
        for i, prompt in enumerate(prompts):
            if st.button(prompt, key=f"suggest_{i}"):
                with st.spinner("Senior Partner is reviewing..."):
                    reply = chat_about_proposal(prompt, proposal_data, [])
                st.session_state["copilot_history"].append({"role": "user", "content": prompt})
                st.session_state["copilot_history"].append({"role": "assistant", "content": reply})
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PROPOSAL LIBRARY PAGE
# ══════════════════════════════════════════════════════════════════════════════

def show_library_page():
    from ingest.proposal_processor import load_all_proposals
    from ingest.vector_store import index_proposals, get_index_stats
    from config import PROPOSALS_FOLDER

    st.title("Proposal Library")
    st.markdown(
        "Past proposals power the generation engine via RAG. "
        "The more proposals indexed, the better the output."
    )
    st.divider()

    stats = get_index_stats()
    col1, col2 = st.columns(2)
    col1.metric("Proposals Indexed", stats["unique_proposals"])
    col2.metric("Knowledge Entries", stats["total_chunks"])

    if stats["filenames"]:
        st.subheader("Indexed Proposals")
        for name in stats["filenames"]:
            st.markdown(f"✓ {name}")
    else:
        st.info("No proposals indexed yet. Run ingestion below.")

    st.divider()
    st.subheader("Index New Proposals")
    st.markdown(f"Proposals folder: `{PROPOSALS_FOLDER}`")

    if st.button("Run Ingestion — Scan & Index All Proposals"):
        with st.spinner("Scanning and indexing proposals..."):
            proposals = load_all_proposals(PROPOSALS_FOLDER)
            if not proposals:
                st.error(f"No proposals found in: {PROPOSALS_FOLDER}")
            else:
                added = index_proposals(proposals)
                updated = get_index_stats()
                st.success(
                    f"Done. {added} new proposals indexed. "
                    f"Total: {updated['unique_proposals']} proposals in library."
                )
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CV LIBRARY PAGE
# ══════════════════════════════════════════════════════════════════════════════

def show_cv_library_page():
    from engine.cv_engine import get_all_cvs, process_cv_upload, delete_cv

    st.title("CV Library")
    st.markdown(
        "Upload consultant CVs. They will be parsed by AI and made available "
        "for attachment to proposals — replacing the AI-generated team section "
        "with real team profiles."
    )
    st.divider()

    # Upload new CV
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Upload CV")
        cv_file = st.file_uploader(
            "Upload consultant CV (PDF or Word)",
            type=["pdf", "docx", "doc"],
            key="cv_uploader",
        )
        if cv_file is not None:
            if st.button("Parse & Add to Library", key="parse_cv_btn"):
                with st.spinner(f"Parsing {cv_file.name}..."):
                    profile = process_cv_upload(cv_file)
                if "error" in profile:
                    st.error(f"Parse error: {profile['error']}")
                else:
                    st.success(
                        f"Added: {profile.get('name', cv_file.name)} | "
                        f"{profile.get('title', '')} | "
                        f"{profile.get('years_experience', '')} years experience"
                    )
                    st.rerun()

    # Existing CVs
    with col2:
        st.subheader("CV Library")
        cvs = get_all_cvs()
        if not cvs:
            st.info("No CVs uploaded yet.")
        else:
            st.caption(f"{len(cvs)} consultant CVs in library")
            for cv in cvs:
                with st.expander(
                    f"{cv.get('name', cv.get('filename', ''))} — "
                    f"{cv.get('title', '')} | "
                    f"{cv.get('years_experience', '')} yrs"
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**Summary:** {cv.get('summary', '')}")
                        st.markdown(f"**Sectors:** {', '.join(cv.get('sector_experience', []))}")
                        st.markdown(f"**Expertise:** {', '.join(cv.get('key_expertise', [])[:4])}")
                    with col_b:
                        projects = cv.get("key_projects", [])
                        if projects:
                            st.markdown("**Key Projects:**")
                            for p in projects[:3]:
                                st.markdown(
                                    f"- {p.get('title', '')} | "
                                    f"{p.get('client_type', '')} | "
                                    f"{p.get('geography', '')}"
                                )
                    if st.button(
                        f"Remove {cv.get('name', cv['filename'])}",
                        key=f"del_cv_{cv['filename']}",
                    ):
                        delete_cv(cv["filename"])
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def show_settings_page():
    from config import PROPOSALS_FOLDER, BLENDED_RATE_USD, CLAUDE_MODEL, ANTHROPIC_API_KEY

    st.title("Settings")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Configuration")
        st.markdown(f"- **Proposals Folder:** `{PROPOSALS_FOLDER}`")
        st.markdown(f"- **Blended Rate:** USD {BLENDED_RATE_USD}/hour")
        st.markdown(f"- **AI Model:** `{CLAUDE_MODEL}`")

        st.subheader("API Key Status")
        if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 10:
            st.success("Anthropic API key is configured.")
        else:
            st.error("Anthropic API key missing. Add to .env or Streamlit secrets.")

    with col2:
        st.subheader("Update Configuration")
        st.markdown("Edit `.env` file to update local settings:")
        st.code("""
# .env
ANTHROPIC_API_KEY=your_key_here
PROPOSALS_FOLDER=/path/to/proposals
        """, language="bash")
        st.markdown("For Streamlit Cloud, update secrets in the dashboard.")

    st.divider()
    st.subheader("Architecture Overview")
    st.markdown("""
**Engines running in this system:**
- **RFP Parser** — PDF, DOCX, PPTX text extraction
- **Clarification Engine** — AI-generated pre-generation questions
- **Research Engine** — Claude web search for client + sector context
- **Retrieval Engine** — TF-IDF similarity search across past proposals
- **Proposal Intelligence** — NotebookLM-style deep reading of past proposals
- **Content Engine** — 6-section parallel generation with full context
- **Value-Add Suggester** — Leading practice recommendations beyond RFP scope
- **CV Engine** — Consultant CV parsing and proposal injection
- **Copilot** — Post-generation chat + section-level refinement

**Outputs:**
- HTML (primary, print-to-PDF)
- Word document (.docx)
- PowerPoint — Technical + Commercial
- Excel costing annexure (4 sheets)
    """)


# ── Sidebar stats ─────────────────────────────────────────────────────────────

def _show_sidebar_stats():
    try:
        from ingest.vector_store import get_index_stats
        from engine.cv_engine import get_all_cvs
        stats = get_index_stats()
        cvs = get_all_cvs()
        st.caption(f"📚 {stats['unique_proposals']} proposals indexed")
        st.caption(f"👤 {len(cvs)} CVs in library")
        if "proposal_data" in st.session_state:
            effort = st.session_state["proposal_data"].get("effort_model", {})
            fee = effort.get("total_fee_usd", 0)
            if fee:
                st.caption(f"📋 Last: USD {fee:,.0f}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
