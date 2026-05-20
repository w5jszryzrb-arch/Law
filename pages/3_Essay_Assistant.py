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
from src.essay_assistant import EssayAssistant
from src.ui_utils import render_sidebar

st.set_page_config(page_title="Essay Assistant — NZ Law Assistant", page_icon="✍️", layout="wide")

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
    if "essay_assistant" not in st.session_state:
        st.session_state["essay_assistant"] = EssayAssistant(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
assistant: EssayAssistant = st.session_state["essay_assistant"]

# ── Load saved state for this project ────────────────────────────────────────
_PAGE = "essay"
_saved: dict = sm.load_conversation(project_id, _PAGE) if project_id else {}

if "essay_chat_history" not in st.session_state:
    st.session_state["essay_chat_history"] = _saved.get("chat_history", [])
if "essay_question_input" not in st.session_state:
    st.session_state["essay_question_input"] = _saved.get("essay_question", "")
if "essay_plan" not in st.session_state:
    st.session_state["essay_plan"] = _saved.get("essay_plan", "")
if "essay_draft" not in st.session_state:
    st.session_state["essay_draft"] = _saved.get("essay_draft", "")


def _save_state():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "chat_history": st.session_state.get("essay_chat_history", []),
            "essay_question": st.session_state.get("essay_question_input", ""),
            "essay_plan": st.session_state.get("essay_plan", ""),
            "essay_draft": st.session_state.get("essay_draft", ""),
        })


def _stream_to_ui(generator, placeholder=None) -> str:
    container = placeholder or st.empty()
    full_text = ""
    for chunk in generator:
        full_text += chunk
        container.markdown(full_text + "▌")
    container.markdown(full_text)
    return full_text


# ── Rubric panel ─────────────────────────────────────────────────────────────
if project_id:
    proj = sm.get_project(project_id)
    st.caption(f"Project: **{proj['subject']}**" if proj else "")

    with st.expander("📋 Assessment Rubric (optional)", expanded=bool(_saved.get("rubric") or (proj and proj.get("rubric")))):
        current_rubric = proj.get("rubric", "") if proj else ""
        rubric_input = st.text_area(
            "Paste your rubric or marking criteria here",
            value=current_rubric,
            height=180,
            placeholder=(
                "e.g.\n"
                "A+ (90–100%): Exceptional identification of all issues, precise use of authority...\n"
                "A  (80–89%):  Strong IRAC analysis, accurate citations, well-structured argument...\n"
            ),
            key="rubric_text_area",
        )
        if st.button("Save Rubric", key="save_rubric"):
            sm.update_project(project_id, rubric=rubric_input)
            st.success("Rubric saved to this project.")
            st.rerun()
        rubric = rubric_input
else:
    rubric = ""

st.title("✍️ Essay Assistant")
st.markdown(
    "All essays follow the **New Zealand Law Style Guide (3rd ed, 2018)**. "
    "Formal academic prose, IRAC structure, NZ citations."
)
if rubric:
    st.info("📋 Assessment rubric is active — all drafts and critiques will align with your rubric.", icon="📋")

# ── Doc list ──────────────────────────────────────────────────────────────────
all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}

question_key = "essay_question_input"

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📋 Analyse Question", "📐 Essay Plan", "📄 Full Draft", "🔍 Critique", "💬 Chat"]
)

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
            assistant.analyse_question(
                question, doc_ids=doc_ids, current_subject=current_subject, rubric=rubric
            )
        )
        st.session_state["essay_analysis"] = result
        _save_state()

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
        "Documents to use", options=list(doc_options.keys()), key="docs_plan"
    )
    doc_ids2 = [doc_options[t]["doc_id"] for t in selected_titles2] if selected_titles2 else None

    if st.button("Generate Essay Plan", type="primary", key="btn_plan") and question2.strip():
        st.markdown("---")
        result = _stream_to_ui(
            assistant.generate_plan(
                question2, word_limit=word_limit, doc_ids=doc_ids2,
                current_subject=current_subject, rubric=rubric,
            )
        )
        st.session_state["essay_plan"] = result
        _save_state()

    if st.session_state.get("essay_plan"):
        with st.expander("Current plan"):
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
        "Essay Plan",
        value=st.session_state.get("essay_plan", ""),
        height=200,
        placeholder="Paste your essay plan here, or generate one in the Plan tab first.",
        key="plan_input",
    )
    word_limit3 = st.select_slider(
        "Target word count", options=[500, 750, 1000, 1500, 2000, 2500, 3000], value=1500, key="wl_draft"
    )
    selected_titles3 = st.multiselect(
        "Documents to use", options=list(doc_options.keys()), key="docs_draft"
    )
    doc_ids3 = [doc_options[t]["doc_id"] for t in selected_titles3] if selected_titles3 else None

    if st.button("Draft Essay", type="primary", key="btn_draft") and question3.strip():
        st.markdown("---")
        result = _stream_to_ui(
            assistant.draft_essay(
                question=question3, plan=plan_text, word_limit=word_limit3,
                doc_ids=doc_ids3, current_subject=current_subject, rubric=rubric,
            )
        )
        st.session_state["essay_draft"] = result
        _save_state()
        st.download_button(
            "📥 Download Draft", data=result,
            file_name="essay_draft.md", mime="text/markdown",
        )

# --- Tab 4: Critique ---
with tab4:
    question4 = st.text_area(
        "Essay Question", value=st.session_state[question_key], height=100, key="q_critique"
    )
    essay_input = st.text_area(
        "Your Essay", value=st.session_state.get("essay_draft", ""), height=300,
        placeholder="Paste your essay here...", key="essay_critique_input",
    )
    if st.button("Get Critique", type="primary", key="btn_critique") and question4.strip() and essay_input.strip():
        st.markdown("---")
        _stream_to_ui(
            assistant.critique_essay(
                question=question4, essay_text=essay_input,
                current_subject=current_subject, rubric=rubric,
            )
        )

# --- Tab 5: Chat ---
with tab5:
    st.markdown("Ask anything about your essay, arguments, or legal issues.")

    selected_titles5 = st.multiselect(
        "Documents to use as context", options=list(doc_options.keys()), key="docs_chat"
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
                    message=prompt, history=history_for_api,
                    doc_ids=doc_ids5, current_subject=current_subject, rubric=rubric,
                )
            )
        st.session_state["essay_chat_history"].append({"role": "assistant", "content": result})
        _save_state()

    if st.session_state["essay_chat_history"]:
        if st.button("Clear chat", key="clear_essay_chat"):
            st.session_state["essay_chat_history"] = []
            _save_state()
            st.rerun()
