"""
CV Engine — parse, store, and surface consultant CVs for proposals.

Workflow:
1. Upload CV (PDF or DOCX) via UI
2. Claude extracts structured profile data
3. Stored in data/cv_index.json
4. During proposal generation, selected CVs are injected into project_team section
5. CVs are also rendered in HTML and Word outputs
"""
import json
import os
import tempfile
from pathlib import Path
import pdfplumber
from docx import Document
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, BASE_DIR

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CV_INDEX_PATH = os.path.join(BASE_DIR, "data", "cv_index.json")


# ── Public API ────────────────────────────────────────────────────────────────

def process_cv_upload(uploaded_file) -> dict:
    """
    Full pipeline: extract text → parse with Claude → save → return profile.
    uploaded_file: Streamlit UploadedFile
    """
    text = _extract_cv_text(uploaded_file)
    if not text or len(text.strip()) < 50:
        return {"error": "Could not extract text from CV. Check the file format."}

    profile = _parse_cv_with_claude(text, uploaded_file.name)
    if "error" not in profile:
        save_cv_profile(profile)
    return profile


def save_cv_profile(profile: dict):
    """Save or update a CV profile in the index."""
    index = get_all_cvs()
    index = [cv for cv in index if cv.get("filename") != profile.get("filename")]
    index.append(profile)
    _save_index(index)


def get_all_cvs() -> list[dict]:
    return _load_index()


def delete_cv(filename: str):
    index = [cv for cv in get_all_cvs() if cv.get("filename") != filename]
    _save_index(index)


def get_cv_by_filename(filename: str) -> dict | None:
    for cv in get_all_cvs():
        if cv.get("filename") == filename:
            return cv
    return None


def format_cv_for_team_slide(cv: dict, role_override: str = "") -> dict:
    """
    Format a CV profile as a team_member dict compatible with
    the proposal_generator's project_team structure.
    """
    projects = cv.get("key_projects", [])[:3]
    relevant_exp = (
        f"{cv.get('summary', '')} "
        + " | ".join([
            f"{p.get('title', '')} ({p.get('geography', '')})"
            for p in projects
        ])
    )
    return {
        "role": role_override or cv.get("title", "Consultant"),
        "title": cv.get("title", ""),
        "name": cv.get("name", ""),
        "responsibilities": cv.get("key_expertise", [])[:4],
        "relevant_experience": relevant_exp.strip(),
        "years_experience": cv.get("years_experience", ""),
        "education": cv.get("education", []),
        "certifications": cv.get("certifications", []),
        "languages": cv.get("languages", []),
    }


def format_cv_full_text(cv: dict) -> str:
    """Format CV as clean text for injection into generation prompts."""
    projects_text = "\n".join([
        f"  • {p.get('title', '')} — {p.get('client_type', '')} | "
        f"Role: {p.get('role', '')} | {p.get('description', '')}"
        for p in cv.get("key_projects", [])[:4]
    ])
    return f"""
NAME: {cv.get('name', '')} | TITLE: {cv.get('title', '')}
EXPERIENCE: {cv.get('years_experience', '')} years
SUMMARY: {cv.get('summary', '')}
EXPERTISE: {', '.join(cv.get('key_expertise', []))}
SECTORS: {', '.join(cv.get('sector_experience', []))}
KEY PROJECTS:
{projects_text}
EDUCATION: {', '.join(cv.get('education', [])[:2])}
CERTIFICATIONS: {', '.join(cv.get('certifications', [])[:3])}
""".strip()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_cv_text(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        if suffix == ".pdf":
            pages = []
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text.strip())
            return "\n\n".join(pages)
        elif suffix in (".docx", ".doc"):
            doc = Document(tmp_path)
            return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"CV text extraction error: {e}")
    finally:
        os.unlink(tmp_path)
    return ""


def _parse_cv_with_claude(cv_text: str, filename: str) -> dict:
    prompt = f"""Extract structured information from this consultant CV.
Be precise — only include information that is actually in the CV.

CV TEXT:
{cv_text[:5000]}

Return JSON:
{{
  "name": "Full name",
  "title": "Current title / role",
  "years_experience": 0,
  "summary": "2-3 sentence professional summary focusing on sector and engagement type expertise",
  "key_expertise": ["expertise area 1", "area 2", "area 3", "area 4", "area 5"],
  "sector_experience": ["Real Estate", "Government", "Infrastructure", "etc"],
  "geography_experience": ["UAE", "KSA", "etc"],
  "key_projects": [
    {{
      "title": "Project/engagement title",
      "client_type": "Type of client (anonymised if needed)",
      "role": "Consultant's role on this project",
      "description": "1-2 sentences on what was done and outcomes",
      "geography": "UAE / KSA / etc",
      "year": "Year or approximate"
    }}
  ],
  "education": ["Degree, Institution", "Second degree if applicable"],
  "certifications": ["Cert 1", "Cert 2"],
  "languages": ["English", "Arabic"],
  "linkedin": ""
}}

Return only valid JSON."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        parsed["filename"] = filename
        return parsed
    except Exception as e:
        print(f"CV parse error: {e}")
        return {"filename": filename, "name": filename, "error": str(e)}


def _load_index() -> list:
    if os.path.exists(CV_INDEX_PATH):
        try:
            with open(CV_INDEX_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_index(index: list):
    os.makedirs(os.path.dirname(CV_INDEX_PATH), exist_ok=True)
    with open(CV_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
