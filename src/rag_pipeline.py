from typing import Generator, Optional

import config
from src.claude_client import ClaudeClient, UsageStats
from src.vector_store import LegalVectorStore, RetrievedChunk


class RAGPipeline:
    def __init__(self, vector_store: LegalVectorStore, claude_client: ClaudeClient) -> None:
        self.vs = vector_store
        self.claude = claude_client

    def _collections_for_mode(self, mode: str) -> list[str]:
        if mode == "exam":
            return [config.COLLECTIONS["case_law"], config.COLLECTIONS["lecture"],
                    config.COLLECTIONS["statute"], config.COLLECTIONS["article"],
                    config.COLLECTIONS["past_paper"], config.COLLECTIONS["workshop_question"],
                    config.COLLECTIONS["instruction"]]
        if mode == "case":
            return [config.COLLECTIONS["case_law"], config.COLLECTIONS["article"]]
        if mode == "notes":
            return list(config.COLLECTIONS.values())
        # essay and general: all collections
        return list(config.COLLECTIONS.values())

    def retrieve(
        self,
        query: str,
        mode: str = "general",
        doc_ids: Optional[list[str]] = None,
        n_results: int = config.TOP_K_RETRIEVAL,
    ) -> list[RetrievedChunk]:
        collections = self._collections_for_mode(mode)
        all_chunks: list[RetrievedChunk] = []

        if doc_ids:
            for doc_id in doc_ids:
                for col in collections:
                    chunks = self.vs.query(
                        query_text=query,
                        collection_names=[col],
                        n_results=n_results,
                        doc_id_filter=doc_id,
                    )
                    all_chunks.extend(chunks)
            # Re-rank and deduplicate
            seen: set[str] = set()
            unique: list[RetrievedChunk] = []
            for c in sorted(all_chunks, key=lambda x: x.score, reverse=True):
                k = f"{c.doc_id}_{c.chunk_index}"
                if k not in seen:
                    seen.add(k)
                    unique.append(c)
            return unique[:n_results]

        return self.vs.query(
            query_text=query,
            collection_names=collections,
            n_results=n_results,
        )

    def retrieve_full_document(self, doc_id: str, collection_name: str) -> list[RetrievedChunk]:
        return self.vs.get_all_chunks_for_doc(doc_id, collection_name)

    def stream(
        self,
        system_prompt: str,
        user_query: str,
        mode: str = "general",
        doc_ids: Optional[list[str]] = None,
        history: Optional[list[dict]] = None,
        current_subject: str = "",
        rubric: str = "",
        n_results: int = config.TOP_K_RETRIEVAL,
        chunks: Optional[list[RetrievedChunk]] = None,
    ) -> Generator[str, None, UsageStats]:
        if chunks is None:
            chunks = self.retrieve(query=user_query, mode=mode, doc_ids=doc_ids, n_results=n_results)
        return self.claude.stream(
            system_prompt=system_prompt,
            user_query=user_query,
            history=history or [],
            chunks=chunks,
            current_subject=current_subject,
            rubric=rubric,
        )

    def complete(
        self,
        system_prompt: str,
        user_query: str,
        mode: str = "general",
        doc_ids: Optional[list[str]] = None,
        history: Optional[list[dict]] = None,
        current_subject: str = "",
        rubric: str = "",
        n_results: int = config.TOP_K_RETRIEVAL,
        chunks: Optional[list[RetrievedChunk]] = None,
    ) -> tuple[str, UsageStats]:
        if chunks is None:
            chunks = self.retrieve(query=user_query, mode=mode, doc_ids=doc_ids, n_results=n_results)
        return self.claude.complete(
            system_prompt=system_prompt,
            user_query=user_query,
            history=history or [],
            chunks=chunks,
            current_subject=current_subject,
            rubric=rubric,
        )
