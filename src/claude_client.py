import os
from dataclasses import dataclass
from typing import Generator, Optional

import anthropic
from dotenv import load_dotenv

import config
from src.vector_store import RetrievedChunk

load_dotenv()


@dataclass
class UsageStats:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def cache_savings_pct(self) -> float:
        total = self.input_tokens + self.cache_read_tokens
        if total == 0:
            return 0.0
        return round(self.cache_read_tokens / total * 100, 1)


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks as a deterministic context block."""
    # Sort deterministically so caching is never invalidated by ordering
    sorted_chunks = sorted(chunks, key=lambda c: (c.source_filename, c.chunk_index))
    parts: list[str] = []
    for c in sorted_chunks:
        header = f"[Source: {c.title} | Type: {c.doc_type} | Chunk {c.chunk_index}]"
        parts.append(f"{header}\n{c.text}")
    return "\n\n---\n\n".join(parts)


def _build_messages(
    history: list[dict],
    chunks: list[RetrievedChunk],
    user_query: str,
    current_subject: str = "",
) -> list[dict]:
    messages = list(history)

    subject_prefix = f"[Subject: {current_subject}]\n\n" if current_subject.strip() else ""

    if chunks:
        context_text = _format_chunks(chunks)
        user_content = [
            {
                "type": "text",
                "text": f"## Uploaded Course Materials (use as primary source)\n\n{context_text}",
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"{subject_prefix}{user_query}",
            },
        ]
    else:
        user_content = [
            {
                "type": "text",
                "text": f"{subject_prefix}{user_query}",
            }
        ]

    messages.append({"role": "user", "content": user_content})
    return messages


def _system_block(system_prompt: str) -> list[dict]:
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


class ClaudeClient:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self._client = anthropic.Anthropic(api_key=api_key)

    def stream(
        self,
        system_prompt: str,
        user_query: str,
        history: Optional[list[dict]] = None,
        chunks: Optional[list[RetrievedChunk]] = None,
        current_subject: str = "",
        max_tokens: int = config.MAX_TOKENS,
    ) -> Generator[str, None, UsageStats]:
        messages = _build_messages(
            history or [],
            chunks or [],
            user_query,
            current_subject,
        )
        stats = UsageStats()

        with self._client.messages.stream(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=_system_block(system_prompt),
            messages=messages,
        ) as s:
            for text in s.text_stream:
                yield text
            final = s.get_final_message()
            u = final.usage
            stats.input_tokens = u.input_tokens
            stats.output_tokens = u.output_tokens
            stats.cache_creation_tokens = getattr(u, "cache_creation_input_tokens", 0) or 0
            stats.cache_read_tokens = getattr(u, "cache_read_input_tokens", 0) or 0

        return stats

    def complete(
        self,
        system_prompt: str,
        user_query: str,
        history: Optional[list[dict]] = None,
        chunks: Optional[list[RetrievedChunk]] = None,
        current_subject: str = "",
        max_tokens: int = config.MAX_TOKENS,
    ) -> tuple[str, UsageStats]:
        messages = _build_messages(
            history or [],
            chunks or [],
            user_query,
            current_subject,
        )
        resp = self._client.messages.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=_system_block(system_prompt),
            messages=messages,
        )
        u = resp.usage
        stats = UsageStats(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_creation_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        )
        text = resp.content[0].text if resp.content else ""
        return text, stats
