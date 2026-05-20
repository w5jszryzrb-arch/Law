import os
import sys
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

import src.session_manager as sm
from src.styles import apply_styles

st.set_page_config(
    page_title="NZ Law School Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_styles()

# ── API key check ─────────────────────────────────────────────────────────────
api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or not api_key.startswith("sk-"):
    st.error(
        "**API key not configured.** Create a `.env` file in the project root:\n"
        "```\nANTHROPIC_API_KEY=sk-ant-...\n```",
        icon="🔑",
    )

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B2D4F 0%, #253D68 55%, #2D5AA0 100%);
    border-radius: 16px;
    padding: 2.5rem 2.5rem 2rem;
    margin-bottom: 2rem;
    color: white;
">
    <div style="display:flex; align-items:center; gap:16px; margin-bottom:.5rem;">
        <span style="font-size:2.8rem; line-height:1;">⚖️</span>
        <div>
            <h1 style="font-family:'Crimson Pro',Georgia,serif; font-size:2.4rem;
                       font-weight:700; color:#fff; margin:0; line-height:1.1;">
                NZ Law School Assistant
            </h1>
            <p style="color:rgba(255,255,255,.72); margin:.4rem 0 0; font-size:.95rem;">
                AI-powered study companion · New Zealand law · NZ Law Style Guide (3rd ed)
            </p>
        </div>
    </div>
    <div style="display:flex; gap:12px; margin-top:1.25rem; flex-wrap:wrap;">
        <span style="background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);
                     border-radius:99px; padding:4px 14px; font-size:.8rem; color:rgba(255,255,255,.85);">
            ⚖️ Case Law Analysis
        </span>
        <span style="background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);
                     border-radius:99px; padding:4px 14px; font-size:.8rem; color:rgba(255,255,255,.85);">
            ✍️ Essay Writing
        </span>
        <span style="background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);
                     border-radius:99px; padding:4px 14px; font-size:.8rem; color:rgba(255,255,255,.85);">
            📝 Exam Practice
        </span>
        <span style="background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);
                     border-radius:99px; padding:4px 14px; font-size:.8rem; color:rgba(255,255,255,.85);">
            📓 Notes Generator
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── New Topic ─────────────────────────────────────────────────────────────────
st.markdown("### ✨ Start a New Project")

with st.container(border=True):
    st.markdown(
        "<p style='color:#64748B; font-size:.875rem; margin-bottom:.75rem;'>"
        "Each project saves your conversations, essay drafts, rubric, and exam questions — "
        "so you can pick up right where you left off."
        "</p>",
        unsafe_allow_html=True,
    )
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        new_subject = st.text_input(
            "Subject or topic",
            placeholder="e.g.  Contract Law — Offer and Acceptance  |  Tort — Negligence  |  Criminal Law",
            label_visibility="collapsed",
        )
    with col_btn:
        start = st.button("Start →", type="primary", use_container_width=True)

    if start:
        if not new_subject.strip():
            st.warning("Enter a subject or topic to begin.")
        else:
            project_id = sm.create_project(subject=new_subject.strip())
            st.session_state["current_project_id"] = project_id
            st.session_state["current_subject"] = new_subject.strip()
            st.rerun()

# ── Active project redirect banner ───────────────────────────────────────────
active_id = st.session_state.get("current_project_id", "")
if active_id:
    proj = sm.get_project(active_id)
    if proj:
        st.markdown(
            f"""<div style="background:#ECFDF5; border:1.5px solid #A7F3D0; border-left:4px solid #059669;
                           border-radius:12px; padding:1rem 1.25rem; margin:.75rem 0;">
                <strong style="color:#065F46;">Active project:</strong>
                <span style="color:#065F46;"> {proj['subject']}</span>
                <span style="color:#6EE7B7; margin-left:12px; font-size:.82rem;">
                    Use the sidebar ← to navigate to your tools
                </span>
            </div>""",
            unsafe_allow_html=True,
        )

st.divider()

# ── My Projects ───────────────────────────────────────────────────────────────
projects = sm.list_projects()

_PAGE_ICONS = {"case_analysis": "⚖️", "essay": "✍️", "exam": "📝", "notes": "📓"}

col_title, col_count = st.columns([5, 1])
with col_title:
    st.markdown("### 📁 My Projects")
with col_count:
    if projects:
        st.markdown(
            f"<p style='text-align:right; color:#64748B; font-size:.85rem; padding-top:.9rem;'>"
            f"{len(projects)} project{'s' if len(projects)!=1 else ''}</p>",
            unsafe_allow_html=True,
        )

if not projects:
    st.markdown(
        """<div style="background:white; border:1.5px dashed #DDE3EE; border-radius:12px;
                      padding:2.5rem; text-align:center;">
            <p style="font-size:2rem; margin:0;">📚</p>
            <p style="color:#64748B; margin:.5rem 0 0; font-size:.9rem;">
                No projects yet. Start one above to begin.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )
else:
    def _fmt_date(iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso)
            delta = datetime.utcnow() - dt
            if delta.days == 0:
                h = delta.seconds // 3600
                return "Today" if h == 0 else f"{h}h ago"
            if delta.days == 1:
                return "Yesterday"
            if delta.days < 7:
                return f"{delta.days}d ago"
            return dt.strftime("%-d %b %Y")
        except Exception:
            return iso[:10]

    cols = st.columns(3)
    for i, proj in enumerate(projects):
        pages_used = sm.get_project_pages(proj["id"])
        tools = " ".join(_PAGE_ICONS.get(p, "") for p in pages_used) if pages_used else ""
        last_seen = _fmt_date(proj["updated_at"])
        is_active = proj["id"] == st.session_state.get("current_project_id", "")
        rubric_tag = "📋 " if proj.get("rubric") else ""

        with cols[i % 3]:
            active_border = "border-color:#1B2D4F; box-shadow:0 0 0 2px rgba(27,45,79,.15);" if is_active else ""
            st.markdown(
                f"""<div class="project-card" style="{active_border}">
                    <p class="subject">{proj['subject']}</p>
                    <p class="meta">{rubric_tag}Last active: {last_seen}</p>
                    {"<p class='tools'>" + tools + "</p>" if tools else ""}
                </div>""",
                unsafe_allow_html=True,
            )
            btn_col, del_col = st.columns([3, 1])
            with btn_col:
                label = "✓ Active" if is_active else "Open →"
                if st.button(label, key=f"open_{proj['id']}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state["current_project_id"] = proj["id"]
                    st.session_state["current_subject"] = proj["subject"]
                    # Reset page-level state so saved conversations reload
                    for key in ["case_chat_history","essay_chat_history","essay_question_input",
                                "essay_plan","essay_draft","generated_question"]:
                        st.session_state.pop(key, None)
                    sm.touch_project(proj["id"])
                    st.rerun()
            with del_col:
                if st.button("🗑", key=f"del_{proj['id']}", use_container_width=True,
                             help="Delete this project"):
                    sm.delete_project(proj["id"])
                    if st.session_state.get("current_project_id") == proj["id"]:
                        st.session_state.pop("current_project_id", None)
                    st.rerun()

# ── How it works ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🗺️ How to use this tool")

c1, c2, c3, c4 = st.columns(4)
cards = [
    ("📂", "1. Upload Materials",
     "Upload lecture slides, case law PDFs, past papers, and workshop questions in **Documents**."),
    ("🔬", "2. Analyse Cases",
     "Get full IRAC analysis, extract the ratio decidendi, compare cases, or chat about a case."),
    ("✍️", "3. Write Essays",
     "Analyse your question, generate a structured plan, draft in NZ academic style, get critique."),
    ("📝", "4. Practise Exams",
     "Generate practice questions from your course materials only, get model answers, and get marked."),
]
for col, (icon, title, body) in zip([c1,c2,c3,c4], cards):
    with col:
        st.markdown(
            f"""<div style="background:white; border:1.5px solid #DDE3EE; border-radius:12px;
                           padding:1.1rem 1.1rem 1.25rem; height:100%;
                           box-shadow:0 1px 3px rgba(27,45,79,.06);">
                <p style="font-size:1.6rem; margin:0 0 .5rem;">{icon}</p>
                <p style="font-weight:600; color:#1B2D4F; margin:0 0 .4rem; font-size:.9rem;">{title}</p>
                <p style="color:#64748B; font-size:.82rem; line-height:1.55; margin:0;">{body}</p>
            </div>""",
            unsafe_allow_html=True,
        )
