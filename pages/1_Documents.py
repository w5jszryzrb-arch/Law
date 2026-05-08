import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import config
from src.document_processor import process_uploaded_file
from src.vector_store import LegalVectorStore

st.set_page_config(page_title="Documents — NZ Law Assistant", page_icon="📂", layout="wide")

with st.sidebar:
    st.markdown("## ⚖️ NZ Law Assistant")
    st.divider()
    current_subject = st.text_input(
        "Current subject / topic",
        value=st.session_state.get("current_subject", ""),
        placeholder="e.g. Contract Law — Offer and Acceptance",
    )
    st.session_state["current_subject"] = current_subject

st.title("📂 Document Library")
st.markdown("Upload your course materials. All files are stored locally and used as sources for analysis.")

# Initialise vector store
if "vector_store" not in st.session_state:
    with st.spinner("Loading document library..."):
        st.session_state["vector_store"] = LegalVectorStore()
vs: LegalVectorStore = st.session_state["vector_store"]

# Upload section
st.subheader("Upload Documents")

uploaded_files = st.file_uploader(
    "Choose files",
    type=["pdf", "pptx", "ppt", "txt"],
    accept_multiple_files=True,
    help="Accepted: PDF, PPTX, TXT",
)

doc_type_options = list(config.DOC_TYPE_LABELS.items())
doc_type_display = {v: k for k, v in config.DOC_TYPE_LABELS.items()}

if uploaded_files:
    with st.form("upload_form"):
        titles: dict[str, str] = {}
        types: dict[str, str] = {}

        for uf in uploaded_files:
            st.markdown(f"**{uf.name}**")
            c1, c2 = st.columns([2, 1])
            with c1:
                titles[uf.name] = st.text_input(
                    "Title", value=uf.name.rsplit(".", 1)[0], key=f"title_{uf.name}"
                )
            with c2:
                chosen_label = st.selectbox(
                    "Type",
                    options=list(config.DOC_TYPE_LABELS.values()),
                    key=f"type_{uf.name}",
                )
                types[uf.name] = doc_type_display[chosen_label]

        submitted = st.form_submit_button("Process & Upload", type="primary")

    if submitted:
        for uf in uploaded_files:
            title = titles[uf.name]
            doc_type = types[uf.name]
            with st.status(f"Processing {uf.name}...", expanded=True) as status:
                try:
                    st.write("Extracting text...")
                    doc = process_uploaded_file(
                        file_bytes=uf.read(),
                        original_filename=uf.name,
                        title=title,
                        doc_type=doc_type,
                    )
                    st.write(f"Extracted {len(doc.full_text):,} characters, {len(doc.chunks)} chunks.")
                    st.write("Embedding and storing...")
                    collection_name = config.COLLECTIONS.get(doc_type, config.COLLECTIONS["other"])
                    vs.add_chunks(doc.chunks, collection_name)
                    status.update(label=f"✅ {title} uploaded successfully", state="complete")
                except Exception as e:
                    status.update(label=f"❌ Failed: {e}", state="error")

        st.rerun()

st.divider()

# Library view
st.subheader("Your Library")

all_docs = vs.list_documents()

if not all_docs:
    st.info("No documents uploaded yet.")
else:
    # Filter by type
    type_filter = st.selectbox(
        "Filter by type",
        options=["All"] + list(config.DOC_TYPE_LABELS.values()),
        index=0,
    )

    filtered = all_docs
    if type_filter != "All":
        key = doc_type_display.get(type_filter, "")
        filtered = [d for d in all_docs if d["doc_type"] == key]

    for doc in filtered:
        label = config.DOC_TYPE_LABELS.get(doc["doc_type"], doc["doc_type"])
        with st.expander(f"**{doc['title']}** — {label}"):
            st.markdown(f"- **File:** {doc['source_filename']}")
            st.markdown(f"- **Type:** {label}")
            st.markdown(f"- **Collection:** {doc['collection']}")
            if st.button("🗑️ Delete", key=f"del_{doc['doc_id']}"):
                vs.delete_document(doc["doc_id"], doc["collection"])
                st.success(f"Deleted '{doc['title']}'")
                st.rerun()
