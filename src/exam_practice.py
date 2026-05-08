from typing import Generator, Optional

import config
from src.prompts import EXAM_PROMPT, PAST_PAPER_ANALYSIS_PROMPT
from src.rag_pipeline import RAGPipeline
from src.vector_store import RetrievedChunk


class ExamPractice:
    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def _get_exam_chunks(self, doc_ids: Optional[list[str]] = None) -> list[RetrievedChunk]:
        """Retrieve all available exam-relevant chunks, including past papers."""
        collections = [
            config.COLLECTIONS["case_law"],
            config.COLLECTIONS["lecture"],
            config.COLLECTIONS["statute"],
            config.COLLECTIONS["article"],
            config.COLLECTIONS["past_paper"],
            config.COLLECTIONS["instruction"],
        ]
        if doc_ids:
            all_chunks: list[RetrievedChunk] = []
            for doc_id in doc_ids:
                chunks = self.pipeline.vs.query(
                    query_text="legal principles cases statutes exam",
                    collection_names=collections,
                    n_results=8,
                    doc_id_filter=doc_id,
                )
                all_chunks.extend(chunks)
            return all_chunks
        return self.pipeline.vs.query(
            query_text="legal principles cases statutes exam",
            collection_names=collections,
            n_results=10,
        )

    def analyse_past_paper(
        self,
        doc_id: str,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        chunks = self.pipeline.retrieve_full_document(
            doc_id, config.COLLECTIONS["past_paper"]
        )
        query = (
            "Analyse this past exam paper. Extract: all topics tested, question types, "
            "mark allocations, time allocations, topic frequency, question style patterns, "
            "and what skills are being assessed. Format as structured markdown."
        )
        return self.pipeline.stream(
            system_prompt=PAST_PAPER_ANALYSIS_PROMPT,
            user_query=query,
            mode="exam",
            chunks=chunks,
            current_subject=current_subject,
        )

    def generate_questions(
        self,
        topic: str,
        question_type: str = "problem_question",
        difficulty: str = "intermediate",
        n_questions: int = 1,
        doc_ids: Optional[list[str]] = None,
        time_minutes: int = 30,
        marks: int = 25,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        type_label = {
            "problem_question": "problem question (scenario-based)",
            "essay_question": "essay question",
            "short_answer": "short answer question",
        }.get(question_type, question_type)

        query = (
            f"Generate {n_questions} {type_label}(s) on the topic: '{topic}'.\n\n"
            f"Difficulty: {difficulty}\n"
            f"Time allocation: {time_minutes} minutes per question\n"
            f"Marks: {marks} marks per question\n\n"
            f"IMPORTANT: Base the question ONLY on the cases, statutes, and principles "
            f"in the uploaded course materials. Do not introduce cases or concepts not in the materials.\n\n"
            f"For each question:\n"
            f"- Label it clearly (e.g. Question 1)\n"
            f"- Include the time and mark allocation\n"
            f"- For problem questions: create a realistic scenario with multiple legal issues\n"
            f"- For essay questions: phrase it to require IRAC analysis\n"
            f"- Note which uploaded materials are relevant to answering it"
        )
        chunks = self._get_exam_chunks(doc_ids)
        return self.pipeline.stream(
            system_prompt=EXAM_PROMPT,
            user_query=query,
            mode="exam",
            chunks=chunks,
            current_subject=current_subject,
        )

    def model_answer(
        self,
        question: str,
        time_minutes: int = 30,
        marks: int = 25,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Write a model answer to the following exam question.\n\n"
            f"Question: {question}\n\n"
            f"Time allowed: {time_minutes} minutes | Marks: {marks}\n\n"
            f"Requirements:\n"
            f"- Use IRAC structure for each legal issue\n"
            f"- Cite ONLY cases and statutes from the uploaded course materials\n"
            f"- Indicate the source for each point (e.g. [from: Lecture 2 slides])\n"
            f"- Calibrate depth and length to the time and marks allocated\n"
            f"- Use NZ Law Style Guide citation format\n"
            f"- Conclude with a clear answer to the question"
        )
        chunks = self._get_exam_chunks(doc_ids)
        return self.pipeline.stream(
            system_prompt=EXAM_PROMPT,
            user_query=query,
            mode="exam",
            chunks=chunks,
            current_subject=current_subject,
        )

    def mark_answer(
        self,
        question: str,
        student_answer: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Mark and provide detailed feedback on this student's exam answer.\n\n"
            f"Question: {question}\n\n"
            f"Student's answer:\n{student_answer}\n\n"
            f"Provide:\n"
            f"1. **What the student got right** — specific correct points with references to course materials\n"
            f"2. **What was missed** — issues/cases/statutes from course materials not addressed\n"
            f"3. **Structural feedback** — IRAC application, argument development\n"
            f"4. **Citation feedback** — NZ Law Style Guide compliance\n"
            f"5. **Grade band** (A+/A/B+/B/C/D) with justification\n"
            f"6. **Three priority improvements** for next time"
        )
        chunks = self._get_exam_chunks(doc_ids)
        return self.pipeline.stream(
            system_prompt=EXAM_PROMPT,
            user_query=query,
            mode="exam",
            chunks=chunks,
            current_subject=current_subject,
        )

    def identify_gaps(
        self,
        topic_area: str,
        student_notes: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Compare the student's notes on '{topic_area}' against the uploaded course materials "
            f"and identify knowledge gaps.\n\n"
            f"Student's notes:\n{student_notes}\n\n"
            f"Identify:\n"
            f"1. Cases in the course materials not mentioned in the student's notes\n"
            f"2. Legal principles covered in lectures not included in the notes\n"
            f"3. Concepts that are present but underdeveloped\n"
            f"4. Priority areas to revise before an exam"
        )
        chunks = self._get_exam_chunks(doc_ids)
        return self.pipeline.stream(
            system_prompt=EXAM_PROMPT,
            user_query=query,
            mode="exam",
            chunks=chunks,
            current_subject=current_subject,
        )
