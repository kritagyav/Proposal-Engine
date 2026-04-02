import os
from dotenv import load_dotenv

load_dotenv()

# API key — reads from Streamlit secrets when deployed, .env locally
def _get_api_key():
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        return os.getenv("ANTHROPIC_API_KEY")

ANTHROPIC_API_KEY = _get_api_key()
CLAUDE_MODEL = "claude-sonnet-4-6"

# Paths — work both locally and on Streamlit Cloud
BASE_DIR = os.path.dirname(__file__)
PROPOSALS_FOLDER = os.getenv("PROPOSALS_FOLDER", "/Users/kritagyav/Desktop/Proposal Agent/Proposal PDF")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "data", "vector_db")
TEMPLATES_PATH = os.path.join(BASE_DIR, "templates")
OUTPUTS_PATH = os.path.join(BASE_DIR, "data", "outputs")
os.makedirs(OUTPUTS_PATH, exist_ok=True)

# Commercial
BLENDED_RATE_USD = 120

# Default phases (fallback)
DEFAULT_PHASES = [
    "Phase 1: Discovery & Assessment",
    "Phase 2: Design & Development",
    "Phase 3: Implementation & Change Management",
    "Phase 4: Review & Handover",
]

# Effort estimation benchmarks (hours) per L2 deliverable complexity
EFFORT_BENCHMARKS = {
    "low":    {"min": 8,  "mid": 16,  "max": 24},
    "medium": {"min": 24, "mid": 40,  "max": 60},
    "high":   {"min": 60, "mid": 100, "max": 160},
}
