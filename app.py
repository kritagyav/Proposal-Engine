"""
Proposal Engine — Streamlit Web Interface
Run with: streamlit run app.py
"""
import streamlit as st
import os
import json
from pathlib import Path

st.set_page_config(
    page_title="Proposal Engine | Protiviti ME",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Protiviti brand styling
st.markdown("""
<style>
    .main { background-color: #FAFAFA; }
    .stButton > button {
        background-color: #C8102E;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        border: none;
        padding: 0.6rem 2rem;
    }
    .stButton > button:hover { background-color: #A00D25; }
    h1, h2, h3 { color: #404040; }
    .metric-box {
        background: white;
        border-left: 4px solid #C8102E;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Sidebar
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Protiviti_logo.svg/320px-Protiviti_logo.svg.png",
                 width=180)
        st.markdown("### Proposal Engine")
        st.markdown("*Real Estate & Infrastructure Practice*")
        st.divider()

        page = st.radio("Navigation", [
            "Generate Proposal",
            "Manage Proposal Library",
            "Settings",
        ])

    if page == "Generate Proposal":
        show_generate_page()
    elif page == "Manage Proposal Library":
        show_library_page()
    elif page == "Settings":
        show_settings_page()


def show_generate_page():
    st.title("Generate Proposal")
    st.markdown("Upload an RFP and fill in client context. The engine will generate your Technical Proposal, Commercial Proposal, and Costing Annexure.")
    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Upload RFP")
        rfp_file = st.file_uploader(
            "Upload RFP document",
            type=["pdf", "docx", "doc", "pptx"],
            help="PDF or Word document"
        )

        st.subheader("2. Client Context")
        client_name = st.text_input("Client Name *", placeholder="e.g. Dubai Land Department")
        sector = st.selectbox("Sector", [
            "Government Real Estate Authority",
            "Private Real Estate Developer",
            "Infrastructure / Utilities",
            "Construction & Engineering",
            "Investment & Asset Management",
            "Other",
        ])
        geography = st.selectbox("Geography", ["UAE", "KSA", "Regional (UAE + KSA)", "Other GCC"])
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
        ])

    with col2:
        st.subheader("3. Relationship & Commercial")
        relationship_history = st.text_area(
            "Relationship History",
            placeholder="e.g. Protiviti has supported this client since 2021 on their PMO setup. Key contact is Ahmed Al-Rashidi, Head of Strategy.",
            height=100,
        )
        past_engagements = st.text_area(
            "Past Engagements (if any)",
            placeholder="e.g. PMO Framework Design (2022), Risk Register Development (2023)",
            height=80,
        )
        budget_range = st.text_input(
            "Indicative Budget / Fee Range",
            placeholder="e.g. USD 150,000 - 200,000"
        )
        deadline = st.text_input("Submission Deadline", placeholder="e.g. 15 April 2026")
        key_contacts = st.text_input(
            "Key Client Contacts",
            placeholder="e.g. Ahmed Al-Rashidi (Head of Strategy), Sara Al-Mansoori (PMO)"
        )
        differentiators = st.text_area(
            "Key Differentiators to Emphasize",
            placeholder="e.g. UAE market knowledge, prior relationship, sector specialization",
            height=80,
        )

    st.divider()

    # Validation
    ready = rfp_file is not None and client_name.strip() != ""
    if not ready:
        st.info("Upload an RFP and enter the client name to enable generation.")

    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    with col_btn1:
        generate_clicked = st.button(
            "Generate Proposal Package",
            disabled=not ready,
            use_container_width=True,
        )

    if generate_clicked:
        _run_generation(
            rfp_file=rfp_file,
            client_context={
                "client_name": client_name,
                "sector": sector,
                "geography": geography,
                "engagement_type": engagement_type,
                "relationship_history": relationship_history,
                "past_engagements": past_engagements,
                "budget_range": budget_range,
                "deadline": deadline,
                "key_contacts": key_contacts,
                "differentiators": differentiators,
            }
        )


def _run_generation(rfp_file, client_context: dict):
    from engine.rfp_parser import extract_rfp_text
    from engine.proposal_generator import generate_proposal
    from outputs.html_generator import generate_proposal_html

    client_name = client_context["client_name"]

    with st.status("Generating your proposal...", expanded=True) as status:

        st.write("Parsing RFP document...")
        rfp_text = extract_rfp_text(rfp_file)
        if not rfp_text.strip():
            st.error("Could not extract text from the uploaded RFP. Please check the file.")
            return

        st.write("Searching past proposals for relevant context...")
        st.write("Researching client and sector from web...")
        st.write("Generating proposal content via Claude AI...")
        proposal_data = generate_proposal(rfp_text, client_context)

        st.write("Building HTML proposal...")
        html_path = generate_proposal_html(proposal_data, client_name)

        status.update(label="Proposal ready!", state="complete")

    # Store in session state for on-demand PPT/Excel
    st.session_state["proposal_data"] = proposal_data
    st.session_state["client_name"] = client_name
    st.session_state["html_path"] = html_path

    # ── Results ──────────────────────────────────────────────────────────────
    st.success("Proposal generated. Review below and download when ready.")

    effort = proposal_data.get("effort_model", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Fee", f"USD {effort.get('total_fee_usd', 0):,.0f}")
    col2.metric("Total Hours", f"{effort.get('total_hours', 0):,}")
    col3.metric("Phases", len(effort.get("phases", [])))
    col4.metric("Value-Add Suggestions", len(proposal_data.get("value_add_suggestions", [])))

    st.divider()

    # ── Download buttons ──────────────────────────────────────────────────────
    st.subheader("Download")
    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        with open(html_path, "rb") as f:
            st.download_button(
                label="Download HTML (Primary)",
                data=f,
                file_name=Path(html_path).name,
                mime="text/html",
                use_container_width=True,
                type="primary",
            )
        st.caption("Open in browser → Print → Save as PDF")

    with col_d2:
        if st.button("Generate PowerPoint", use_container_width=True):
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
                st.download_button("↓ Technical Proposal.pptx", f,
                    file_name=Path(st.session_state["tech_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True)
            with open(st.session_state["comm_path"], "rb") as f:
                st.download_button("↓ Commercial Proposal.pptx", f,
                    file_name=Path(st.session_state["comm_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True)

    with col_d3:
        if st.button("Generate Excel Costing", use_container_width=True):
            with st.spinner("Building Excel model..."):
                from outputs.excel_generator import generate_excel
                excel_path = generate_excel(
                    proposal_data["effort_model"], client_name,
                    proposal_data["rfp_intel"].get("project_title", "Engagement")
                )
            st.session_state["excel_path"] = excel_path
            st.rerun()

        if "excel_path" in st.session_state:
            with open(st.session_state["excel_path"], "rb") as f:
                st.download_button("↓ Costing Annexure.xlsx", f,
                    file_name=Path(st.session_state["excel_path"]).name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)

    st.divider()

    # ── HTML Preview ──────────────────────────────────────────────────────────
    st.subheader("Proposal Preview")
    st.caption("This is your full proposal. Scroll through to review before downloading.")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    import streamlit.components.v1 as components
    components.html(html_content, height=900, scrolling=True)


def show_library_page():
    from ingest.proposal_processor import load_all_proposals
    from ingest.vector_store import index_proposals, get_index_stats
    from config import PROPOSALS_FOLDER

    st.title("Proposal Library")
    st.markdown("Manage the past proposals that power the generation engine.")
    st.divider()

    stats = get_index_stats()

    col1, col2 = st.columns(2)
    col1.metric("Proposals Indexed", stats["unique_proposals"])
    col2.metric("Knowledge Chunks", stats["total_chunks"])

    st.subheader("Indexed Proposals")
    if stats["filenames"]:
        for name in stats["filenames"]:
            st.markdown(f"✓ {name}")
    else:
        st.info("No proposals indexed yet. Run ingestion below.")

    st.divider()
    st.subheader("Index New Proposals")
    st.markdown(f"Proposals folder: `{PROPOSALS_FOLDER}`")
    st.markdown("Copy new proposal files (PPT, PDF, DOCX) into the proposals folder, then click below.")

    if st.button("Run Ingestion — Index All Proposals"):
        with st.spinner("Scanning and indexing proposals..."):
            proposals = load_all_proposals(PROPOSALS_FOLDER)
            if not proposals:
                st.error(f"No proposals found in {PROPOSALS_FOLDER}")
            else:
                added = index_proposals(proposals)
                updated_stats = get_index_stats()
                st.success(f"Done. {added} new proposals indexed. Total: {updated_stats['unique_proposals']} proposals.")
                st.rerun()


def show_settings_page():
    from config import PROPOSALS_FOLDER, BLENDED_RATE_USD, CLAUDE_MODEL

    st.title("Settings")
    st.divider()

    st.subheader("Current Configuration")
    st.markdown(f"- **Proposals Folder:** `{PROPOSALS_FOLDER}`")
    st.markdown(f"- **Blended Rate:** USD {BLENDED_RATE_USD}/hour")
    st.markdown(f"- **AI Model:** `{CLAUDE_MODEL}`")

    st.divider()
    st.subheader("Update Configuration")
    st.markdown("Edit the `.env` file in the project folder to update settings.")
    st.code("""
# .env file
ANTHROPIC_API_KEY=your_key_here
PROPOSALS_FOLDER=/path/to/your/proposals
    """, language="bash")

    st.divider()
    st.subheader("API Key Status")
    from config import ANTHROPIC_API_KEY
    if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 10:
        st.success("Anthropic API key is configured.")
    else:
        st.error("Anthropic API key is missing. Add it to your .env file.")


if __name__ == "__main__":
    main()
