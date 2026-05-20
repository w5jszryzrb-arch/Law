import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import config
import src.session_manager as sm
from src.vector_store import LegalVectorStore
from src.claude_client import ClaudeClient
from src.rag_pipeline import RAGPipeline
from src.case_analyzer import CaseAnalyzer
from src.ui_utils import render_sidebar

st.set_page_config(page_title="Case Analysis — NZ Law Assistant", page_icon="⚖️", layout="wide")

current_subject, project_id = render_sidebar()


def _init_resources():
    if "vector_store" not in st.session_state:
        st.session_state["vector_store"] = LegalVectorStore()
    if "claude_client" not in st.session_state:
        try:
            st.session_state["claude_client"] = ClaudeClient()
        except ValueError as e:
            st.error(str(e)); st.stop()
    if "rag_pipeline" not in st.session_state:
        st.session_state["rag_pipeline"] = RAGPipeline(
            st.session_state["vector_store"], st.session_state["claude_client"]
        )
    if "case_analyzer" not in st.session_state:
        st.session_state["case_analyzer"] = CaseAnalyzer(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
analyzer: CaseAnalyzer = st.session_state["case_analyzer"]

# ── Load saved conversation for this project ──────────────────────────────────
_PAGE = "case_analysis"
_saved: dict = sm.load_conversation(project_id, _PAGE) if project_id else {}

if "case_chat_history" not in st.session_state:
    st.session_state["case_chat_history"] = _saved.get("chat_history", [])
if "case_chat_case_id" not in st.session_state:
    st.session_state["case_chat_case_id"] = _saved.get("last_case_id", None)


def _save_state():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "chat_history": st.session_state.get("case_chat_history", []),
            "last_case_id": st.session_state.get("case_chat_case_id"),
        })


def _stream_to_ui(generator) -> str:
    output = st.empty()
    full_text = ""
    for chunk in generator:
        full_text += chunk
        output.markdown(full_text + "▌")
    output.markdown(full_text)
    return full_text


# ── UI ────────────────────────────────────────────────────────────────────────
if project_id:
    proj = sm.get_project(project_id)
    st.caption(f"Project: **{proj['subject']}**" if proj else "")

st.title("⚖️ Case Law Analysis")
st.markdown("Deep reading, IRAC analysis, ratio decidendi extraction, and case comparison.")

case_docs = [d for d in vs.list_documents() if d["doc_type"] == "case_law"]

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔍 Full Analysis", "📌 Extract Ratio", "🔄 Compare Cases", "💬 Chat About Case"]
)

# --- Tab 1: Full Analysis ---
with tab1:
    if not case_docs:
        st.warning("No case law documents uploaded. Go to **Documents** to upload cases.")
    else:
        selected = st.selectbox(
            "Select a case to analyse",
            options=case_docs,
            format_func=lambda d: d["title"],
            key="full_analysis_case",
        )
        if st.button("Analyse Case", type="primary", key="btn_full_analysis"):
            st.markdown("---")
            result = _stream_to_ui(
                analyzer.analyse_full_case(
                    doc_id=selected["doc_id"],
                    collection_name=selected["collection"],
                    current_subject=current_subject,
                )
            )
            if result:
                st.download_button(
                    "📥 Download Analysis",
                    data=result,
                    file_name=f"{selected['title']}_analysis.md",
                    mime="text/markdown",
                )

# --- Tab 2: Extract Ratio ---
with tab2:
    if not case_docs:
        st.warning("No case law documents uploaded.")
    else:
        selected_ratio = st.selectbox(
            "Select a case",
            options=case_docs,
            format_func=lambda d: d["title"],
            key="ratio_case",
        )
        if st.button("Extract Ratio Decidendi", type="primary", key="btn_ratio"):
            st.markdown("---")
            _stream_to_ui(
                analyzer.extract_ratio(
                    doc_id=selected_ratio["doc_id"],
                    collection_name=selected_ratio["collection"],
                    current_subject=current_subject,
                )
            )

# --- Tab 3: Compare Cases ---
with tab3:
    if len(case_docs) < 2:
        st.warning("Upload at least 2 cases to compare.")
    else:
        selected_cases = st.multiselect(
            "Select cases to compare (2–4)",
            options=case_docs,
            format_func=lambda d: d["title"],
            max_selections=4,
        )
        comparison_q = st.text_area(
            "What aspect do you want to compare?",
            placeholder="e.g. How do these cases treat the requirement of consideration?",
        )
        if st.button("Compare Cases", type="primary", key="btn_compare") and len(selected_cases) >= 2:
            st.markdown("---")
            _stream_to_ui(
                analyzer.compare_cases(
                    doc_ids=[d["doc_id"] for d in selected_cases],
                    collection_name=config.COLLECTIONS["case_law"],
                    comparison_question=comparison_q or "the key legal issues",
                    current_subject=current_subject,
                )
            )

# --- Tab 4: Chat About Case ---
with tab4:
    if not case_docs:
        st.warning("No case law documents uploaded.")
    else:
        chat_case = st.selectbox(
            "Select a case to discuss",
            options=case_docs,
            format_func=lambda d: d["title"],
            key="chat_case",
        )

        # Reset chat if case changed
        if chat_case and st.session_state.get("case_chat_case_id") != chat_case["doc_id"]:
            st.session_state["case_chat_history"] = []
            st.session_state["case_chat_case_id"] = chat_case["doc_id"]
            _save_state()

        for msg in st.session_state["case_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask about this case..."):
            st.session_state["case_chat_history"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                history_for_api = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["case_chat_history"][:-1]
                ]
                result = _stream_to_ui(
                    analyzer.chat_about_case(
                        user_message=prompt,
                        doc_id=chat_case["doc_id"],
                        collection_name=chat_case["collection"],
                        history=history_for_api,
                        current_subject=current_subject,
                    )
                )
            st.session_state["case_chat_history"].append({"role": "assistant", "content": result})
            _save_state()

        if st.session_state["case_chat_history"]:
            if st.button("Clear chat", key="clear_case_chat"):
                st.session_state["case_chat_history"] = []
                _save_state()
                st.rerun()
