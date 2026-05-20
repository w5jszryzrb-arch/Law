"""Shared sidebar renderer used by every page."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

import src.session_manager as sm


_PAGE_ICONS = {
    "case_analysis": "⚖️",
    "essay": "✍️",
    "exam": "📝",
    "notes": "📓",
}


def render_sidebar() -> tuple[str, str]:
    """
    Renders the shared project-aware sidebar.

    Returns (current_subject, current_project_id).
    current_project_id may be "" if no project is active.
    """
    with st.sidebar:
        st.markdown("## ⚖️ NZ Law Assistant")
        st.divider()

        project_id: str = st.session_state.get("current_project_id", "")
        project_data: dict = {}

        if project_id:
            project_data = sm.get_project(project_id) or {}
            if not project_data:
                # Project was deleted elsewhere
                st.session_state.pop("current_project_id", None)
                project_id = ""

        if project_id and project_data:
            subject = project_data.get("subject", "")
            st.markdown(f"**Active project**")
            new_subject = st.text_input(
                "Subject / topic",
                value=subject,
                key="sidebar_subject",
            )
            if new_subject != subject and new_subject.strip():
                sm.update_project(project_id, subject=new_subject)
                st.session_state["current_subject"] = new_subject
                project_data["subject"] = new_subject
            st.session_state["current_subject"] = new_subject or subject

            pages_used = sm.get_project_pages(project_id)
            if pages_used:
                icons = " ".join(_PAGE_ICONS.get(p, "📄") for p in pages_used)
                st.caption(f"Tools used: {icons}")

            st.divider()
            if st.button("← Back to Projects", use_container_width=True):
                st.session_state.pop("current_project_id", None)
                st.switch_page("app.py")
        else:
            current_subject = st.text_input(
                "Subject / topic",
                value=st.session_state.get("current_subject", ""),
                placeholder="e.g. Contract Law — Offer and Acceptance",
            )
            st.session_state["current_subject"] = current_subject
            st.divider()
            if st.button("← Projects Home", use_container_width=True):
                st.switch_page("app.py")

    return (
        st.session_state.get("current_subject", ""),
        st.session_state.get("current_project_id", ""),
    )
