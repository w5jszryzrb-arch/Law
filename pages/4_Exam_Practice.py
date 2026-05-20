import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import config
import src.session_manager as sm
from src.document_processor import process_uploaded_file
from src.vector_store import LegalVectorStore
from src.claude_client import ClaudeClient
from src.rag_pipeline import RAGPipeline
from src.exam_practice import ExamPractice
from src.ui_utils import render_sidebar
from src.styles import page_header, tip

st.set_page_config(page_title="Exam Practice — NZ Law Assistant", page_icon="📝", layout="wide")
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
    if "exam_practice" not in st.session_state:
        st.session_state["exam_practice"] = ExamPractice(st.session_state["rag_pipeline"])

_init()
vs: LegalVectorStore = st.session_state["vector_store"]
exam: ExamPractice = st.session_state["exam_practice"]

# ── Restore state ─────────────────────────────────────────────────────────────
_PAGE = "exam"
_saved = sm.load_conversation(project_id, _PAGE) if project_id else {}
if "generated_question" not in st.session_state:
    st.session_state["generated_question"] = _saved.get("generated_question", "")
if "generated_q_time" not in st.session_state:
    st.session_state["generated_q_time"] = _saved.get("q_time", 30)
if "generated_q_marks" not in st.session_state:
    st.session_state["generated_q_marks"] = _saved.get("q_marks", 25)

def _save():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "generated_question": st.session_state.get("generated_question",""),
            "q_time": st.session_state.get("generated_q_time", 30),
            "q_marks": st.session_state.get("generated_q_marks", 25),
        })

def _stream(gen) -> str:
    out = st.empty()
    text = ""
    for chunk in gen:
        text += chunk
        out.markdown(f'<div class="output-box">{text}▌</div>', unsafe_allow_html=True)
    out.markdown(f'<div class="output-box">{text}</div>', unsafe_allow_html=True)
    return text

# ── Page header ───────────────────────────────────────────────────────────────
page_header("📝", "Exam Practice",
            "Strictly course-content only · IRAC model answers · Past paper analysis")

all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}
past_paper_docs = [d for d in all_docs if d["doc_type"] == "past_paper"]
workshop_docs   = [d for d in all_docs if d["doc_type"] == "workshop_question"]

# Content status bar
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Course Docs",  len([d for d in all_docs if d["doc_type"] in ("case_law","lecture","statute","article")]))
with c2: st.metric("Past Papers",  len(past_paper_docs))
with c3: st.metric("Workshop Qs", len(workshop_docs))
with c4: st.metric("Total Docs",  len(all_docs))

if not all_docs:
    st.warning("Upload course materials in **Documents** before generating practice questions.", icon="⚠️")

st.markdown(
    "<div style='background:#EFF6FF; border:1.5px solid #BFDBFE; border-left:4px solid #1B2D4F;"
    " border-radius:0 8px 8px 0; padding:.65rem 1rem; font-size:.85rem; color:#1E3A8A; margin:.5rem 0 1rem;'>"
    "🔒 <strong>Course content only</strong> — questions and model answers are generated exclusively "
    "from your uploaded materials. Claude will not use general legal knowledge."
    "</div>",
    unsafe_allow_html=True,
)

tab_gen, tab_model, tab_mark, tab_past, tab_ws = st.tabs([
    "🗒️ Generate Question",
    "📋 Model Answer",
    "✏️ Mark My Answer",
    "📄 Past Papers",
    "📚 Workshop Questions",
])

# ── Generate ──────────────────────────────────────────────────────────────────
with tab_gen:
    tip("Generate a practice question in the exact style of your past papers and workshop questions.")
    col1, col2 = st.columns([3,1])
    with col1:
        topic = st.text_input("Topic / legal issue",
                              placeholder="e.g. Offer and acceptance  |  Duty of care  |  Mens rea")
    with col2:
        difficulty = st.selectbox("Difficulty", ["Foundation","Intermediate","Advanced"])

    col3, col4, col5 = st.columns(3)
    with col3:
        q_type = st.selectbox("Question type",
            options=["problem_question","essay_question","short_answer"],
            format_func=lambda x: {"problem_question":"Problem Question",
                                   "essay_question":"Essay Question",
                                   "short_answer":"Short Answer"}[x])
    with col4:
        time_mins = st.number_input("Time (min)", min_value=10, max_value=120, value=30, step=5)
    with col5:
        marks = st.number_input("Marks", min_value=5, max_value=100, value=25, step=5)

    sel_docs = st.multiselect("Restrict to these documents (optional)",
                               options=list(doc_options.keys()), key="gen_docs")
    doc_ids = [doc_options[t]["doc_id"] for t in sel_docs] if sel_docs else None

    if past_paper_docs or workshop_docs:
        st.caption(f"Pattern sources: {len(past_paper_docs)} past paper(s) · {len(workshop_docs)} workshop set(s) will shape question style.")

    if st.button("Generate Question", type="primary", key="btn_gen") and topic.strip():
        st.markdown("---")
        result = _stream(exam.generate_questions(
            topic=topic, question_type=q_type, difficulty=difficulty.lower(),
            n_questions=1, doc_ids=doc_ids, time_minutes=int(time_mins),
            marks=int(marks), current_subject=current_subject,
        ))
        st.session_state["generated_question"] = result
        st.session_state["generated_q_time"] = time_mins
        st.session_state["generated_q_marks"] = marks
        _save()

# ── Model Answer ──────────────────────────────────────────────────────────────
with tab_model:
    tip("Model answers use IRAC structure and cite only cases/statutes from your uploaded materials.")
    question_in = st.text_area("Question",
        value=st.session_state.get("generated_question",""), height=140,
        placeholder="Paste a question here, or generate one in the Generate tab.")
    col1, col2 = st.columns(2)
    with col1:
        t_model = st.number_input("Time (min)", min_value=10, max_value=120,
                                   value=int(st.session_state.get("generated_q_time",30)), step=5, key="t_model")
    with col2:
        m_model = st.number_input("Marks", min_value=5, max_value=100,
                                   value=int(st.session_state.get("generated_q_marks",25)), step=5, key="m_model")
    sel_docs2 = st.multiselect("Restrict to these documents (optional)",
                                options=list(doc_options.keys()), key="model_docs")
    doc_ids2 = [doc_options[t]["doc_id"] for t in sel_docs2] if sel_docs2 else None

    if st.button("Show Model Answer", type="primary", key="btn_model") and question_in.strip():
        st.markdown("---")
        result = _stream(exam.model_answer(
            question=question_in, time_minutes=int(t_model), marks=int(m_model),
            doc_ids=doc_ids2, current_subject=current_subject,
        ))
        st.session_state["model_answer"] = result
        st.download_button("📥 Download Model Answer", data=result,
                           file_name="model_answer.md", mime="text/markdown")

# ── Mark My Answer ────────────────────────────────────────────────────────────
with tab_mark:
    tip("Paste your answer for detailed feedback — what you got right, what you missed, and a grade band.")
    q_mark = st.text_area("Question",
        value=st.session_state.get("generated_question",""), height=100,
        placeholder="Paste the question here.", key="q_mark")
    student_ans = st.text_area("Your Answer", height=280,
        placeholder="Write or paste your answer here...", key="student_ans")
    sel_docs3 = st.multiselect("Restrict to these documents (optional)",
                                options=list(doc_options.keys()), key="mark_docs")
    doc_ids3 = [doc_options[t]["doc_id"] for t in sel_docs3] if sel_docs3 else None

    if (st.button("Get Feedback", type="primary", key="btn_mark")
            and q_mark.strip() and student_ans.strip()):
        st.markdown("---")
        _stream(exam.mark_answer(question=q_mark, student_answer=student_ans,
                                  doc_ids=doc_ids3, current_subject=current_subject))

# ── Past Papers ────────────────────────────────────────────────────────────────
with tab_past:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("#### Upload Past Exam Papers")
        st.markdown(
            "<p style='color:#64748B; font-size:.875rem;'>"
            "Upload past papers so the model learns your exam's format, question style, "
            "mark allocations, and topic weighting.</p>",
            unsafe_allow_html=True,
        )
        pp_upload = st.file_uploader("Upload past paper(s)", type=["pdf","txt"],
                                      accept_multiple_files=True, key="pp_upload")
        if pp_upload:
            with st.form("pp_form"):
                pp_titles = {uf.name: st.text_input(f"Title — {uf.name}",
                    value=uf.name.rsplit(".",1)[0], key=f"pp_t_{uf.name}") for uf in pp_upload}
                if st.form_submit_button("Upload Past Papers", type="primary"):
                    for uf in pp_upload:
                        with st.status(f"Processing {uf.name}...") as s:
                            try:
                                doc = process_uploaded_file(uf.read(), uf.name,
                                                            pp_titles[uf.name], "past_paper")
                                vs.add_chunks(doc.chunks, config.COLLECTIONS["past_paper"])
                                s.update(label=f"✅ {pp_titles[uf.name]}", state="complete")
                            except Exception as e:
                                s.update(label=f"❌ {e}", state="error")
                    st.rerun()

    with col_r:
        st.markdown("#### Uploaded Past Papers")
        if not past_paper_docs:
            st.markdown(
                "<div style='background:#F8FAFC; border:2px dashed #DDE3EE; border-radius:10px;"
                " padding:1.5rem; text-align:center;'>"
                "<p style='color:#94A3B8; font-size:.85rem; margin:0;'>No past papers yet</p></div>",
                unsafe_allow_html=True,
            )
        else:
            for d in past_paper_docs:
                with st.container(border=True):
                    st.markdown(f"**{d['title']}**")
                    c_btn, c_del = st.columns([3,1])
                    with c_btn:
                        if st.button("Analyse", key=f"ap_{d['doc_id']}", use_container_width=True):
                            st.markdown("---")
                            result = _stream(exam.analyse_past_paper(
                                doc_id=d["doc_id"], current_subject=current_subject))
                            if result:
                                st.download_button("📥 Download", data=result,
                                    file_name=f"{d['title']}_analysis.md", mime="text/markdown")
                    with c_del:
                        if st.button("🗑", key=f"dp_{d['doc_id']}", use_container_width=True):
                            vs.delete_document(d["doc_id"], d["collection"]); st.rerun()

# ── Workshop Questions ─────────────────────────────────────────────────────────
with tab_ws:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("#### Upload Workshop / Tutorial Questions")
        st.markdown(
            "<p style='color:#64748B; font-size:.875rem;'>"
            "Upload questions from workshops or tutorials. The model will learn the question "
            "style and use these when generating practice questions.</p>",
            unsafe_allow_html=True,
        )
        ws_upload = st.file_uploader("Upload workshop question set(s)", type=["pdf","txt"],
                                      accept_multiple_files=True, key="ws_upload")
        if ws_upload:
            with st.form("ws_form"):
                ws_titles = {uf.name: st.text_input(f"Title — {uf.name}",
                    value=uf.name.rsplit(".",1)[0], key=f"ws_t_{uf.name}") for uf in ws_upload}
                if st.form_submit_button("Upload Workshop Questions", type="primary"):
                    for uf in ws_upload:
                        with st.status(f"Processing {uf.name}...") as s:
                            try:
                                doc = process_uploaded_file(uf.read(), uf.name,
                                                            ws_titles[uf.name], "workshop_question")
                                vs.add_chunks(doc.chunks, config.COLLECTIONS["workshop_question"])
                                s.update(label=f"✅ {ws_titles[uf.name]}", state="complete")
                            except Exception as e:
                                s.update(label=f"❌ {e}", state="error")
                    st.rerun()

    with col_r:
        st.markdown("#### Uploaded Workshop Questions")
        if not workshop_docs:
            st.markdown(
                "<div style='background:#F8FAFC; border:2px dashed #DDE3EE; border-radius:10px;"
                " padding:1.5rem; text-align:center;'>"
                "<p style='color:#94A3B8; font-size:.85rem; margin:0;'>No workshop questions yet</p></div>",
                unsafe_allow_html=True,
            )
        else:
            for d in workshop_docs:
                with st.container(border=True):
                    st.markdown(f"**{d['title']}**")
                    c_btn, c_del = st.columns([3,1])
                    with c_btn:
                        if st.button("Analyse Style", key=f"aw_{d['doc_id']}", use_container_width=True):
                            st.markdown("---")
                            from src.prompts import PAST_PAPER_ANALYSIS_PROMPT
                            chunks = exam.pipeline.retrieve_full_document(
                                d["doc_id"], config.COLLECTIONS["workshop_question"])
                            _stream(exam.pipeline.stream(
                                system_prompt=PAST_PAPER_ANALYSIS_PROMPT,
                                user_query=(
                                    "Analyse these workshop/tutorial questions. Extract: topics covered, "
                                    "question types and formats, difficulty level, skills being tested, "
                                    "and how they compare to typical exam questions."
                                ),
                                mode="exam", chunks=chunks, current_subject=current_subject,
                            ))
                    with c_del:
                        if st.button("🗑", key=f"dw_{d['doc_id']}", use_container_width=True):
                            vs.delete_document(d["doc_id"], d["collection"]); st.rerun()
