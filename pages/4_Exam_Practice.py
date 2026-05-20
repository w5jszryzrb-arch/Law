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

st.set_page_config(page_title="Exam Practice — NZ Law Assistant", page_icon="📝", layout="wide")

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
    if "exam_practice" not in st.session_state:
        st.session_state["exam_practice"] = ExamPractice(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
exam: ExamPractice = st.session_state["exam_practice"]

# ── Load saved state ──────────────────────────────────────────────────────────
_PAGE = "exam"
_saved: dict = sm.load_conversation(project_id, _PAGE) if project_id else {}

if "generated_question" not in st.session_state:
    st.session_state["generated_question"] = _saved.get("generated_question", "")
if "generated_q_time" not in st.session_state:
    st.session_state["generated_q_time"] = _saved.get("q_time", 30)
if "generated_q_marks" not in st.session_state:
    st.session_state["generated_q_marks"] = _saved.get("q_marks", 25)


def _save_state():
    if project_id:
        sm.save_conversation(project_id, _PAGE, {
            "generated_question": st.session_state.get("generated_question", ""),
            "q_time": st.session_state.get("generated_q_time", 30),
            "q_marks": st.session_state.get("generated_q_marks", 25),
        })


def _stream_to_ui(generator) -> str:
    output = st.empty()
    full_text = ""
    for chunk in generator:
        full_text += chunk
        output.markdown(full_text + "▌")
    output.markdown(full_text)
    return full_text


# ── UI ────────────────────────────────────────────────────────────────────────
if project_id:
    proj = sm.get_project(project_id)
    st.caption(f"Project: **{proj['subject']}**" if proj else "")

st.title("📝 Exam Practice")
st.info(
    "**Course content only.** Questions and model answers are generated strictly from your uploaded "
    "course materials — past papers, workshop questions, lectures, and cases.",
    icon="📌",
)

all_docs = vs.list_documents()
doc_options = {d["title"]: d for d in all_docs}
past_paper_docs = [d for d in all_docs if d["doc_type"] == "past_paper"]
workshop_docs = [d for d in all_docs if d["doc_type"] == "workshop_question"]

if len(all_docs) < 1:
    st.warning("Upload your course materials in **Documents** first.")

tab_gen, tab_model, tab_mark, tab_past, tab_workshop = st.tabs([
    "🗒️ Generate Questions",
    "📋 Model Answer",
    "✏️ Mark My Answer",
    "📄 Past Papers",
    "📚 Workshop Questions",
])

# ── Tab: Generate Questions ───────────────────────────────────────────────────
with tab_gen:
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_input(
            "Topic / legal issue",
            placeholder="e.g. Offer and acceptance, Negligence — duty of care",
        )
    with col2:
        difficulty = st.selectbox("Difficulty", ["Foundation", "Intermediate", "Advanced"])

    col3, col4, col5 = st.columns(3)
    with col3:
        q_type = st.selectbox(
            "Question type",
            options=["problem_question", "essay_question", "short_answer"],
            format_func=lambda x: {
                "problem_question": "Problem Question",
                "essay_question": "Essay Question",
                "short_answer": "Short Answer",
            }[x],
        )
    with col4:
        time_mins = st.number_input("Time (minutes)", min_value=10, max_value=120, value=30, step=5)
    with col5:
        marks = st.number_input("Marks", min_value=5, max_value=100, value=25, step=5)

    selected_doc_titles = st.multiselect(
        "Restrict to these documents (optional — leave empty to use all)",
        options=list(doc_options.keys()),
    )
    doc_ids = [doc_options[t]["doc_id"] for t in selected_doc_titles] if selected_doc_titles else None

    if past_paper_docs or workshop_docs:
        st.caption(
            f"Pattern sources: {len(past_paper_docs)} past paper(s), {len(workshop_docs)} workshop question set(s) available."
        )

    if st.button("Generate Question", type="primary", key="btn_gen_q") and topic.strip():
        st.markdown("---")
        result = _stream_to_ui(
            exam.generate_questions(
                topic=topic, question_type=q_type, difficulty=difficulty.lower(),
                n_questions=1, doc_ids=doc_ids, time_minutes=int(time_mins),
                marks=int(marks), current_subject=current_subject,
            )
        )
        st.session_state["generated_question"] = result
        st.session_state["generated_q_time"] = time_mins
        st.session_state["generated_q_marks"] = marks
        _save_state()

# ── Tab: Model Answer ─────────────────────────────────────────────────────────
with tab_model:
    question_input = st.text_area(
        "Question",
        value=st.session_state.get("generated_question", ""),
        height=150,
        placeholder="Paste a question here, or generate one in the Generate tab.",
    )
    col1, col2 = st.columns(2)
    with col1:
        time_model = st.number_input(
            "Time (minutes)", min_value=10, max_value=120,
            value=int(st.session_state.get("generated_q_time", 30)), step=5, key="time_model",
        )
    with col2:
        marks_model = st.number_input(
            "Marks", min_value=5, max_value=100,
            value=int(st.session_state.get("generated_q_marks", 25)), step=5, key="marks_model",
        )
    selected_doc_titles2 = st.multiselect(
        "Restrict to these documents (optional)", options=list(doc_options.keys()), key="docs_model"
    )
    doc_ids2 = [doc_options[t]["doc_id"] for t in selected_doc_titles2] if selected_doc_titles2 else None

    if st.button("Show Model Answer", type="primary", key="btn_model") and question_input.strip():
        st.markdown("---")
        result = _stream_to_ui(
            exam.model_answer(
                question=question_input, time_minutes=int(time_model), marks=int(marks_model),
                doc_ids=doc_ids2, current_subject=current_subject,
            )
        )
        st.session_state["model_answer"] = result
        st.download_button(
            "📥 Download Model Answer", data=result,
            file_name="model_answer.md", mime="text/markdown",
        )

# ── Tab: Mark My Answer ───────────────────────────────────────────────────────
with tab_mark:
    question_mark = st.text_area(
        "Question",
        value=st.session_state.get("generated_question", ""),
        height=120,
        placeholder="Paste the question here.",
        key="q_mark",
    )
    student_answer = st.text_area(
        "Your Answer", height=300,
        placeholder="Write or paste your answer here...", key="student_answer",
    )
    selected_doc_titles3 = st.multiselect(
        "Restrict to these documents (optional)", options=list(doc_options.keys()), key="docs_mark"
    )
    doc_ids3 = [doc_options[t]["doc_id"] for t in selected_doc_titles3] if selected_doc_titles3 else None

    if (
        st.button("Get Feedback", type="primary", key="btn_mark")
        and question_mark.strip() and student_answer.strip()
    ):
        st.markdown("---")
        _stream_to_ui(
            exam.mark_answer(
                question=question_mark, student_answer=student_answer,
                doc_ids=doc_ids3, current_subject=current_subject,
            )
        )

# ── Tab: Past Papers ──────────────────────────────────────────────────────────
with tab_past:
    st.markdown("### Upload Past Exam Papers")
    st.markdown(
        "Upload past papers so the model learns your exam's format, question style, "
        "mark allocations, and topic weighting. This improves generated practice questions."
    )

    past_upload = st.file_uploader(
        "Upload past exam paper(s)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="past_paper_upload",
    )
    if past_upload:
        with st.form("past_paper_form"):
            pp_titles: dict[str, str] = {}
            for uf in past_upload:
                pp_titles[uf.name] = st.text_input(
                    f"Title for {uf.name}",
                    value=uf.name.rsplit(".", 1)[0],
                    key=f"pp_title_{uf.name}",
                )
            submitted_pp = st.form_submit_button("Upload Past Papers", type="primary")

        if submitted_pp:
            for uf in past_upload:
                with st.status(f"Processing {uf.name}...") as status:
                    try:
                        doc = process_uploaded_file(
                            file_bytes=uf.read(),
                            original_filename=uf.name,
                            title=pp_titles[uf.name],
                            doc_type="past_paper",
                        )
                        vs.add_chunks(doc.chunks, config.COLLECTIONS["past_paper"])
                        status.update(label=f"✅ {pp_titles[uf.name]} uploaded", state="complete")
                    except Exception as e:
                        status.update(label=f"❌ Failed: {e}", state="error")
            st.rerun()

    st.divider()
    if not past_paper_docs:
        st.info("No past papers uploaded yet.")
    else:
        st.markdown("### Uploaded Past Papers")
        for d in past_paper_docs:
            with st.expander(f"**{d['title']}**"):
                if st.button("Analyse this past paper", key=f"analyse_pp_{d['doc_id']}"):
                    st.markdown("---")
                    result = _stream_to_ui(
                        exam.analyse_past_paper(
                            doc_id=d["doc_id"], current_subject=current_subject,
                        )
                    )
                    if result:
                        st.download_button(
                            "📥 Download Analysis", data=result,
                            file_name=f"{d['title']}_analysis.md", mime="text/markdown",
                        )
                if st.button("🗑️ Delete", key=f"del_pp_{d['doc_id']}"):
                    vs.delete_document(d["doc_id"], d["collection"])
                    st.rerun()

# ── Tab: Workshop Questions ───────────────────────────────────────────────────
with tab_workshop:
    st.markdown("### Upload Workshop / Tutorial Questions")
    st.markdown(
        "Upload questions from workshops, tutorials, or problem sets. "
        "The model will use these to understand question style and topic focus, "
        "and can generate practice questions in the same style."
    )

    ws_upload = st.file_uploader(
        "Upload workshop question set(s)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="workshop_upload",
    )
    if ws_upload:
        with st.form("workshop_form"):
            ws_titles: dict[str, str] = {}
            for uf in ws_upload:
                ws_titles[uf.name] = st.text_input(
                    f"Title for {uf.name}",
                    value=uf.name.rsplit(".", 1)[0],
                    key=f"ws_title_{uf.name}",
                )
            submitted_ws = st.form_submit_button("Upload Workshop Questions", type="primary")

        if submitted_ws:
            for uf in ws_upload:
                with st.status(f"Processing {uf.name}...") as status:
                    try:
                        doc = process_uploaded_file(
                            file_bytes=uf.read(),
                            original_filename=uf.name,
                            title=ws_titles[uf.name],
                            doc_type="workshop_question",
                        )
                        vs.add_chunks(doc.chunks, config.COLLECTIONS["workshop_question"])
                        status.update(label=f"✅ {ws_titles[uf.name]} uploaded", state="complete")
                    except Exception as e:
                        status.update(label=f"❌ Failed: {e}", state="error")
            st.rerun()

    st.divider()
    if not workshop_docs:
        st.info("No workshop questions uploaded yet.")
    else:
        st.markdown("### Uploaded Workshop Questions")
        for d in workshop_docs:
            with st.expander(f"**{d['title']}**"):
                if st.button("Analyse question style", key=f"analyse_ws_{d['doc_id']}"):
                    st.markdown("---")
                    chunks = exam.pipeline.retrieve_full_document(
                        d["doc_id"], config.COLLECTIONS["workshop_question"]
                    )
                    _stream_to_ui(
                        exam.pipeline.stream(
                            system_prompt=__import__("src.prompts", fromlist=["PAST_PAPER_ANALYSIS_PROMPT"]).PAST_PAPER_ANALYSIS_PROMPT,
                            user_query=(
                                "Analyse these workshop/tutorial questions. Extract: topics covered, "
                                "question types and formats, difficulty level, skills being tested, "
                                "and how they compare to typical exam questions."
                            ),
                            mode="exam",
                            chunks=chunks,
                            current_subject=current_subject,
                        )
                    )
                if st.button("🗑️ Delete", key=f"del_ws_{d['doc_id']}"):
                    vs.delete_document(d["doc_id"], d["collection"])
                    st.rerun()
