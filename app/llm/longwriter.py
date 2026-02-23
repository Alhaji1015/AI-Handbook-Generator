from dataclasses import dataclass
from typing import List, Callable, Optional, Dict
import re

from .gemini_client import GeminiClient
from .prompts import HANDBOOK_PLANNER, SECTION_WRITER


@dataclass
class SourceChunk:
    doc_name: str
    chunk_index: int
    content: str


def format_sources(chunks: List[SourceChunk], limit_chars: int = 12000) -> str:
    out = []
    total = 0
    for ch in chunks:
        block = f"[Doc: {ch.doc_name}, Chunk: {ch.chunk_index}]\n{ch.content}\n"
        if total + len(block) > limit_chars:
            break
        out.append(block)
        total += len(block)
    return "\n---\n".join(out)


def _extract_section_titles(outline_md: str) -> List[str]:
    """
    Extract section titles from markdown-ish outline.
    Supports:
      - "1. Chapter Title"
      - "1.1 Subsection Title"
      - "- Chapter Title"
      - "## Chapter Title"
    Returns a linear list of titles in order.
    """
    titles: List[str] = []
    for line in outline_md.splitlines():
        s = line.strip()
        if not s:
            continue

        # Markdown headings
        if s.startswith("#"):
            t = s.lstrip("#").strip()
            if len(t) > 3:
                titles.append(t)
            continue

        # Numbered sections: "1." "1.1" "2.3.1"
        m = re.match(r"^(\d+(\.\d+)*)(\)|\.)\s+(.*)$", s)
        if m:
            t = m.group(4).strip()
            if len(t) > 3:
                titles.append(t)
            continue

        # Bullets
        if s.startswith(("-", "*")):
            t = s.lstrip("-* ").strip()
            if len(t) > 3:
                titles.append(t)
            continue

    # Dedup while preserving order
    seen = set()
    ordered = []
    for t in titles:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(t)
    return ordered


class LongWriter:
    def __init__(self):
        self.llm = GeminiClient()

    def make_outline(self, topic: str, sources_text: str) -> str:
        messages = [
            {"role": "system", "content": "You are an expert technical writer."},
            {
                "role": "user",
                "content": f"{HANDBOOK_PLANNER}\n\nTopic: {topic}\n\nSources:\n{sources_text}\n\nOutput Markdown."
            },
        ]
        return self.llm.chat(messages, temperature=0.2, max_tokens=1800)

    def generate_handbook(
        self,
        topic: str,
        initial_sources_text: str,
        retrieve_sources_for_section: Callable[[str, int], str],
        target_words: int = 20000,
        section_token_budget: int = 3500,
        per_section_k: int = 25,
    ) -> str:
        """
        Deterministic long generation:
        - Build outline once using initial_sources_text
        - Parse outline into ordered section titles
        - For each title, retrieve fresh sources and write that section
        """

        outline = self.make_outline(topic, initial_sources_text)
        section_titles = _extract_section_titles(outline)

        handbook_parts: List[str] = []
        handbook_parts.append(f"# Handbook: {topic}\n\n")
        handbook_parts.append("## Table of Contents + Plan\n\n")
        handbook_parts.append(outline)
        handbook_parts.append("\n\n---\n\n")

        current_words = len(" ".join(handbook_parts).split())
        rolling_tail = ""

        # If parsing fails, fall back to a generic list of sections
        if not section_titles:
            section_titles = [
                "Introduction",
                "Core Concepts",
                "Architecture & Components",
                "Implementation Guide",
                "Evaluation & Monitoring",
                "Governance, Risk & Compliance",
                "Operationalization & MLOps",
                "Common Failure Modes",
                "Case Studies",
                "Conclusion",
            ]

        for i, title in enumerate(section_titles, start=1):
            if current_words >= target_words:
                break

            # Retrieve section-specific sources (this improves citations massively)
            sources_text = retrieve_sources_for_section(title, per_section_k)

            prompt = (
                f"{SECTION_WRITER}\n\n"
                f"Topic: {topic}\n\n"
                f"Table of contents + plan:\n{outline}\n\n"
                f"Current section to write: {title}\n\n"
                f"Previously written tail (for continuity):\n{rolling_tail[-4000:]}\n\n"
                f"Sources:\n{sources_text}\n\n"
                f"Write ONLY the section '{title}' now."
            )

            messages = [
                {"role": "system", "content": "You are an expert long-form author. Write clean Markdown."},
                {"role": "user", "content": prompt},
            ]

            section = self.llm.chat(messages,temperature=0.25,max_tokens=section_token_budget
)

            # Guard against None or empty responses
            if not section:
                section = "⚠️ Model returned empty output for this section."

            section = section.strip()

            if not section:
                section = "⚠️ Model failed to generate content for this section."

            # Guard: if model returns tiny content, force it to expand once
            if not section or len(section.split()) < 250:
                repair_prompt = (
                    f"The section you wrote is too short. Expand '{title}' with practical detail, "
                    f"steps, examples, and checklists. Keep citations.\n\n"
                    f"Sources:\n{sources_text}"
                )
                section = self.llm.chat(
                    [{"role": "system", "content": "Expand the section with detail."},
                     {"role": "user", "content": repair_prompt}],
                    temperature=0.25,
                    max_tokens=section_token_budget,
                )

            handbook_parts.append(f"## {title}\n\n")
            handbook_parts.append(section.strip())
            handbook_parts.append("\n\n---\n\n")

            rolling_tail = (rolling_tail + "\n" + section)[-12000:]
            current_words += len(section.split())

        # If still under target, keep adding an appendix loop
        appendix_round = 1
        while current_words < target_words:
            title = f"Appendix {appendix_round}: Practical Templates and Checklists"
            sources_text = retrieve_sources_for_section("templates checklists examples", per_section_k)

            prompt = (
                f"{SECTION_WRITER}\n\n"
                f"Topic: {topic}\n\n"
                f"Current section to write: {title}\n\n"
                f"Previously written tail:\n{rolling_tail[-4000:]}\n\n"
                f"Sources:\n{sources_text}\n\n"
                f"Add new material (no repetition)."
            )

            section = self.llm.chat(
                [{"role": "system", "content": "Write clean Markdown, very practical."},
                 {"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=section_token_budget,
            )

            handbook_parts.append(f"## {title}\n\n")
            handbook_parts.append(section.strip())
            handbook_parts.append("\n\n---\n\n")

            rolling_tail = (rolling_tail + "\n" + section)[-12000:]
            current_words += len(section.split())
            appendix_round += 1

            if appendix_round > 30:  # safety stop
                break

        return "".join(handbook_parts)