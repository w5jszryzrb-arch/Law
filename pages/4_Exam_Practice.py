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
from src.exam_practice import ExamPractice

st.set_page_config(page_title="Exam Practice — NZ Law Assistant", page_icon="📝", layout="wide")

with st.sidebar:
    st.markdown("## ⚖️ NZ Law Assistant")
    st.divider()
    current_subject = st.text_input(
        "Current subject / topic",
        value=st.session_state.get("current_subject", ""),
        placeholder="e.g. Contract Law — Offer and Acceptance",
    )
    st.session_state["current_subject"] = current_subject

st.title("📝 Exam Practice")
st.info(
    "**Course content only.** Questions and model answers are generated strictly from your uploaded "
    "course materials. No external legal knowledge is used.",
    icon="📌",
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
    if "exam_practice" not in st.session_state:
        st.session_state["exam_practice"] = ExamPractice(st.session_state["rag_pipeline"])


_init_resources()
vs: LegalVectorStore = st.session_state["vector_store"]
exam: ExamPractice = st.session_state["exam_practice"]


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
past_paper_docs = [d for d in all_docs if d["doc_type"] == "past_paper"]

if len(all_docs) < 2:
    st.warning(
        "⚠️ Fewer than 2 documents uploaded. Upload your course materials in the **Documents** page "
        "so exam questions can be grounded in your content."
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["🗒️ Generate Questions", "📋 Model Answer", "✏️ Mark My Answer", "📄 Past Paper Analysis"]
)

# --- Tab 1: Generate Questions ---
with tab1:
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
        "Restrict to these documents (optional)",
        options=list(doc_options.keys()),
    )
    doc_ids = [doc_options[t]["doc_id"] for t in selected_doc_titles] if selected_doc_titles else None

    if st.button("Generate Question", type="primary", key="btn_gen_q") and topic.strip():
        st.markdown("---")
        result = _stream_to_ui(
            exam.generate_questions(
                topic=topic,
                question_type=q_type,
                difficulty=difficulty.lower(),
                n_questions=1,
                doc_ids=doc_ids,
                time_minutes=int(time_mins),
                marks=int(marks),
                current_subject=current_subject,
            )
        )
        st.session_state["generated_question"] = result
        st.session_state["generated_q_time"] = time_mins
        st.session_state["generated_q_marks"] = marks

# --- Tab 2: Model Answer ---
with tab2:
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
            value=int(st.session_state.get("generated_q_time", 30)), step=5, key="time_model"
        )
    with col2:
        marks_model = st.number_input(
            "Marks", min_value=5, max_value=100,
            value=int(st.session_state.get("generated_q_marks", 25)), step=5, key="marks_model"
        )

    selected_doc_titles2 = st.multiselect(
        "Restrict to these documents (optional)",
        options=list(doc_options.keys()),
        key="docs_model",
    )
    doc_ids2 = [doc_options[t]["doc_id"] for t in selected_doc_titles2] if selected_doc_titles2 else None

    if st.button("Show Model Answer", type="primary", key="btn_model") and question_input.strip():
        st.markdown("---")
        result = _stream_to_ui(
            exam.model_answer(
                question=question_input,
                time_minutes=int(time_model),
                marks=int(marks_model),
                doc_ids=doc_ids2,
                current_subject=current_subject,
            )
        )
        st.session_state["model_answer"] = result
        st.download_button(
            "📥 Download Model Answer",
            data=result,
            file_name="model_answer.md",
            mime="text/markdown",
        )

# --- Tab 3: Mark My Answer ---
with tab3:
    question_mark = st.text_area(
        "Question",
        value=st.session_state.get("generated_question", ""),
        height=120,
        placeholder="Paste the question here.",
        key="q_mark",
    )
    student_answer = st.text_area(
        "Your Answer",
        height=300,
        placeholder="Write or paste your answer here...",
        key="student_answer",
    )

    selected_doc_titles3 = st.multiselect(
        "Restrict to these documents (optional)",
        options=list(doc_options.keys()),
        key="docs_mark",
    )
    doc_ids3 = [doc_options[t]["doc_id"] for t in selected_doc_titles3] if selected_doc_titles3 else None

    if (
        st.button("Get Feedback", type="primary", key="btn_mark")
        and question_mark.strip()
        and student_answer.strip()
    ):
        st.markdown("---")
        _stream_to_ui(
            exam.mark_answer(
                question=question_mark,
                student_answer=student_answer,
                doc_ids=doc_ids3,
                current_subject=current_subject,
            )
        )

# --- Tab 4: Past Paper Analysis ---
with tab4:
    if not past_paper_docs:
        st.warning(
            "No past exam papers uploaded. Upload them in the **Documents** page and select "
            "'Past Exam Paper' as the document type."
        )
    else:
        selected_paper = st.selectbox(
            "Select a past paper to analyse",
            options=past_paper_docs,
            format_func=lambda d: d["title"],
        )
        if st.button("Analyse Past Paper", type="primary", key="btn_past_paper"):
            st.markdown("---")
            result = _stream_to_ui(
                exam.analyse_past_paper(
                    doc_id=selected_paper["doc_id"],
                    current_subject=current_subject,
                )
            )
            if result:
                st.download_button(
                    "📥 Download Analysis",
                    data=result,
                    file_name=f"{selected_paper['title']}_analysis.md",
                    mime="text/markdown",
                )
