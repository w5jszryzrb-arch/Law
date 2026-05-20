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
from src.styles import page_header, tip

st.set_page_config(page_title="Case Analysis — NZ Law Assistant", page_icon="⚖️", layout="wide")
current_subject, project_id = render_sidebar()


def _init():
    if "vector_store" not in st.session_state:
        st.session_state["vector_store"] = LegalVectorStore()
    if "claude_client" not in st.session_state:
        try:
            st.session_state["claude_client"] = ClaudeClient()
        except ValueError as e:
            st.error(str(e)); st.stop()
    if "rag_pipeline" not in st.session_state:
        st.session_state["rag_pipeline"] = RAGPipeline(
            st.session_state["vector_store"], st.session_state["claude_client"])
    if "case_analyzer" not in st.session_state:
        st.session_state["case_analyzer"] = CaseAnalyzer(st.session_state["rag_pipeline"])

_init()
vs: LegalVectorStore = st.session_state["vector_store"]
analyzer: CaseAnalyzer = st.session_state["case_analyzer"]

# ── Restore project state ─────────────────────────────────────────────────────
_PAGE = "case_analysis"
_saved: dict = sm.load_conversation(project_id, _PAGE) if project_id else {}
if "case_chat_history" not in st.session_state:
    st.session_state["case_chat_history"] = _saved.get("chat_history", [])
if "case_chat_case_id" not in st.session_state:
    st.session_state["case_chat_case_id"] = _saved.get("last_case_id")

def _save():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "chat_history": st.session_state.get("case_chat_history", []),
            "last_case_id": st.session_state.get("case_chat_case_id"),
        })

def _stream(gen) -> str:
    out = st.empty()
    text = ""
    for chunk in gen:
        text += chunk
        out.markdown(
            f'<div class="output-box">{text}▌</div>', unsafe_allow_html=True
        )
    out.markdown(f'<div class="output-box">{text}</div>', unsafe_allow_html=True)
    return text

# ── Page header ───────────────────────────────────────────────────────────────
page_header("⚖️", "Case Law Analysis",
            "IRAC analysis · ratio decidendi · obiter dicta · case comparison")

case_docs = [d for d in vs.list_documents() if d["doc_type"] == "case_law"]

if not case_docs:
    st.markdown(
        """<div style="background:white; border:2px dashed #DDE3EE; border-radius:12px;
                      padding:3rem; text-align:center; margin:1rem 0;">
            <p style="font-size:2.5rem; margin:0;">📂</p>
            <p style="color:#64748B; margin:.75rem 0 .25rem; font-weight:500;">No case law uploaded yet</p>
            <p style="color:#94A3B8; font-size:.85rem; margin:0;">
                Go to <strong>Documents</strong> and upload case PDFs to get started.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Full IRAC Analysis", "📌 Extract Ratio", "🔄 Compare Cases", "💬 Chat About Case"
])

# ── Tab 1: Full Analysis ───────────────────────────────────────────────────────
with tab1:
    tip("Select a case and click Analyse — you'll get a full IRAC breakdown, ratio, obiter, and critical commentary.")
    selected = st.selectbox(
        "Select a case", options=case_docs,
        format_func=lambda d: d["title"], key="full_analysis_case",
    )
    if st.button("Analyse Case", type="primary", key="btn_full"):
        with st.spinner("Reading case..."):
            st.markdown("---")
        result = _stream(
            analyzer.analyse_full_case(
                doc_id=selected["doc_id"],
                collection_name=selected["collection"],
                current_subject=current_subject,
            )
        )
        if result:
            st.download_button("📥 Download Analysis", data=result,
                               file_name=f"{selected['title']}_analysis.md", mime="text/markdown")

# ── Tab 2: Extract Ratio ───────────────────────────────────────────────────────
with tab2:
    tip("Extracts the binding legal principle (ratio decidendi) and distinguishes it from obiter dicta.")
    selected_r = st.selectbox(
        "Select a case", options=case_docs,
        format_func=lambda d: d["title"], key="ratio_case",
    )
    if st.button("Extract Ratio Decidendi", type="primary", key="btn_ratio"):
        with st.spinner("Identifying ratio..."):
            st.markdown("---")
        _stream(
            analyzer.extract_ratio(
                doc_id=selected_r["doc_id"],
                collection_name=selected_r["collection"],
                current_subject=current_subject,
            )
        )

# ── Tab 3: Compare Cases ───────────────────────────────────────────────────────
with tab3:
    if len(case_docs) < 2:
        st.info("Upload at least 2 cases to use comparison mode.", icon="ℹ️")
    else:
        tip("Compare how 2–4 cases treat the same legal issue. Great for spotting tensions and developments in the law.")
        selected_cases = st.multiselect(
            "Select cases to compare (2–4)",
            options=case_docs, format_func=lambda d: d["title"], max_selections=4,
        )
        comparison_q = st.text_area(
            "What do you want to compare?",
            placeholder="e.g. How do these cases treat the duty of care in negligence?",
            height=80,
        )
        if st.button("Compare Cases", type="primary", key="btn_compare") and len(selected_cases) >= 2:
            with st.spinner("Comparing cases..."):
                st.markdown("---")
            _stream(
                analyzer.compare_cases(
                    doc_ids=[d["doc_id"] for d in selected_cases],
                    collection_name=config.COLLECTIONS["case_law"],
                    comparison_question=comparison_q or "the key legal issues",
                    current_subject=current_subject,
                )
            )

# ── Tab 4: Chat ────────────────────────────────────────────────────────────────
with tab4:
    tip("Ask anything about a specific case — facts, reasoning, significance, how it relates to other cases.")

    chat_case = st.selectbox(
        "Case to discuss", options=case_docs,
        format_func=lambda d: d["title"], key="chat_case",
    )

    if chat_case and st.session_state.get("case_chat_case_id") != chat_case["doc_id"]:
        st.session_state["case_chat_history"] = []
        st.session_state["case_chat_case_id"] = chat_case["doc_id"]
        _save()

    if not st.session_state["case_chat_history"]:
        st.markdown(
            "<p style='color:#94A3B8; font-size:.85rem; text-align:center; padding:1rem 0;'>"
            "Ask a question below to start the conversation.</p>",
            unsafe_allow_html=True,
        )

    for msg in st.session_state["case_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Ask about {chat_case['title']}..."):
        st.session_state["case_chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            history_api = [{"role": m["role"], "content": m["content"]}
                           for m in st.session_state["case_chat_history"][:-1]]
            result = _stream(
                analyzer.chat_about_case(
                    user_message=prompt,
                    doc_id=chat_case["doc_id"],
                    collection_name=chat_case["collection"],
                    history=history_api,
                    current_subject=current_subject,
                )
            )
        st.session_state["case_chat_history"].append({"role": "assistant", "content": result})
        _save()

    if st.session_state["case_chat_history"]:
        if st.button("Clear conversation", key="clear_case_chat"):
            st.session_state["case_chat_history"] = []
            _save()
            st.rerun()
