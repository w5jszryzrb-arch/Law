from typing import Generator, Optional

from src.prompts import ESSAY_PROMPT
from src.rag_pipeline import RAGPipeline


class EssayAssistant:
    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def analyse_question(
        self,
        question: str,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Analyse this essay/exam question and identify:\n"
            f"1. All legal issues raised\n"
            f"2. The relevant area(s) of NZ law\n"
            f"3. Key cases and statutes likely to be relevant\n"
            f"4. The analytical approach required\n"
            f"5. How to structure the answer to maximise marks\n\n"
            f"Question: {question}"
        )
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=query,
            mode="essay",
            doc_ids=doc_ids,
            current_subject=current_subject,
            rubric=rubric,
        )

    def generate_plan(
        self,
        question: str,
        word_limit: int = 1500,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        rubric_note = (
            "\nThe assessment rubric has been provided — structure the plan to satisfy the highest grade band criteria."
            if rubric.strip() else ""
        )
        query = (
            f"Generate a detailed essay plan for the following question.\n\n"
            f"Question: {question}\n\n"
            f"Word limit: {word_limit} words{rubric_note}\n\n"
            f"The plan should include:\n"
            f"- A numbered outline with section headings\n"
            f"- The key legal issue addressed in each section\n"
            f"- The primary authority (case/statute) for each section\n"
            f"- Approximate word count per section\n"
            f"- Any counter-arguments to address\n\n"
            f"Use the uploaded materials as sources for authority."
        )
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=query,
            mode="essay",
            doc_ids=doc_ids,
            current_subject=current_subject,
            rubric=rubric,
        )

    def draft_essay(
        self,
        question: str,
        plan: str,
        word_limit: int = 1500,
        doc_ids: Optional[list[str]] = None,
        history: Optional[list[dict]] = None,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        rubric_note = (
            "\n- Align the essay to satisfy the highest grade band criteria in the provided rubric"
            if rubric.strip() else ""
        )
        query = (
            f"Write a full essay draft based on the following question and plan.\n\n"
            f"Question: {question}\n\n"
            f"Essay Plan:\n{plan}\n\n"
            f"Requirements:\n"
            f"- Target {word_limit} words\n"
            f"- Formal academic prose throughout (no bullet points in body)\n"
            f"- Apply IRAC to each legal issue\n"
            f"- Cite all cases and statutes using NZ Law Style Guide format\n"
            f"- Italicise case names in body text\n"
            f"- Include footnotes for citations\n"
            f"- Use only the uploaded course materials as authority{rubric_note}"
        )
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=query,
            mode="essay",
            doc_ids=doc_ids,
            history=history or [],
            current_subject=current_subject,
            rubric=rubric,
            n_results=8,
        )

    def critique_essay(
        self,
        question: str,
        essay_text: str,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        rubric_note = (
            "\n6. **Rubric alignment** — assess against each criterion in the provided rubric and indicate the grade band achieved"
            if rubric.strip()
            else "\n6. **Overall grade band** (A+/A/B+/B/C) with justification"
        )
        query = (
            f"Critique the following essay in response to this question.\n\n"
            f"Question: {question}\n\n"
            f"Essay:\n{essay_text}\n\n"
            f"Assess:\n"
            f"1. **Structure** — does it follow IRAC? Is the flow logical?\n"
            f"2. **Use of authority** — are cases cited correctly in NZ style? Are the right cases used?\n"
            f"3. **Argument strength** — are arguments well-developed and supported?\n"
            f"4. **Counter-arguments** — are they addressed?\n"
            f"5. **Citation accuracy** — are citations in NZ Law Style Guide format?"
            f"{rubric_note}\n"
            f"7. **Three specific improvements** to make"
        )
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=query,
            mode="essay",
            current_subject=current_subject,
            rubric=rubric,
        )

    def improve_argument(
        self,
        argument_text: str,
        feedback: str,
        history: Optional[list[dict]] = None,
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        query = (
            f"Improve the following legal argument based on the feedback provided.\n\n"
            f"Original argument:\n{argument_text}\n\n"
            f"Feedback:\n{feedback}\n\n"
            f"Rewrite the argument to address the feedback. "
            f"Maintain formal academic prose and NZ citation style."
        )
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=query,
            mode="essay",
            doc_ids=doc_ids,
            history=history or [],
            current_subject=current_subject,
            rubric=rubric,
        )

    def chat(
        self,
        message: str,
        history: list[dict],
        doc_ids: Optional[list[str]] = None,
        current_subject: str = "",
        rubric: str = "",
    ) -> Generator[str, None, None]:
        return self.pipeline.stream(
            system_prompt=ESSAY_PROMPT,
            user_query=message,
            mode="essay",
            doc_ids=doc_ids,
            history=history,
            current_subject=current_subject,
            rubric=rubric,
        )
