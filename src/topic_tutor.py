from typing import Generator, Optional

import config
from src.prompts import LEARN_MODE_PROMPT, PRACTICE_SESSION_PROMPT
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
