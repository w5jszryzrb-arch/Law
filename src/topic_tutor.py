from typing import Generator, Optional

import config
from src.prompts import (
    ASSIGNMENT_SESSION_PROMPT,
    EXAM_SESSION_PROMPT,
    LEARN_MODE_PROMPT,
    PRACTICE_SESSION_PROMPT,
)
from src.rag_pipeline import RAGPipeline
from src.vector_store import RetrievedChunk


class TopicTutor:
    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def _get_topic_chunks(
        self,
        query: str,
        doc_ids: list[str],
        n_results: int = 10,
    ) -> list[RetrievedChunk]:
        """Retrieve chunks from the specific documents assigned to this topic."""
        if not doc_ids:
            return []
        # Use all collections so any doc type assigned to the topic is searchable
        all_collections = list(config.COLLECTIONS.values())
        all_chunks: list[RetrievedChunk] = []
        seen: set[str] = set()
        for doc_id in doc_ids:
            chunks = self.pipeline.vs.query(
                query_text=query,
                collection_names=all_collections,
                n_results=n_results,
                doc_id_filter=doc_id,
            )
            for c in chunks:
                key = f"{c.doc_id}_{c.chunk_index}"
                if key not in seen:
                    seen.add(key)
                    all_chunks.append(c)
        # Re-rank by score, keep top n_results
        return sorted(all_chunks, key=lambda c: c.score, reverse=True)[:n_results]

    # ── Learn mode ──────────────────────────────────────────────────────────

    def start_learn(
        self,
        topic_name: str,
        doc_ids: list[str],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Begin teaching the topic '{topic_name}'. "
            "Start with an engaging overview of what this area of law is, why it matters "
            "in New Zealand, and the structure of concepts you will cover. "
            "Then introduce the first foundational concept from the materials."
        )
        chunks = self._get_topic_chunks(query, doc_ids, n_results=12)
        return self.pipeline.claude.stream(
            system_prompt=LEARN_MODE_PROMPT,
            user_query=query,
            history=[],
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
        )

    def learn_chat(
        self,
        message: str,
        history: list[dict],
        topic_name: str,
        doc_ids: list[str],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self._get_topic_chunks(message, doc_ids, n_results=10)
        return self.pipeline.claude.stream(
            system_prompt=LEARN_MODE_PROMPT,
            user_query=message,
            history=history,
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
        )

    # ── Practice mode ────────────────────────────────────────────────────────

    def start_practice(
        self,
        topic_name: str,
        doc_ids: list[str],
        preferences: str = "",
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        prefs = f"\n\nStudent preferences: {preferences}" if preferences.strip() else ""
        query = (
            f"Start a practice session on the topic '{topic_name}'. "
            "Generate the first exam practice question based ONLY on the uploaded course materials. "
            "If past exam papers or marked scripts are in the materials, match their style and format. "
            "Label the question with its type, estimated time, and marks."
            f"{prefs}"
        )
        chunks = self._get_topic_chunks(query, doc_ids, n_results=12)
        return self.pipeline.claude.stream(
            system_prompt=PRACTICE_SESSION_PROMPT,
            user_query=query,
            history=[],
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
        )

    def practice_chat(
        self,
        message: str,
        history: list[dict],
        topic_name: str,
        doc_ids: list[str],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self._get_topic_chunks(message, doc_ids, n_results=10)
        return self.pipeline.claude.stream(
            system_prompt=PRACTICE_SESSION_PROMPT,
            user_query=message,
            history=history,
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
        )

    # ── Assignment mode ──────────────────────────────────────────────────────

    def _build_assignment_context(self, brief: str, rubric: str, word_limit: int) -> str:
        parts = []
        if brief.strip():
            parts.append(f"Assignment Brief:\n{brief.strip()}")
        if rubric.strip():
            parts.append(f"Marking Rubric:\n{rubric.strip()}")
        if word_limit:
            parts.append(f"Word Limit: {word_limit} words")
        return "\n\n".join(parts)

    def start_assignment(
        self,
        topic_name: str,
        doc_ids: list[str],
        brief: str = "",
        rubric: str = "",
        word_limit: int = 0,
        extra_doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        all_ids = list(doc_ids) + (extra_doc_ids or [])
        if brief.strip():
            query = (
                f"Begin an assignment coaching session on '{topic_name}'. "
                "Read the assignment brief and rubric carefully. "
                "Identify all legal issues to address, explain what a top-mark answer looks like "
                "based on the rubric, and propose an essay plan with issue headings and key authorities."
            )
        else:
            query = (
                f"Begin an assignment coaching session on '{topic_name}'. "
                "No assignment brief has been provided yet. "
                "Introduce yourself as the assignment coach and ask the student to paste their question."
            )
        chunks = self._get_topic_chunks(query, all_ids, n_results=12)
        extra_ctx = self._build_assignment_context(brief, rubric, word_limit)
        return self.pipeline.claude.stream(
            system_prompt=ASSIGNMENT_SESSION_PROMPT,
            user_query=query,
            history=[],
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
            rubric=extra_ctx,
        )

    def assignment_chat(
        self,
        message: str,
        history: list[dict],
        topic_name: str,
        doc_ids: list[str],
        brief: str = "",
        rubric: str = "",
        word_limit: int = 0,
        extra_doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        all_ids = list(doc_ids) + (extra_doc_ids or [])
        chunks = self._get_topic_chunks(message, all_ids, n_results=10)
        extra_ctx = self._build_assignment_context(brief, rubric, word_limit)
        return self.pipeline.claude.stream(
            system_prompt=ASSIGNMENT_SESSION_PROMPT,
            user_query=message,
            history=history,
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
            rubric=extra_ctx,
        )

    # ── Exam session mode ────────────────────────────────────────────────────

    def _build_exam_context(self, instructions: str, mark_scheme: str, time_per_question: int) -> str:
        parts = []
        if instructions.strip():
            parts.append(f"Exam Instructions:\n{instructions.strip()}")
        if mark_scheme.strip():
            parts.append(f"Mark Scheme:\n{mark_scheme.strip()}")
        if time_per_question:
            parts.append(f"Time per question: {time_per_question} minutes")
        return "\n\n".join(parts)

    def start_exam_session(
        self,
        topic_name: str,
        doc_ids: list[str],
        instructions: str = "",
        mark_scheme: str = "",
        time_per_question: int = 0,
        extra_doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        all_ids = list(doc_ids) + (extra_doc_ids or [])
        query = (
            f"Begin a simulated exam session on '{topic_name}'. "
            "Confirm the exam conditions with the student, then generate the first practice exam "
            "question based ONLY on the uploaded course materials, matching the exam format provided."
        )
        chunks = self._get_topic_chunks(query, all_ids, n_results=12)
        extra_ctx = self._build_exam_context(instructions, mark_scheme, time_per_question)
        return self.pipeline.claude.stream(
            system_prompt=EXAM_SESSION_PROMPT,
            user_query=query,
            history=[],
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
            rubric=extra_ctx,
        )

    def exam_session_chat(
        self,
        message: str,
        history: list[dict],
        topic_name: str,
        doc_ids: list[str],
        instructions: str = "",
        mark_scheme: str = "",
        time_per_question: int = 0,
        extra_doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        all_ids = list(doc_ids) + (extra_doc_ids or [])
        chunks = self._get_topic_chunks(message, all_ids, n_results=10)
        extra_ctx = self._build_exam_context(instructions, mark_scheme, time_per_question)
        return self.pipeline.claude.stream(
            system_prompt=EXAM_SESSION_PROMPT,
            user_query=message,
            history=history,
            chunks=chunks,
            current_subject=f"Topic: {topic_name}" + (f" | {current_subject}" if current_subject else ""),
            rubric=extra_ctx,
        )
