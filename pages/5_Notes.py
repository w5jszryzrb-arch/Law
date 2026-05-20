import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import src.session_manager as sm
from src.vector_store import LegalVectorStore
from src.claude_client import ClaudeClient
from src.rag_pipeline import RAGPipeline
from src.notes_generator import NotesGenerator
from src.ui_utils import render_sidebar
from src.styles import page_header, tip

st.set_page_config(page_title="Notes — NZ Law Assistant", page_icon="📓", layout="wide")
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
    if "notes_generator" not in st.session_state:
        st.session_state["notes_generator"] = NotesGenerator(st.session_state["rag_pipeline"])

_init()
vs: LegalVectorStore = st.session_state["vector_store"]
notes_gen: NotesGenerator = st.session_state["notes_generator"]

all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}
case_docs = [d for d in all_docs if d["doc_type"] == "case_law"]

page_header("📓", "Notes Generator",
            "Generate structured legal notes from your uploaded course materials")

if not all_docs:
    st.markdown(
        """<div style="background:white; border:2px dashed #DDE3EE; border-radius:12px;
                      padding:3rem; text-align:center; margin:1rem 0;">
            <p style="font-size:2.5rem; margin:0;">📭</p>
            <p style="color:#64748B; margin:.75rem 0 .25rem; font-weight:500;">No documents uploaded yet</p>
            <p style="color:#94A3B8; font-size:.85rem; margin:0;">
                Go to <strong>Documents</strong> and upload your course materials first.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()


def _stream(gen) -> str:
    out = st.empty()
    text = ""
    for chunk in gen:
        text += chunk
        out.markdown(f'<div class="output-box">{text}▌</div>', unsafe_allow_html=True)
    out.markdown(f'<div class="output-box">{text}</div>', unsafe_allow_html=True)
    return text


tab1, tab2, tab3, tab4 = st.tabs([
    "📚 Lecture Notes", "📊 Case Table", "🗺️ Topic Overview", "⚡ Revision Notes",
])

# ── Lecture Notes ─────────────────────────────────────────────────────────────
with tab1:
    tip("Generates well-structured notes organised by sub-topic with cases cited inline — ideal for building your own notes from lectures.")
    topic_ln = st.text_input("Topic",
        placeholder="e.g.  Promissory Estoppel  |  Vicarious Liability  |  Mens Rea",
        key="topic_ln")
    sel_ln = st.multiselect("Source documents (optional — leave empty to search all)",
                             options=list(doc_options.keys()), key="docs_ln")
    doc_ids_ln = [doc_options[t]["doc_id"] for t in sel_ln] if sel_ln else None

    if st.button("Generate Lecture Notes", type="primary", key="btn_ln") and topic_ln.strip():
        st.markdown("---")
        result = _stream(notes_gen.lecture_notes(
            topic=topic_ln, doc_ids=doc_ids_ln, current_subject=current_subject))
        if result:
            st.download_button("📥 Download Notes", data=result,
                file_name=f"{topic_ln.replace(' ','_')}_notes.md", mime="text/markdown")

# ── Case Table ────────────────────────────────────────────────────────────────
with tab2:
    if not case_docs:
        st.info("Upload case law documents to generate a case summary table.", icon="ℹ️")
    else:
        tip("Produces a Markdown table: Case Name | Court & Year | Key Facts | Ratio | Significance — perfect for revision.")
        sel_ct = st.multiselect("Select cases (leave empty for all uploaded cases)",
                                options=case_docs, format_func=lambda d: d["title"], key="cases_ct")
        doc_ids_ct = ([d["doc_id"] for d in sel_ct] if sel_ct
                      else [d["doc_id"] for d in case_docs])

        if st.button("Generate Case Table", type="primary", key="btn_ct"):
            st.markdown("---")
            result = _stream(notes_gen.case_summary_table(
                doc_ids=doc_ids_ct, current_subject=current_subject))
            if result:
                st.download_button("📥 Download Table", data=result,
                    file_name="case_summary_table.md", mime="text/markdown")

# ── Topic Overview ────────────────────────────────────────────────────────────
with tab3:
    tip("Synthesises all uploaded materials into a comprehensive topic overview — principles, leading cases, statutes, academic commentary, and exam focus.")
    topic_to = st.text_input("Topic",
        placeholder="e.g.  Negligence  |  Contract Formation  |  Criminal Defences",
        key="topic_to")
    sel_to = st.multiselect("Source documents (optional)",
                             options=list(doc_options.keys()), key="docs_to")
    doc_ids_to = [doc_options[t]["doc_id"] for t in sel_to] if sel_to else None

    if st.button("Generate Topic Overview", type="primary", key="btn_to") and topic_to.strip():
        st.markdown("---")
        result = _stream(notes_gen.topic_overview(
            topic=topic_to, doc_ids=doc_ids_to, current_subject=current_subject))
        if result:
            st.download_button("📥 Download Overview", data=result,
                file_name=f"{topic_to.replace(' ','_')}_overview.md", mime="text/markdown")

# ── Revision Notes ────────────────────────────────────────────────────────────
with tab4:
    tip("Concise, exam-ready notes: key test, top 3–5 cases, statute sections, common traps, and an IRAC template for problem questions.")
    topic_rn = st.text_input("Topic",
        placeholder="e.g.  Consideration  |  Duty of Care  |  Actus Reus",
        key="topic_rn")
    sel_rn = st.multiselect("Source documents (optional)",
                             options=list(doc_options.keys()), key="docs_rn")
    doc_ids_rn = [doc_options[t]["doc_id"] for t in sel_rn] if sel_rn else None

    if st.button("Generate Revision Notes", type="primary", key="btn_rn") and topic_rn.strip():
        st.markdown("---")
        result = _stream(notes_gen.revision_notes(
            topic=topic_rn, doc_ids=doc_ids_rn, current_subject=current_subject))
        if result:
            st.download_button("📥 Download Revision Notes", data=result,
                file_name=f"{topic_rn.replace(' ','_')}_revision.md", mime="text/markdown")
