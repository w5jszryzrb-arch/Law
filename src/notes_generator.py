from typing import Generator, Optional

from src.prompts import NOTES_PROMPT
from src.rag_pipeline import RAGPipeline


class NotesGenerator:
    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def lecture_notes(
        self,
        topic: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Generate comprehensive lecture notes on the topic: '{topic}'.\n\n"
            f"Structure the notes with:\n"
            f"## [Main Topic Heading]\n"
            f"### [Sub-topic]\n"
            f"- Key principle or definition\n"
            f"- Case authority (*Case Name* [year] citation) — facts and ratio\n"
            f"- Statutory basis if applicable\n\n"
            f"Use all relevant uploaded lecture slides, transcripts, and course materials. "
            f"Include every important case and principle from the materials."
        )
        return self.pipeline.stream(
            system_prompt=NOTES_PROMPT,
            user_query=query,
            mode="notes",
            doc_ids=doc_ids,
            current_subject=current_subject,
            n_results=10,
        )

    def case_summary_table(
        self,
        doc_ids: list[str],
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            "Generate a comprehensive case summary table for all the uploaded cases.\n\n"
            "Format as a Markdown table with these columns:\n"
            "| Case Name | Court & Year | Key Facts | Ratio Decidendi | Significance |\n\n"
            "Include every case from the uploaded materials. "
            "Use NZ Law Style Guide citation format for case names. "
            "Keep each cell concise but accurate."
        )
        return self.pipeline.stream(
            system_prompt=NOTES_PROMPT,
            user_query=query,
            mode="notes",
            doc_ids=doc_ids,
            current_subject=current_subject,
            n_results=12,
        )

    def topic_overview(
        self,
        topic: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Create a comprehensive topic overview for: '{topic}'.\n\n"
            f"Synthesise all uploaded materials (lectures, cases, articles) to cover:\n"
            f"1. Introduction — what is this area of law and why does it matter?\n"
            f"2. Core principles — the foundational rules and their sources\n"
            f"3. Leading cases — key NZ (and persuasive) cases with ratios\n"
            f"4. Statutory framework — relevant NZ legislation\n"
            f"5. Academic commentary — key debates and criticisms\n"
            f"6. Current state of the law — is anything unsettled or developing?\n"
            f"7. Exam focus — what aspects are most likely to be tested?\n\n"
            f"Write in detailed academic prose with inline citations in NZ style."
        )
        return self.pipeline.stream(
            system_prompt=NOTES_PROMPT,
            user_query=query,
            mode="notes",
            doc_ids=doc_ids,
            current_subject=current_subject,
            n_results=12,
        )

    def revision_notes(
        self,
        topic: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Create concise revision notes for '{topic}' focused on exam performance.\n\n"
            f"Include:\n"
            f"- The key legal test or principle (one-sentence version)\n"
            f"- The top 3–5 cases to know (name, ratio, when to use)\n"
            f"- Any key statute sections\n"
            f"- Common exam traps or nuances\n"
            f"- A quick IRAC template for problem questions on this topic\n\n"
            f"Be concise — this is for last-minute revision. Use bullet points and bold headings."
        )
        return self.pipeline.stream(
            system_prompt=NOTES_PROMPT,
            user_query=query,
            mode="notes",
            doc_ids=doc_ids,
            current_subject=current_subject,
            n_results=8,
        )
