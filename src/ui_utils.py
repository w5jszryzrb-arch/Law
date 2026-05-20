"""Shared sidebar and helpers used by every page."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

import src.session_manager as sm
from src.styles import apply_styles

_PAGE_META = {
    "case_analysis": ("⚖️", "Case Analysis"),
    "essay":         ("✍️", "Essay Assistant"),
    "exam":          ("📝", "Exam Practice"),
    "notes":         ("📓", "Notes"),
}


def render_sidebar() -> tuple[str, str]:
    """
    Renders the shared project-aware sidebar.
    Returns (current_subject, current_project_id).
    """
    apply_styles()

    with st.sidebar:
        # Logo / title
        st.markdown(
            "<h2 style='font-family:Crimson Pro,Georgia,serif; font-size:1.4rem;"
            " margin:0 0 .15rem; color:white;'>⚖️ NZ Law Assistant</h2>"
            "<p style='font-size:.73rem; color:rgba(255,255,255,.50); margin:0 0 1rem;'>"
            "New Zealand law · IRAC · NZ Style Guide</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        project_id: str = st.session_state.get("current_project_id", "")
        project_data: dict = {}

        if project_id:
            project_data = sm.get_project(project_id) or {}
            if not project_data:
                st.session_state.pop("current_project_id", None)
                project_id = ""

        if project_id and project_data:
            subject = project_data.get("subject", "")

            # Active project pill
            st.markdown(
                f"<div style='background:rgba(201,168,76,.18); border:1px solid rgba(201,168,76,.4);"
                f" border-radius:8px; padding:.55rem .85rem; margin-bottom:.75rem;'>"
                f"<p style='font-size:.7rem; text-transform:uppercase; letter-spacing:.5px;"
                f" color:rgba(255,255,255,.55); margin:0 0 .2rem;'>Active project</p>"
                f"<p style='font-size:.95rem; font-weight:600; color:#fff; margin:0; "
                f" font-family:Crimson Pro,Georgia,serif; line-height:1.25;'>{subject}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

            new_subject = st.text_input(
                "Subject / topic",
                value=subject,
                key="sidebar_subject_input",
                help="Update the subject for this project",
            )
            if new_subject.strip() and new_subject.strip() != subject:
                sm.update_project(project_id, subject=new_subject.strip())
                st.session_state["current_subject"] = new_subject.strip()

            st.session_state["current_subject"] = new_subject or subject

            # Tools used
            pages_used = sm.get_project_pages(project_id)
            if pages_used:
                icons = "  ".join(
                    _PAGE_META.get(p, ("📄", p))[0] for p in pages_used
                )
                st.markdown(
                    f"<p style='font-size:.75rem; color:rgba(255,255,255,.45); margin:.25rem 0 0;'>"
                    f"Used: {icons}</p>",
                    unsafe_allow_html=True,
                )

            st.divider()

            # Navigation
            st.markdown(
                "<p style='font-size:.72rem; text-transform:uppercase; letter-spacing:.5px;"
                " color:rgba(255,255,255,.45); margin:0 0 .5rem;'>Navigate</p>",
                unsafe_allow_html=True,
            )

            pages = [
                ("pages/1_Documents.py",      "📂  Documents"),
                ("pages/2_Case_Analysis.py",  "⚖️  Case Analysis"),
                ("pages/3_Essay_Assistant.py","✍️  Essay Assistant"),
                ("pages/4_Exam_Practice.py",  "📝  Exam Practice"),
                ("pages/5_Notes.py",          "📓  Notes"),
            ]
            for path, label in pages:
                if st.button(label, key=f"nav_{path}", use_container_width=True):
                    st.switch_page(path)

            st.divider()
            if st.button("← All Projects", use_container_width=True, key="nav_home"):
                st.switch_page("app.py")

        else:
            # No active project
            st.markdown(
                "<p style='font-size:.8rem; color:rgba(255,255,255,.55); margin-bottom:.75rem;'>"
                "No active project. Go to the home page to start or open one.</p>",
                unsafe_allow_html=True,
            )

            current_subject = st.text_input(
                "Subject / topic",
                value=st.session_state.get("current_subject", ""),
                placeholder="e.g. Contract Law",
                key="sidebar_subject_noproj",
            )
            st.session_state["current_subject"] = current_subject

            st.divider()
            if st.button("← Projects Home", use_container_width=True, key="nav_home_noproj"):
                st.switch_page("app.py")

    return (
        st.session_state.get("current_subject", ""),
        st.session_state.get("current_project_id", ""),
    )
