from typing import Generator, Optional

import config
from src.prompts import CASE_ANALYSIS_PROMPT
from src.rag_pipeline import RAGPipeline
from src.vector_store import RetrievedChunk


class CaseAnalyzer:
    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def analyse_full_case(
        self,
        doc_id: str,
        collection_name: str,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self.pipeline.retrieve_full_document(doc_id, collection_name)
        query = (
            "Provide a full structured analysis of this case including: Case Summary, Issues, "
            "Rule/Ratio Decidendi, Application, Conclusion, Obiter Dicta, Precedent Value, "
            "and Critical Commentary. Use the IRAC framework and NZ Law Style Guide citations."
        )
        return self.pipeline.stream(
            system_prompt=CASE_ANALYSIS_PROMPT,
            user_query=query,
            mode="case",
            chunks=chunks,
            current_subject=current_subject,
        )

    def extract_ratio(
        self,
        doc_id: str,
        collection_name: str,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self.pipeline.retrieve_full_document(doc_id, collection_name)
        query = (
            "Identify and extract the ratio decidendi of this case. "
            "State it precisely as a legal principle. Distinguish it from any obiter dicta. "
            "Explain its binding effect in the NZ court hierarchy."
        )
        return self.pipeline.stream(
            system_prompt=CASE_ANALYSIS_PROMPT,
            user_query=query,
            mode="case",
            chunks=chunks,
            current_subject=current_subject,
        )

    def compare_cases(
        self,
        doc_ids: list[str],
        collection_name: str,
        comparison_question: str,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        all_chunks: list[RetrievedChunk] = []
        for doc_id in doc_ids:
            all_chunks.extend(
                self.pipeline.retrieve_full_document(doc_id, collection_name)
            )
        query = (
            f"Compare and contrast these cases in relation to: {comparison_question}\n\n"
            "For each case, identify the ratio and how it treats the issue. "
            "Explain how they agree, differ, or develop the law. "
            "Identify which is binding in NZ and what the combined effect is."
        )
        return self.pipeline.stream(
            system_prompt=CASE_ANALYSIS_PROMPT,
            user_query=query,
            mode="case",
            chunks=all_chunks,
            current_subject=current_subject,
        )

    def chat_about_case(
        self,
        user_message: str,
        doc_id: str,
        collection_name: str,
        history: list[dict],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self.pipeline.retrieve_full_document(doc_id, collection_name)
        return self.pipeline.stream(
            system_prompt=CASE_ANALYSIS_PROMPT,
            user_query=user_message,
            mode="case",
            chunks=chunks,
            history=history,
            current_subject=current_subject,
        )

    def explain_principle(
        self,
        principle: str,
        doc_ids: Optional[list[str]],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Explain the legal principle of '{principle}'. "
            "Use the uploaded cases and materials as authority. "
            "Structure your explanation: what the principle is, where it comes from, "
            "how courts have applied it, and its significance in NZ law."
        )
        return self.pipeline.stream(
            system_prompt=CASE_ANALYSIS_PROMPT,
            user_query=query,
            mode="case",
            doc_ids=doc_ids,
            current_subject=current_subject,
        )
