import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import config
from src.vector_store import LegalVectorStore
from src.claude_client import ClaudeClient
from src.rag_pipeline import RAGPipeline
from src.notes_generator import NotesGenerator

st.set_page_config(page_title="Notes — NZ Law Assistant", page_icon="📓", layout="wide")

with st.sidebar:
    st.markdown("## ⚖️ NZ Law Assistant")
    st.divider()
    current_subject = st.text_input(
        "Current subject / topic",
        value=st.session_state.get("current_subject", ""),
        placeholder="e.g. Contract Law — Offer and Acceptance",
    )
    st.session_state["current_subject"] = current_subject

st.title("📓 Notes Generator")
st.markdown("Generate structured legal notes from your uploaded course materials.")


def _init_resources():
    if "vector_store" not in st.session_state:
        st.session_state["vector_store"] = LegalVectorStore()
    if "claude_client" not in st.session_state:
        try:
            st.session_state["claude_client"] = ClaudeClient()
        except ValueError as e:
            st.error(str(e))
            st.stop()
    if "rag_pipeline" not in st.session_state:
        st.session_state["rag_pipeline"] = RAGPipeline(
            st.session_state["vector_store"], st.session_state["claude_client"]
        )
    if "notes_generator" not in st.session_state:
        st.session_state["notes_generator"] = NotesGenerator(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
notes_gen: NotesGenerator = st.session_state["notes_generator"]


def _stream_to_ui(generator) -> str:
    output = st.empty()
    full_text = ""
    for chunk in generator:
        full_text += chunk
        output.markdown(full_text + "▌")
    output.markdown(full_text)
    return full_text


all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}
case_docs = [d for d in all_docs if d["doc_type"] == "case_law"]

if not all_docs:
    st.warning("No documents uploaded. Go to **Documents** to upload your course materials.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(
    ["📚 Lecture Notes", "📊 Case Table", "🗺️ Topic Overview", "⚡ Revision Notes"]
)

# --- Tab 1: Lecture Notes ---
with tab1:
    topic_ln = st.text_input(
        "Topic",
        placeholder="e.g. Promissory Estoppel, Vicarious Liability, Mens Rea",
        key="topic_ln",
    )
    selected_docs_ln = st.multiselect(
        "Source documents (optional — leave empty to search all)",
        options=list(doc_options.keys()),
        key="docs_ln",
    )
    doc_ids_ln = [doc_options[t]["doc_id"] for t in selected_docs_ln] if selected_docs_ln else None

    if st.button("Generate Lecture Notes", type="primary", key="btn_ln") and topic_ln.strip():
        st.markdown("---")
        result = _stream_to_ui(
            notes_gen.lecture_notes(
                topic=topic_ln,
                doc_ids=doc_ids_ln,
                current_subject=current_subject,
            )
        )
        if result:
            st.download_button(
                "📥 Download Notes",
                data=result,
                file_name=f"{topic_ln.replace(' ', '_')}_notes.md",
                mime="text/markdown",
            )

# --- Tab 2: Case Table ---
with tab2:
    if not case_docs:
        st.warning("No case law documents uploaded.")
    else:
        selected_cases_ct = st.multiselect(
            "Select cases for the table (leave empty for all cases)",
            options=case_docs,
            format_func=lambda d: d["title"],
            key="cases_ct",
        )
        doc_ids_ct = [d["doc_id"] for d in selected_cases_ct] if selected_cases_ct else [d["doc_id"] for d in case_docs]

        if st.button("Generate Case Table", type="primary", key="btn_ct"):
            st.markdown("---")
            result = _stream_to_ui(
                notes_gen.case_summary_table(
                    doc_ids=doc_ids_ct,
                    current_subject=current_subject,
                )
            )
            if result:
                st.download_button(
                    "📥 Download Table",
                    data=result,
                    file_name="case_summary_table.md",
                    mime="text/markdown",
                )

# --- Tab 3: Topic Overview ---
with tab3:
    topic_to = st.text_input(
        "Topic",
        placeholder="e.g. Negligence, Contract Formation, Criminal Defences",
        key="topic_to",
    )
    selected_docs_to = st.multiselect(
        "Source documents (optional)",
        options=list(doc_options.keys()),
        key="docs_to",
    )
    doc_ids_to = [doc_options[t]["doc_id"] for t in selected_docs_to] if selected_docs_to else None

    if st.button("Generate Topic Overview", type="primary", key="btn_to") and topic_to.strip():
        st.markdown("---")
        result = _stream_to_ui(
            notes_gen.topic_overview(
                topic=topic_to,
                doc_ids=doc_ids_to,
                current_subject=current_subject,
            )
        )
        if result:
            st.download_button(
                "📥 Download Overview",
                data=result,
                file_name=f"{topic_to.replace(' ', '_')}_overview.md",
                mime="text/markdown",
            )

# --- Tab 4: Revision Notes ---
with tab4:
    topic_rn = st.text_input(
        "Topic",
        placeholder="e.g. Consideration, Duty of Care, Actus Reus",
        key="topic_rn",
    )
    selected_docs_rn = st.multiselect(
        "Source documents (optional)",
        options=list(doc_options.keys()),
        key="docs_rn",
    )
    doc_ids_rn = [doc_options[t]["doc_id"] for t in selected_docs_rn] if selected_docs_rn else None

    if st.button("Generate Revision Notes", type="primary", key="btn_rn") and topic_rn.strip():
        st.markdown("---")
        result = _stream_to_ui(
            notes_gen.revision_notes(
                topic=topic_rn,
                doc_ids=doc_ids_rn,
                current_subject=current_subject,
            )
        )
        if result:
            st.download_button(
                "📥 Download Revision Notes",
                data=result,
                file_name=f"{topic_rn.replace(' ', '_')}_revision.md",
                mime="text/markdown",
            )
