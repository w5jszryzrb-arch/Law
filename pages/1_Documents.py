import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import config
from src.document_processor import process_uploaded_file
from src.vector_store import LegalVectorStore
from src.ui_utils import render_sidebar
from src.styles import page_header, tip, doc_badge

st.set_page_config(page_title="Documents — NZ Law Assistant", page_icon="📂", layout="wide")
current_subject, project_id = render_sidebar()

if "vector_store" not in st.session_state:
    with st.spinner("Loading document library..."):
        st.session_state["vector_store"] = LegalVectorStore()
vs: LegalVectorStore = st.session_state["vector_store"]

page_header("📂", "Document Library",
            "Upload your course materials — they are the source of truth for all analysis, essays, and exam practice.")

# ── Stats row ────────────────────────────────────────────────────────────────
all_docs = vs.list_documents()
counts = {}
for d in all_docs:
    counts[d["doc_type"]] = counts.get(d["doc_type"], 0) + 1

if all_docs:
    cols = st.columns(len(counts) if counts else 1)
    for i, (dtype, cnt) in enumerate(counts.items()):
        label = config.DOC_TYPE_LABELS.get(dtype, dtype)
        with cols[i]:
            st.metric(label, cnt)
    st.divider()

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown("### Upload New Documents")
tip("Upload PDFs, PowerPoints, or text files. The system will auto-detect the document type, but you can override it.")

uploaded_files = st.file_uploader(
    "Drop files here or click to browse",
    type=["pdf", "pptx", "ppt", "txt"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

doc_type_display = {v: k for k, v in config.DOC_TYPE_LABELS.items()}

if uploaded_files:
    with st.form("upload_form"):
        st.markdown("**Configure each document:**")
        titles: dict[str, str] = {}
        types: dict[str, str] = {}

        for uf in uploaded_files:
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                titles[uf.name] = st.text_input(
                    "Title", value=uf.name.rsplit(".", 1)[0],
                    key=f"title_{uf.name}", label_visibility="collapsed",
                    placeholder="Document title",
                )
            with c2:
                chosen_label = st.selectbox(
                    "Type", options=list(config.DOC_TYPE_LABELS.values()),
                    key=f"type_{uf.name}", label_visibility="collapsed",
                )
                types[uf.name] = doc_type_display[chosen_label]
            with c3:
                st.markdown(
                    f"<p style='padding-top:.4rem; font-size:.78rem; color:#64748B;'>{uf.name}</p>",
                    unsafe_allow_html=True,
                )

        submitted = st.form_submit_button("⬆️ Process & Upload", type="primary", use_container_width=True)

    if submitted:
        for uf in uploaded_files:
            with st.status(f"Processing **{titles[uf.name]}**...", expanded=True) as status:
                try:
                    st.write("Extracting text...")
                    doc = process_uploaded_file(
                        file_bytes=uf.read(),
                        original_filename=uf.name,
                        title=titles[uf.name],
                        doc_type=types[uf.name],
                    )
                    st.write(f"✓ Extracted {len(doc.full_text):,} characters across {len(doc.chunks)} chunks")
                    st.write("Embedding and indexing...")
                    collection_name = config.COLLECTIONS.get(types[uf.name], config.COLLECTIONS["other"])
                    vs.add_chunks(doc.chunks, collection_name)
                    status.update(label=f"✅ **{titles[uf.name]}** ready", state="complete")
                except Exception as e:
                    status.update(label=f"❌ Failed: {e}", state="error")
        st.rerun()

st.divider()

# ── Library ───────────────────────────────────────────────────────────────────
st.markdown("### Your Library")

if not all_docs:
    st.markdown(
        """<div style="background:white; border:2px dashed #DDE3EE; border-radius:12px;
                      padding:3rem; text-align:center; margin-top:.5rem;">
            <p style="font-size:2.5rem; margin:0;">📭</p>
            <p style="color:#64748B; margin:.75rem 0 .25rem; font-weight:500;">No documents yet</p>
            <p style="color:#94A3B8; font-size:.85rem; margin:0;">
                Upload lecture slides, case PDFs, articles, past papers, and workshop questions above.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )
else:
    # Filter bar
    type_filter = st.selectbox(
        "Filter by type",
        options=["All"] + list(config.DOC_TYPE_LABELS.values()),
        label_visibility="collapsed",
    )
    filtered = all_docs if type_filter == "All" else [
        d for d in all_docs if config.DOC_TYPE_LABELS.get(d["doc_type"], "") == type_filter
    ]

    # Table-style list
    for doc in filtered:
        badge_html = doc_badge(doc["doc_type"])
        with st.container(border=True):
            col_info, col_del = st.columns([9, 1])
            with col_info:
                st.markdown(
                    f"**{doc['title']}** &nbsp;&nbsp; {badge_html}"
                    f"<br><span style='color:#94A3B8; font-size:.78rem;'>{doc['source_filename']}</span>",
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑", key=f"del_{doc['doc_id']}", help="Delete document"):
                    vs.delete_document(doc["doc_id"], doc["collection"])
                    st.success(f"Deleted '{doc['title']}'")
                    st.rerun()
