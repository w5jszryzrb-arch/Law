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
from src.styles import page_header, tip

st.set_page_config(page_title="Essay Assistant — NZ Law Assistant", page_icon="✍️", layout="wide")
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
    if "essay_assistant" not in st.session_state:
        st.session_state["essay_assistant"] = EssayAssistant(st.session_state["rag_pipeline"])

_init()
vs: LegalVectorStore = st.session_state["vector_store"]
assistant: EssayAssistant = st.session_state["essay_assistant"]

# ── Restore project state ─────────────────────────────────────────────────────
_PAGE = "essay"
_saved: dict = sm.load_conversation(project_id, _PAGE) if project_id else {}
if "essay_chat_history"   not in st.session_state:
    st.session_state["essay_chat_history"]   = _saved.get("chat_history", [])
if "essay_question_input" not in st.session_state:
    st.session_state["essay_question_input"] = _saved.get("essay_question", "")
if "essay_plan"           not in st.session_state:
    st.session_state["essay_plan"]           = _saved.get("essay_plan", "")
if "essay_draft"          not in st.session_state:
    st.session_state["essay_draft"]          = _saved.get("essay_draft", "")

def _save():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "chat_history":   st.session_state.get("essay_chat_history", []),
            "essay_question": st.session_state.get("essay_question_input", ""),
            "essay_plan":     st.session_state.get("essay_plan", ""),
            "essay_draft":    st.session_state.get("essay_draft", ""),
        })

def _stream(gen) -> str:
    out = st.empty()
    text = ""
    for chunk in gen:
        text += chunk
        out.markdown(f'<div class="output-box">{text}▌</div>', unsafe_allow_html=True)
    out.markdown(f'<div class="output-box">{text}</div>', unsafe_allow_html=True)
    return text

# ── Rubric ────────────────────────────────────────────────────────────────────
proj = sm.get_project(project_id) if project_id else None
rubric = ""
if project_id and proj:
    rubric = proj.get("rubric", "") or ""
    with st.expander(
        ("📋 Assessment Rubric  ✓ Active" if rubric else "📋 Assessment Rubric  (optional)"),
        expanded=False,
    ):
        if rubric:
            st.success("A rubric is saved for this project. All drafts and critiques align with it.", icon="📋")
        new_rubric = st.text_area(
            "Paste your marking criteria or rubric",
            value=rubric, height=160,
            placeholder=(
                "e.g.\n"
                "A+ (90–100%): Exceptional issue identification, all relevant authority cited, flawless IRAC...\n"
                "A  (80–89%):  Strong analysis, accurate citations, well-structured argument...\n"
                "B+ (75–79%):  Good analysis with minor gaps in authority or structure...\n"
            ),
            key="rubric_input",
        )
        if st.button("Save Rubric to Project", type="primary", key="save_rubric"):
            sm.update_project(project_id, rubric=new_rubric)
            st.success("Rubric saved.")
            st.rerun()
        rubric = new_rubric

# ── Page header ───────────────────────────────────────────────────────────────
page_header("✍️", "Essay Assistant",
            "NZ Law Style Guide (3rd ed) · IRAC structure · Formal academic prose")

if rubric:
    st.markdown(
        "<div style='background:#FFFBEB; border:1.5px solid #FDE68A; border-left:4px solid #C9A84C;"
        " border-radius:0 8px 8px 0; padding:.6rem 1rem; font-size:.85rem; color:#78350F; margin-bottom:.75rem;'>"
        "📋 <strong>Rubric active</strong> — essays and critiques will be aligned with your marking criteria."
        "</div>",
        unsafe_allow_html=True,
    )

# ── Workflow steps indicator ──────────────────────────────────────────────────
q_done = bool(st.session_state.get("essay_question_input", "").strip())
plan_done = bool(st.session_state.get("essay_plan", "").strip())
draft_done = bool(st.session_state.get("essay_draft", "").strip())

st.markdown(
    f"""<div class="step-row">
        <span class="step {'done' if q_done else 'active'}">1 · Analyse Question</span>
        <span style="color:#DDE3EE">→</span>
        <span class="step {'done' if plan_done else ('active' if q_done else '')}">2 · Plan</span>
        <span style="color:#DDE3EE">→</span>
        <span class="step {'done' if draft_done else ('active' if plan_done else '')}">3 · Draft</span>
        <span style="color:#DDE3EE">→</span>
        <span class="step {'active' if draft_done else ''}">4 · Critique</span>
    </div>""",
    unsafe_allow_html=True,
)

# ── Docs ──────────────────────────────────────────────────────────────────────
all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}
q_key = "essay_question_input"

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Analyse Question", "📐 Essay Plan", "📄 Full Draft", "🔍 Critique", "💬 Chat",
])

# ── Tab 1 ──────────────────────────────────────────────────────────────────────
with tab1:
    tip("Paste your question or problem scenario — the assistant will identify all legal issues and the analytical approach.")
    question = st.text_area(
        "Essay / Problem Question",
        value=st.session_state[q_key], height=140,
        placeholder="Paste your essay question or problem scenario here...",
        key="q_analyse",
    )
    st.session_state[q_key] = question
    selected_t = st.multiselect("Documents to use (optional — leave empty to search all)",
                                 options=list(doc_options.keys()), key="docs_analyse")
    doc_ids = [doc_options[t]["doc_id"] for t in selected_t] if selected_t else None

    if st.button("Analyse Question", type="primary", key="btn_analyse") and question.strip():
        st.markdown("---")
        result = _stream(assistant.analyse_question(question, doc_ids=doc_ids,
                                                    current_subject=current_subject, rubric=rubric))
        st.session_state["essay_analysis"] = result
        _save()

# ── Tab 2 ──────────────────────────────────────────────────────────────────────
with tab2:
    tip("Generates a numbered essay outline with issue headings, key authorities, and word allocations per section.")
    question2 = st.text_area("Essay / Problem Question", value=st.session_state[q_key],
                              height=120, key="q_plan")
    st.session_state[q_key] = question2
    word_limit = st.select_slider("Word limit", options=[500,750,1000,1500,2000,2500,3000], value=1500)
    selected_t2 = st.multiselect("Documents to use", options=list(doc_options.keys()), key="docs_plan")
    doc_ids2 = [doc_options[t]["doc_id"] for t in selected_t2] if selected_t2 else None

    if st.button("Generate Essay Plan", type="primary", key="btn_plan") and question2.strip():
        st.markdown("---")
        result = _stream(assistant.generate_plan(question2, word_limit=word_limit, doc_ids=doc_ids2,
                                                  current_subject=current_subject, rubric=rubric))
        st.session_state["essay_plan"] = result
        _save()

    if st.session_state.get("essay_plan"):
        with st.expander("View current plan"):
            st.markdown(st.session_state["essay_plan"])

# ── Tab 3 ──────────────────────────────────────────────────────────────────────
with tab3:
    tip("Writes a full essay in NZ academic style using your plan and uploaded materials as authority.")
    question3 = st.text_area("Essay / Problem Question", value=st.session_state[q_key],
                              height=100, key="q_draft")
    st.session_state[q_key] = question3
    plan_text = st.text_area("Essay Plan", value=st.session_state.get("essay_plan",""), height=180,
                              placeholder="Generate a plan in the Plan tab, or paste one here.",
                              key="plan_input")
    wl3 = st.select_slider("Target word count", options=[500,750,1000,1500,2000,2500,3000],
                            value=1500, key="wl_draft")
    selected_t3 = st.multiselect("Documents to use", options=list(doc_options.keys()), key="docs_draft")
    doc_ids3 = [doc_options[t]["doc_id"] for t in selected_t3] if selected_t3 else None

    if st.button("Draft Essay", type="primary", key="btn_draft") and question3.strip():
        st.markdown("---")
        result = _stream(assistant.draft_essay(question=question3, plan=plan_text, word_limit=wl3,
                                               doc_ids=doc_ids3, current_subject=current_subject, rubric=rubric))
        st.session_state["essay_draft"] = result
        _save()
        st.download_button("📥 Download Draft", data=result,
                           file_name="essay_draft.md", mime="text/markdown")

# ── Tab 4 ──────────────────────────────────────────────────────────────────────
with tab4:
    tip("Paste your essay for detailed critique — structure, authority, citations, argument strength, and a grade band.")
    question4 = st.text_area("Essay Question", value=st.session_state[q_key], height=90, key="q_crit")
    essay_in = st.text_area("Your Essay", value=st.session_state.get("essay_draft",""), height=260,
                            placeholder="Paste your essay here...", key="essay_crit_in")
    if st.button("Get Critique", type="primary", key="btn_crit") and question4.strip() and essay_in.strip():
        st.markdown("---")
        _stream(assistant.critique_essay(question=question4, essay_text=essay_in,
                                         current_subject=current_subject, rubric=rubric))

# ── Tab 5 ──────────────────────────────────────────────────────────────────────
with tab5:
    tip("Ask anything — strengthen an argument, understand a case, discuss counter-arguments, refine a paragraph.")
    selected_t5 = st.multiselect("Documents to use", options=list(doc_options.keys()), key="docs_chat")
    doc_ids5 = [doc_options[t]["doc_id"] for t in selected_t5] if selected_t5 else None

    if not st.session_state["essay_chat_history"]:
        st.markdown(
            "<p style='color:#94A3B8; font-size:.85rem; text-align:center; padding:1rem 0;'>"
            "Your conversation will appear here.</p>", unsafe_allow_html=True,
        )

    for msg in st.session_state["essay_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your essay or legal issues..."):
        st.session_state["essay_chat_history"].append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            history_api = [{"role":m["role"],"content":m["content"]}
                           for m in st.session_state["essay_chat_history"][:-1]]
            result = _stream(assistant.chat(message=prompt, history=history_api,
                                            doc_ids=doc_ids5, current_subject=current_subject, rubric=rubric))
        st.session_state["essay_chat_history"].append({"role":"assistant","content":result})
        _save()

    if st.session_state["essay_chat_history"]:
        if st.button("Clear conversation", key="clear_essay_chat"):
            st.session_state["essay_chat_history"] = []
            _save()
            st.rerun()
