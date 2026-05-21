"""
NZ Law School Essay Assistant — Flask web app.

Run with:
    python app.py

Then open http://localhost:5000 in your browser.
Requires ANTHROPIC_API_KEY in a .env file.
"""
import json
import os
import secrets
from typing import Generator

from dotenv import load_dotenv
from flask import (
    Flask, Response, abort, jsonify, redirect, render_template, request,
    send_from_directory, session, stream_with_context, url_for,
)

load_dotenv()

import config
import src.session_manager as sm
from src.case_analyzer import CaseAnalyzer
from src.claude_client import ClaudeClient
from src.document_processor import process_uploaded_file
from src.essay_assistant import EssayAssistant
from src.exam_practice import ExamPractice
from src.notes_generator import NotesGenerator
from src.prompts import PAST_PAPER_ANALYSIS_PROMPT
from src.rag_pipeline import RAGPipeline
from src.vector_store import LegalVectorStore

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB upload cap

# ── Shared services ──────────────────────────────────────────────────────────
_VS: LegalVectorStore | None = None
_CLAUDE: ClaudeClient | None = None
_PIPELINE: RAGPipeline | None = None
_CASE: CaseAnalyzer | None = None
_ESSAY: EssayAssistant | None = None
_EXAM: ExamPractice | None = None
_NOTES: NotesGenerator | None = None


def services():
    """Lazy-initialise the heavy services on first request."""
    global _VS, _CLAUDE, _PIPELINE, _CASE, _ESSAY, _EXAM, _NOTES
    if _VS is None:
        _VS = LegalVectorStore()
        _CLAUDE = ClaudeClient()
        _PIPELINE = RAGPipeline(_VS, _CLAUDE)
        _CASE = CaseAnalyzer(_PIPELINE)
        _ESSAY = EssayAssistant(_PIPELINE)
        _EXAM = ExamPractice(_PIPELINE)
        _NOTES = NotesGenerator(_PIPELINE)
    return _VS, _CASE, _ESSAY, _EXAM, _NOTES


def current_project() -> dict | None:
    pid = session.get("project_id")
    if not pid:
        return None
    proj = sm.get_project(pid)
    if not proj:
        session.pop("project_id", None)
        return None
    return proj


def common_context() -> dict:
    proj = current_project()
    return {
        "project": proj,
        "current_subject": (proj or {}).get("subject", ""),
        "rubric": (proj or {}).get("rubric", ""),
        "project_id": (proj or {}).get("id"),
        "doc_type_labels": config.DOC_TYPE_LABELS,
    }


# ── Streaming helper ─────────────────────────────────────────────────────────
def stream_response(gen: Generator[str, None, None]) -> Response:
    def producer():
        try:
            for chunk in gen:
                if chunk:
                    yield chunk
        except Exception as exc:  # noqa: BLE001
            yield f"\n\n[Error: {exc}]"

    return Response(
        stream_with_context(producer()),
        mimetype="text/plain; charset=utf-8",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── Error handlers ───────────────────────────────────────────────────────────
@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File too large (limit 64 MB)"), 413


# ── Pages ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    projects = sm.list_projects()
    pages_by_project = {p["id"]: sm.get_project_pages(p["id"]) for p in projects}
    return render_template(
        "home.html",
        projects=projects,
        pages_by_project=pages_by_project,
        **common_context(),
    )


@app.route("/documents")
def documents_page():
    vs, *_ = services()
    all_docs = vs.list_documents()
    counts: dict[str, int] = {}
    for d in all_docs:
        counts[d["doc_type"]] = counts.get(d["doc_type"], 0) + 1
    return render_template(
        "documents.html",
        all_docs=all_docs,
        counts=counts,
        **common_context(),
    )


@app.route("/case-analysis")
def case_analysis_page():
    vs, *_ = services()
    case_docs = [d for d in vs.list_documents() if d["doc_type"] == "case_law"]
    saved = (sm.load_conversation(session["project_id"], "case_analysis")
             if session.get("project_id") else {})
    return render_template(
        "case_analysis.html",
        case_docs=case_docs,
        saved=saved,
        **common_context(),
    )


@app.route("/essay")
def essay_page():
    vs, *_ = services()
    all_docs = vs.list_documents()
    saved = (sm.load_conversation(session["project_id"], "essay")
             if session.get("project_id") else {})
    return render_template(
        "essay.html",
        all_docs=all_docs,
        saved=saved,
        **common_context(),
    )


@app.route("/exam")
def exam_page():
    vs, *_ = services()
    all_docs = vs.list_documents()
    past_paper_docs = [d for d in all_docs if d["doc_type"] == "past_paper"]
    workshop_docs = [d for d in all_docs if d["doc_type"] == "workshop_question"]
    marked_script_docs = [d for d in all_docs if d["doc_type"] == "marked_script"]
    course_docs_count = sum(
        1 for d in all_docs
        if d["doc_type"] in ("case_law", "lecture", "statute", "article")
    )
    saved = (sm.load_conversation(session["project_id"], "exam")
             if session.get("project_id") else {})
    return render_template(
        "exam.html",
        all_docs=all_docs,
        past_paper_docs=past_paper_docs,
        workshop_docs=workshop_docs,
        marked_script_docs=marked_script_docs,
        course_docs_count=course_docs_count,
        saved=saved,
        **common_context(),
    )


@app.route("/notes")
def notes_page():
    vs, *_ = services()
    all_docs = vs.list_documents()
    case_docs = [d for d in all_docs if d["doc_type"] == "case_law"]
    return render_template(
        "notes.html",
        all_docs=all_docs,
        case_docs=case_docs,
        **common_context(),
    )


# ── Project routes ───────────────────────────────────────────────────────────
@app.post("/api/projects")
def api_create_project():
    data = request.get_json(silent=True) or request.form
    subject = (data.get("subject") or "").strip()
    description = (data.get("description") or "").strip()
    if not subject:
        return jsonify(error="Subject required"), 400
    pid = sm.create_project(subject=subject, description=description)
    session["project_id"] = pid
    return jsonify(project_id=pid, redirect=url_for("documents_page"))


@app.post("/api/projects/<pid>/open")
def api_open_project(pid: str):
    if not sm.get_project(pid):
        return jsonify(error="Project not found"), 404
    session["project_id"] = pid
    sm.touch_project(pid)
    return jsonify(ok=True, redirect=url_for("documents_page"))


@app.post("/api/projects/<pid>/update")
def api_update_project(pid: str):
    data = request.get_json(silent=True) or {}
    sm.update_project(
        pid,
        subject=data.get("subject"),
        rubric=data.get("rubric"),
        description=data.get("description"),
    )
    return jsonify(ok=True)


@app.post("/api/projects/<pid>/delete")
def api_delete_project(pid: str):
    sm.delete_project(pid)
    if session.get("project_id") == pid:
        session.pop("project_id", None)
    return jsonify(ok=True)


@app.post("/api/leave-project")
def api_leave_project():
    session.pop("project_id", None)
    return jsonify(ok=True, redirect=url_for("home"))


# ── Conversation persistence ─────────────────────────────────────────────────
@app.post("/api/save-conversation")
def api_save_conversation():
    pid = session.get("project_id")
    if not pid:
        return jsonify(ok=False, reason="no_project"), 200
    data = request.get_json(silent=True) or {}
    page = data.get("page", "")
    payload = data.get("data", {})
    if not page:
        return jsonify(error="page required"), 400
    sm.save_conversation(pid, page, payload)
    return jsonify(ok=True)


# ── Documents ────────────────────────────────────────────────────────────────
@app.post("/api/documents/upload")
def api_upload_documents():
    vs, *_ = services()
    files = request.files.getlist("files")
    titles = json.loads(request.form.get("titles") or "{}")
    types = json.loads(request.form.get("types") or "{}")
    if not files:
        return jsonify(error="No files"), 400

    results = []
    for uf in files:
        if not uf or not uf.filename:
            continue
        title = (titles.get(uf.filename) or uf.filename.rsplit(".", 1)[0]).strip()
        doc_type = (types.get(uf.filename) or "").strip() or None
        try:
            doc = process_uploaded_file(
                file_bytes=uf.read(),
                original_filename=uf.filename,
                title=title,
                doc_type=doc_type,
            )
            collection = config.COLLECTIONS.get(doc.doc_type, config.COLLECTIONS["other"])
            vs.add_chunks(doc.chunks, collection)
            results.append({
                "ok": True,
                "filename": uf.filename,
                "title": title,
                "doc_type": doc.doc_type,
                "chunks": len(doc.chunks),
                "chars": len(doc.full_text),
            })
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "filename": uf.filename, "error": str(exc)})
    return jsonify(results=results)


@app.post("/api/documents/<doc_id>/delete")
def api_delete_document(doc_id: str):
    vs, *_ = services()
    payload = request.get_json(silent=True) or {}
    collection = payload.get("collection")
    if not collection:
        return jsonify(error="collection required"), 400
    vs.delete_document(doc_id, collection)
    return jsonify(ok=True)


# ── Case Analysis ────────────────────────────────────────────────────────────
@app.post("/api/case/<action>")
def api_case(action: str):
    _, case, *_ = services()
    payload = request.get_json(silent=True) or {}
    subject = (current_project() or {}).get("subject", "")

    if action == "full":
        return stream_response(case.analyse_full_case(
            doc_id=payload["doc_id"], collection_name=payload["collection"],
            current_subject=subject,
        ))
    if action == "ratio":
        return stream_response(case.extract_ratio(
            doc_id=payload["doc_id"], collection_name=payload["collection"],
            current_subject=subject,
        ))
    if action == "compare":
        return stream_response(case.compare_cases(
            doc_ids=payload["doc_ids"],
            collection_name=config.COLLECTIONS["case_law"],
            comparison_question=payload.get("question") or "the key legal issues",
            current_subject=subject,
        ))
    if action == "chat":
        return stream_response(case.chat_about_case(
            user_message=payload["message"],
            doc_id=payload["doc_id"], collection_name=payload["collection"],
            history=payload.get("history") or [], current_subject=subject,
        ))
    abort(404)


# ── Essay Assistant ──────────────────────────────────────────────────────────
@app.post("/api/essay/<action>")
def api_essay(action: str):
    _, _, essay, *_ = services()
    payload = request.get_json(silent=True) or {}
    proj = current_project() or {}
    subject = proj.get("subject", "")
    rubric = proj.get("rubric", "")
    doc_ids = payload.get("doc_ids") or None

    if action == "analyse":
        return stream_response(essay.analyse_question(
            question=payload["question"], doc_ids=doc_ids,
            current_subject=subject, rubric=rubric,
        ))
    if action == "plan":
        return stream_response(essay.generate_plan(
            question=payload["question"],
            word_limit=int(payload.get("word_limit", 1500)),
            doc_ids=doc_ids, current_subject=subject, rubric=rubric,
        ))
    if action == "draft":
        return stream_response(essay.draft_essay(
            question=payload["question"], plan=payload.get("plan", ""),
            word_limit=int(payload.get("word_limit", 1500)),
            doc_ids=doc_ids, current_subject=subject, rubric=rubric,
        ))
    if action == "critique":
        return stream_response(essay.critique_essay(
            question=payload["question"], essay_text=payload["essay"],
            current_subject=subject, rubric=rubric,
        ))
    if action == "chat":
        return stream_response(essay.chat(
            message=payload["message"], history=payload.get("history") or [],
            doc_ids=doc_ids, current_subject=subject, rubric=rubric,
        ))
    abort(404)


# ── Exam Practice ────────────────────────────────────────────────────────────
@app.post("/api/exam/<action>")
def api_exam(action: str):
    _, _, _, exam, _ = services()
    payload = request.get_json(silent=True) or {}
    subject = (current_project() or {}).get("subject", "")
    doc_ids = payload.get("doc_ids") or None

    if action == "generate":
        return stream_response(exam.generate_questions(
            topic=payload["topic"],
            question_type=payload.get("type", "problem_question"),
            difficulty=payload.get("difficulty", "intermediate"),
            n_questions=1,
            doc_ids=doc_ids,
            time_minutes=int(payload.get("time_minutes", 30)),
            marks=int(payload.get("marks", 25)),
            current_subject=subject,
        ))
    if action == "model":
        return stream_response(exam.model_answer(
            question=payload["question"],
            time_minutes=int(payload.get("time_minutes", 30)),
            marks=int(payload.get("marks", 25)),
            doc_ids=doc_ids, current_subject=subject,
        ))
    if action == "mark":
        return stream_response(exam.mark_answer(
            question=payload["question"], student_answer=payload["answer"],
            doc_ids=doc_ids, current_subject=subject,
        ))
    if action == "analyse-paper":
        return stream_response(exam.analyse_past_paper(
            doc_id=payload["doc_id"], current_subject=subject,
        ))
    if action == "analyse-workshop":
        chunks = exam.pipeline.retrieve_full_document(
            payload["doc_id"], config.COLLECTIONS["workshop_question"]
        )
        return stream_response(exam.pipeline.stream(
            system_prompt=PAST_PAPER_ANALYSIS_PROMPT,
            user_query=(
                "Analyse these workshop/tutorial questions. Extract: topics covered, "
                "question types and formats, difficulty level, skills being tested, "
                "and how they compare to typical exam questions."
            ),
            mode="exam", chunks=chunks, current_subject=subject,
        ))
    if action == "analyse-script":
        return stream_response(exam.analyse_marked_script(
            doc_id=payload["doc_id"], current_subject=subject,
        ))
    abort(404)


# ── Notes ────────────────────────────────────────────────────────────────────
@app.post("/api/notes/<action>")
def api_notes(action: str):
    _, _, _, _, notes = services()
    payload = request.get_json(silent=True) or {}
    subject = (current_project() or {}).get("subject", "")
    doc_ids = payload.get("doc_ids") or None

    if action == "lecture":
        return stream_response(notes.lecture_notes(
            topic=payload["topic"], doc_ids=doc_ids, current_subject=subject,
        ))
    if action == "table":
        return stream_response(notes.case_summary_table(
            doc_ids=payload["doc_ids"], current_subject=subject,
        ))
    if action == "overview":
        return stream_response(notes.topic_overview(
            topic=payload["topic"], doc_ids=doc_ids, current_subject=subject,
        ))
    if action == "revision":
        return stream_response(notes.revision_notes(
            topic=payload["topic"], doc_ids=doc_ids, current_subject=subject,
        ))
    abort(404)


# ── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "127.0.0.1")
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print(f"\n  NZ Law Assistant -> http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
