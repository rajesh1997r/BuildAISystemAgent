"""
Text Processing Tool
====================
Provides four text operations used across the pipeline:

  clean            – normalise whitespace and line endings
  summarize        – extractive three-sentence summary
  format           – fix capitalisation and paragraph spacing
  extract_keywords – top-10 non-stop-word frequencies
"""
import re
from typing import Type

try:
    from crewai.tools import BaseTool
except ImportError:
    class BaseTool:  # type: ignore
        name: str = ""
        description: str = ""
        def _run(self, *args, **kwargs): ...

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Input schema
# ------------------------------------------------------------------ #

class TextProcessingInput(BaseModel):
    text: str = Field(description="The text to process.")
    operation: str = Field(
        default="clean",
        description=(
            "Operation to perform: "
            "'clean' | 'summarize' | 'format' | 'extract_keywords'"
        ),
    )


# ------------------------------------------------------------------ #
# Tool
# ------------------------------------------------------------------ #

class TextProcessingTool(BaseTool):
    """
    Multi-purpose text processing utility.

    Supports cleaning, summarising, formatting, and keyword extraction.
    All operations handle empty / invalid input gracefully.
    """

    name: str = "Text Processing Tool"
    description: str = (
        "Process text using one of four operations: "
        "clean (remove extra whitespace), "
        "summarize (3-sentence extractive summary), "
        "format (fix capitalisation and spacing), or "
        "extract_keywords (top-10 frequent terms). "
        "Specify the 'operation' parameter."
    )
    args_schema: Type[BaseModel] = TextProcessingInput

    _OPERATIONS = ("clean", "summarize", "format", "extract_keywords")

    def _run(self, text: str, operation: str = "clean") -> str:
        """Dispatch to the requested operation."""
        # ---- Validation -------------------------------------------------------
        if not text or not text.strip():
            return "Error: Input text cannot be empty."

        operation = operation.lower().strip()
        if operation not in self._OPERATIONS:
            return (
                f"Unknown operation '{operation}'. "
                f"Available: {', '.join(self._OPERATIONS)}"
            )

        # ---- Dispatch ---------------------------------------------------------
        dispatch = {
            "clean":            self._clean,
            "summarize":        self._summarize,
            "format":           self._format,
            "extract_keywords": self._extract_keywords,
        }
        try:
            return dispatch[operation](text)
        except Exception as exc:
            return f"Processing error in '{operation}': {exc}"

    # ------------------------------------------------------------------ #
    # Operations
    # ------------------------------------------------------------------ #

    def _clean(self, text: str) -> str:
        """Normalise whitespace, tabs, and excessive blank lines."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\t", "  ", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.rstrip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    def _summarize(self, text: str) -> str:
        """Return a three-sentence extractive summary."""
        # Split on sentence-ending punctuation
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text.strip())
            if len(s.split()) > 5
        ]
        if len(sentences) <= 3:
            return "Summary:\n" + text.strip()

        chosen = [
            sentences[0],
            sentences[len(sentences) // 2],
            sentences[-1],
        ]
        return "Summary:\n" + " ".join(chosen)

    def _format(self, text: str) -> str:
        """Capitalise first letter of each paragraph and fix spacing."""
        paragraphs = text.split("\n\n")
        formatted = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # Capitalise first character if it is a lower-case letter
            if para and para[0].islower():
                para = para[0].upper() + para[1:]
            formatted.append(para)
        return "\n\n".join(formatted)

    def _extract_keywords(self, text: str) -> str:
        """Return the top-10 non-stop-word terms by frequency."""
        STOP_WORDS = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "are", "was",
            "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might", "that",
            "this", "these", "those", "it", "its", "we", "our", "you", "your",
            "they", "their", "he", "she", "his", "her", "also", "not", "all",
            "which", "when", "who", "what", "how", "then", "than", "just",
            "more", "about", "can", "each", "into", "its", "been", "other",
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        freq: dict = {}
        for w in words:
            if w not in STOP_WORDS and len(w) > 3:
                freq[w] = freq.get(w, 0) + 1

        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
        if not top:
            return "No significant keywords found."

        kw_list = ", ".join(f"{w} ({c})" for w, c in top)
        return f"Top Keywords: {kw_list}"
