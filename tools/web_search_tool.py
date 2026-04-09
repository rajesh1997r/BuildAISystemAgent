"""
Web Search Tool
===============
Uses DuckDuckGo (via duckduckgo-search) to fetch recent content
trends and references for a given query.

Falls back to curated mock results when the network is unavailable
so the pipeline can still run in offline / test mode.
"""
import os
from typing import Optional, Type

try:
    from crewai.tools import BaseTool
except ImportError:
    # Minimal stub so module is importable without crewai installed
    class BaseTool:  # type: ignore
        name: str = ""
        description: str = ""
        def _run(self, *args, **kwargs): ...

from pydantic import BaseModel, Field

# Optional dependency – the tool degrades gracefully without it
try:
    from duckduckgo_search import DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    _DDGS_AVAILABLE = False


# ------------------------------------------------------------------ #
# Input schema
# ------------------------------------------------------------------ #

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query string.")
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of results to return (1–10).",
    )


# ------------------------------------------------------------------ #
# Tool
# ------------------------------------------------------------------ #

class WebSearchTool(BaseTool):
    """
    Search the web for recent articles, statistics, and trend data.

    Returns a formatted text block with titles and short snippets.
    Falls back to representative mock results when DuckDuckGo is
    unavailable.
    """

    name: str = "Web Search Tool"
    description: str = (
        "Search the web for up-to-date information, trends, statistics, "
        "and references on a given topic. "
        "Input: query string. Output: numbered list of titles + snippets."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute the search and return formatted results."""
        # ---- Input validation ------------------------------------------------
        if not query or not query.strip():
            return "Error: Search query cannot be empty."

        query = query.strip()

        # ---- Attempt live search --------------------------------------------
        try:
            if _DDGS_AVAILABLE:
                return self._ddg_search(query, max_results)
            return self._mock_search(query)
        except Exception as exc:
            # Graceful degradation
            fallback = self._mock_search(query)
            return (
                f"⚠  Live search unavailable ({exc}). "
                f"Using cached representative results.\n\n{fallback}"
            )

    # ------------------------------------------------------------------ #
    # Backends
    # ------------------------------------------------------------------ #

    def _ddg_search(self, query: str, max_results: int) -> str:
        """Perform a real DuckDuckGo text search."""
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))

        if not raw:
            return f"No results found for: '{query}'."

        lines = [f"Search Results for: '{query}'", "=" * 50]
        for i, item in enumerate(raw, start=1):
            title   = item.get("title", "No title")
            snippet = item.get("body", "No description")[:250]
            lines += [f"\n{i}. {title}", f"   {snippet}..."]

        return "\n".join(lines)

    def _mock_search(self, query: str) -> str:
        """Return representative placeholder results for offline mode."""
        return (
            f"Search Results for: '{query}' [offline / cached]\n"
            + "=" * 50 + "\n"
            f"\n1. The Complete Guide to {query}\n"
            f"   Experts say {query} is one of the fastest-growing fields, "
            "with new developments emerging every month. Key areas include…\n"
            f"\n2. Top 10 Trends in {query} for 2025\n"
            "   Industry analysts highlight automation, personalization, and "
            f"sustainability as the top drivers shaping {query} this year…\n"
            f"\n3. Why {query} Matters for the Future\n"
            f"   Recent surveys show that 78 % of professionals consider {query} "
            "critical to their industry's growth over the next five years…\n"
            f"\n4. Beginner's Roadmap to {query}\n"
            "   A step-by-step overview covering foundational concepts, "
            "tools, and real-world applications…\n"
            f"\n5. Common Mistakes in {query} — and How to Avoid Them\n"
            "   Practitioners share the pitfalls they wish they'd known "
            "about earlier in their journey…\n"
        )
