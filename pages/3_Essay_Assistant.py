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
from src.essay_assistant import EssayAssistant

st.set_page_config(page_title="Essay Assistant — NZ Law Assistant", page_icon="✍️", layout="wide")

with st.sidebar:
    st.markdown("## ⚖️ NZ Law Assistant")
    st.divider()
    current_subject = st.text_input(
        "Current subject / topic",
        value=st.session_state.get("current_subject", ""),
        placeholder="e.g. Contract Law — Offer and Acceptance",
    )
    st.session_state["current_subject"] = current_subject

st.title("✍️ Essay Assistant")
st.markdown(
    "All essays follow the **New Zealand Law Style Guide (3rd ed, 2018)**. "
    "Formal academic prose, IRAC structure, NZ citations."
)


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
    if "essay_assistant" not in st.session_state:
        st.session_state["essay_assistant"] = EssayAssistant(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
assistant: EssayAssistant = st.session_state["essay_assistant"]


def _stream_to_ui(generator, placeholder=None) -> str:
    container = placeholder or st.empty()
    full_text = ""
    for chunk in generator:
        full_text += chunk
        container.markdown(full_text + "▌")
    container.markdown(full_text)
    return full_text


all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📋 Analyse Question", "📐 Essay Plan", "📄 Full Draft", "🔍 Critique", "💬 Chat"]
)

# Shared question input
question_key = "essay_question_input"
if question_key not in st.session_state:
    st.session_state[question_key] = ""

# --- Tab 1: Analyse Question ---
with tab1:
    question = st.text_area(
        "Essay / Problem Question",
        value=st.session_state[question_key],
        height=150,
        placeholder="Paste your essay question or problem scenario here...",
        key="q_analyse",
    )
    st.session_state[question_key] = question

    selected_titles = st.multiselect(
        "Documents to use as context (optional — leave empty to search all)",
        options=list(doc_options.keys()),
        key="docs_analyse",
    )
    doc_ids = [doc_options[t]["doc_id"] for t in selected_titles] if selected_titles else None

    if st.button("Analyse Question", type="primary", key="btn_analyse") and question.strip():
        st.markdown("---")
        result = _stream_to_ui(
            assistant.analyse_question(question, doc_ids=doc_ids, current_subject=current_subject)
        )
        st.session_state["essay_analysis"] = result

# --- Tab 2: Essay Plan ---
with tab2:
    question2 = st.text_area(
        "Essay / Problem Question",
        value=st.session_state[question_key],
        height=120,
        key="q_plan",
    )
    st.session_state[question_key] = question2

    word_limit = st.select_slider(
        "Word limit", options=[500, 750, 1000, 1500, 2000, 2500, 3000], value=1500
    )
    selected_titles2 = st.multiselect(
        "Documents to use",
        options=list(doc_options.keys()),
        key="docs_plan",
    )
    doc_ids2 = [doc_options[t]["doc_id"] for t in selected_titles2] if selected_titles2 else None

    if st.button("Generate Essay Plan", type="primary", key="btn_plan") and question2.strip():
        st.markdown("---")
        result = _stream_to_ui(
            assistant.generate_plan(question2, word_limit=word_limit, doc_ids=doc_ids2, current_subject=current_subject)
        )
        st.session_state["essay_plan"] = result

    if "essay_plan" in st.session_state and st.session_state["essay_plan"]:
        with st.expander("Current plan (click to view/copy)"):
            st.markdown(st.session_state["essay_plan"])

# --- Tab 3: Full Draft ---
with tab3:
    question3 = st.text_area(
        "Essay / Problem Question",
        value=st.session_state[question_key],
        height=120,
        key="q_draft",
    )
    st.session_state[question_key] = question3

    plan_text = st.text_area(
        "Essay Plan (paste or auto-filled from Plan tab)",
        value=st.session_state.get("essay_plan", ""),
        height=200,
        placeholder="Paste your essay plan here, or generate one in the Plan tab first.",
        key="plan_input",
    )
    word_limit3 = st.select_slider(
        "Target word count", options=[500, 750, 1000, 1500, 2000, 2500, 3000], value=1500, key="wl_draft"
    )
    selected_titles3 = st.multiselect(
        "Documents to use",
        options=list(doc_options.keys()),
        key="docs_draft",
    )
    doc_ids3 = [doc_options[t]["doc_id"] for t in selected_titles3] if selected_titles3 else None

    if st.button("Draft Essay", type="primary", key="btn_draft") and question3.strip():
        st.markdown("---")
        result = _stream_to_ui(
            assistant.draft_essay(
                question=question3,
                plan=plan_text,
                word_limit=word_limit3,
                doc_ids=doc_ids3,
                current_subject=current_subject,
            )
        )
        st.session_state["essay_draft"] = result
        st.download_button(
            "📥 Download Draft",
            data=result,
            file_name="essay_draft.md",
            mime="text/markdown",
        )

# --- Tab 4: Critique ---
with tab4:
    question4 = st.text_area(
        "Essay Question",
        value=st.session_state[question_key],
        height=100,
        key="q_critique",
    )
    essay_input = st.text_area(
        "Your Essay",
        value=st.session_state.get("essay_draft", ""),
        height=300,
        placeholder="Paste your essay here...",
        key="essay_critique_input",
    )
    if st.button("Get Critique", type="primary", key="btn_critique") and question4.strip() and essay_input.strip():
        st.markdown("---")
        _stream_to_ui(
            assistant.critique_essay(
                question=question4, essay_text=essay_input, current_subject=current_subject
            )
        )

# --- Tab 5: Chat ---
with tab5:
    st.markdown("Ask anything about your essay, get help with specific arguments, or discuss legal issues.")

    if "essay_chat_history" not in st.session_state:
        st.session_state["essay_chat_history"] = []

    selected_titles5 = st.multiselect(
        "Documents to use as context",
        options=list(doc_options.keys()),
        key="docs_chat",
    )
    doc_ids5 = [doc_options[t]["doc_id"] for t in selected_titles5] if selected_titles5 else None

    for msg in st.session_state["essay_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your essay or legal issues..."):
        st.session_state["essay_chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            history_for_api = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state["essay_chat_history"][:-1]
            ]
            result = _stream_to_ui(
                assistant.chat(
                    message=prompt,
                    history=history_for_api,
                    doc_ids=doc_ids5,
                    current_subject=current_subject,
                )
            )
        st.session_state["essay_chat_history"].append({"role": "assistant", "content": result})

    if st.session_state["essay_chat_history"]:
        if st.button("Clear chat", key="clear_essay_chat"):
            st.session_state["essay_chat_history"] = []
            st.rerun()
