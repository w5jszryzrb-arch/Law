import os
import sys
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

import src.session_manager as sm

st.set_page_config(
    page_title="NZ Law School Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── API key check ─────────────────────────────────────────────────────────────
api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or not api_key.startswith("sk-"):
    st.error(
        "**ANTHROPIC_API_KEY not set.** Create a `.env` file:\n```\nANTHROPIC_API_KEY=sk-ant-...\n```",
        icon="🔑",
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;margin-bottom:0'>⚖️ NZ Law School Assistant</h1>"
    "<p style='text-align:center;color:grey;margin-top:4px'>"
    "New Zealand law · NZ Law Style Guide (3rd ed) · IRAC structure</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── New Topic ─────────────────────────────────────────────────────────────────
st.markdown("### ✨ New Topic")
with st.container(border=True):
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        new_subject = st.text_input(
            "Subject / topic",
            placeholder="e.g. Contract Law — Offer and Acceptance",
            label_visibility="collapsed",
        )
    with col_btn:
        start = st.button("Start Project", type="primary", use_container_width=True)

    if start:
        if not new_subject.strip():
            st.warning("Please enter a subject or topic first.")
        else:
            project_id = sm.create_project(subject=new_subject.strip())
            st.session_state["current_project_id"] = project_id
            st.session_state["current_subject"] = new_subject.strip()
            st.success(f"Project created: **{new_subject.strip()}**")
            st.markdown("Use the sidebar to navigate to the tools.")
            st.rerun()

st.divider()

# ── My Projects ───────────────────────────────────────────────────────────────
st.markdown("### 📁 My Projects")

projects = sm.list_projects()

if not projects:
    st.info("No projects yet. Start one above.")
else:
    _PAGE_ICONS = {"case_analysis": "⚖️", "essay": "✍️", "exam": "📝", "notes": "📓"}

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
            return dt.strftime("%d %b %Y")
        except Exception:
            return iso[:10]

    # 3-column grid of project cards
    cols = st.columns(3)
    for i, proj in enumerate(projects):
        with cols[i % 3]:
            pages_used = sm.get_project_pages(proj["id"])
            tools_icons = " ".join(_PAGE_ICONS.get(p, "📄") for p in pages_used) if pages_used else "—"
            last_seen = _fmt_date(proj["updated_at"])
            has_rubric = "📋 " if proj.get("rubric") else ""

            with st.container(border=True):
                st.markdown(f"#### {proj['subject']}")
                st.caption(f"{has_rubric}Last active: {last_seen}")
                if tools_icons != "—":
                    st.caption(f"Tools: {tools_icons}")

                btn_col, del_col = st.columns([3, 1])
                with btn_col:
                    if st.button("Open", key=f"open_{proj['id']}", use_container_width=True, type="primary"):
                        st.session_state["current_project_id"] = proj["id"]
                        st.session_state["current_subject"] = proj["subject"]
                        sm.touch_project(proj["id"])
                        st.rerun()
                with del_col:
                    if st.button("🗑️", key=f"del_{proj['id']}", use_container_width=True, help="Delete project"):
                        sm.delete_project(proj["id"])
                        if st.session_state.get("current_project_id") == proj["id"]:
                            st.session_state.pop("current_project_id", None)
                        st.rerun()

# ── Active project banner (after open) ───────────────────────────────────────
active_id = st.session_state.get("current_project_id", "")
if active_id:
    proj = sm.get_project(active_id)
    if proj:
        st.divider()
        st.success(
            f"**Active project:** {proj['subject']}  \n"
            "Use the sidebar ← to navigate to Case Analysis, Essay, Exam, or Notes."
        )
