import os
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="NZ Law School Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar: subject input (shared across all pages)
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Scale_of_justice_2.svg/200px-Scale_of_justice_2.svg.png", width=60)
    st.markdown("## ⚖️ NZ Law Assistant")
    st.divider()
    current_subject = st.text_input(
        "Current subject / topic",
        value=st.session_state.get("current_subject", ""),
        placeholder="e.g. Contract Law — Offer and Acceptance",
        help="Type your current subject. All responses will be tailored to this area of NZ law.",
    )
    st.session_state["current_subject"] = current_subject

    st.divider()
    st.caption("Navigate using the pages above ↑")

# Check API key
api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or not api_key.startswith("sk-"):
    st.error(
        "**ANTHROPIC_API_KEY not set.**\n\n"
        "Create a `.env` file in the project root:\n```\nANTHROPIC_API_KEY=sk-ant-...\n```",
        icon="🔑",
    )

# Home page content
st.title("⚖️ New Zealand Law School Assistant")
st.markdown(
    "Your AI-powered study companion for **New Zealand law**. "
    "All analysis follows the **NZ Law Style Guide (3rd ed, 2018)** and the NZ court hierarchy."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📂 Documents")
    st.markdown(
        "Upload case law, lecture slides, transcripts, legal scholarship, "
        "past exam papers, and assignment instructions."
    )

with col2:
    st.markdown("### ⚖️ Case Analysis")
    st.markdown(
        "Deep IRAC analysis of any uploaded case — ratio decidendi, obiter dicta, "
        "precedent value, and critical commentary."
    )

with col3:
    st.markdown("### ✍️ Essay Assistant")
    st.markdown(
        "Analyse essay questions, generate structured plans, draft full essays "
        "in formal NZ academic style, and get critique."
    )

col4, col5, _ = st.columns(3)

with col4:
    st.markdown("### 📝 Exam Practice")
    st.markdown(
        "Generate practice questions based **only** on your uploaded course content. "
        "Get model answers and detailed feedback on your answers."
    )

with col5:
    st.markdown("### 📓 Notes")
    st.markdown(
        "Generate lecture notes, case summary tables, topic overviews, "
        "and revision notes from your uploaded materials."
    )

st.divider()

# Document status
try:
    from src.vector_store import LegalVectorStore
    import config

    if "vector_store" not in st.session_state:
        with st.spinner("Loading document library..."):
            st.session_state["vector_store"] = LegalVectorStore()

    vs: LegalVectorStore = st.session_state["vector_store"]
    docs = vs.list_documents()

    if docs:
        st.success(f"**{len(docs)} document(s)** in your library.")
        with st.expander("View library"):
            for d in docs:
                label = config.DOC_TYPE_LABELS.get(d["doc_type"], d["doc_type"])
                st.markdown(f"- **{d['title']}** — {label}")
    else:
        st.info("No documents uploaded yet. Go to **Documents** to get started.")

except Exception as e:
    st.warning(f"Could not load document library: {e}")
