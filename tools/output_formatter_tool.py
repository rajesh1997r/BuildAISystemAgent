"""
Output Formatter Tool
=====================
Converts raw content into clean Markdown, basic HTML, or plain text.

Ensures proper heading hierarchy, paragraph spacing, list formatting,
and a final trailing newline for file-safe output.
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

class OutputFormatterInput(BaseModel):
    content: str = Field(description="The content string to format.")
    format_type: str = Field(
        default="markdown",
        description="Output format: 'markdown' | 'html' | 'plain'",
    )


# ------------------------------------------------------------------ #
# Tool
# ------------------------------------------------------------------ #

class OutputFormatterTool(BaseTool):
    """
    Format content for publication.

    Supported formats:
      markdown – clean, normalised Markdown (default)
      html     – minimal, valid HTML5 document
      plain    – Markdown symbols stripped, plain prose
    """

    name: str = "Output Formatter Tool"
    description: str = (
        "Convert content into clean Markdown, HTML, or plain text. "
        "Use 'markdown' for blog posts, 'html' for web pages, "
        "'plain' for plain-text export. "
        "Defaults to Markdown."
    )
    args_schema: Type[BaseModel] = OutputFormatterInput

    def _run(self, content: str, format_type: str = "markdown") -> str:
        """Format *content* into the requested *format_type*."""
        if not content or not content.strip():
            return "Error: Content cannot be empty."

        format_type = format_type.lower().strip()
        formatters = {
            "markdown": self._to_markdown,
            "html":     self._to_html,
            "plain":    self._to_plain,
        }

        if format_type not in formatters:
            format_type = "markdown"   # safe fallback

        try:
            return formatters[format_type](content)
        except Exception as exc:
            return f"Formatting error: {exc}"

    # ------------------------------------------------------------------ #
    # Formatters
    # ------------------------------------------------------------------ #

    def _to_markdown(self, content: str) -> str:
        """Normalise Markdown: consistent spacing around headings and lists."""
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Ensure blank line before every heading
        content = re.sub(r"(?<!\n)\n(#{1,6}\s)", r"\n\n\1", content)

        # Collapse 3+ blank lines to 2
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Trim trailing spaces per line
        lines = [line.rstrip() for line in content.split("\n")]
        result = "\n".join(lines).strip()
        return result + "\n"

    def _to_html(self, content: str) -> str:
        """Convert Markdown-flavoured content to a minimal HTML5 document."""
        html = content

        # Convert ATX headings (most specific first)
        for level in range(6, 0, -1):
            pattern = r"^" + "#" * level + r"\s+(.+)$"
            html = re.sub(pattern, rf"<h{level}>\1</h{level}>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
        html = re.sub(r"\*\*(.+?)\*\*",      r"<strong>\1</strong>",          html)
        html = re.sub(r"\*(.+?)\*",           r"<em>\1</em>",                  html)

        # Inline code
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # Wrap non-heading / non-empty chunks in <p>
        blocks = html.split("\n\n")
        wrapped = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if re.match(r"<h[1-6]>", block):
                wrapped.append(block)
            elif re.match(r"^[-*•]", block, re.MULTILINE):
                items = re.sub(r"^[-*•]\s+(.+)$", r"  <li>\1</li>", block, flags=re.MULTILINE)
                wrapped.append(f"<ul>\n{items}\n</ul>")
            else:
                wrapped.append(f"<p>{block}</p>")

        body = "\n\n".join(wrapped)
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "</head>\n<body>\n\n"
            + body
            + "\n\n</body>\n</html>\n"
        )

    def _to_plain(self, content: str) -> str:
        """Strip all Markdown syntax and return plain prose."""
        # Remove headings
        content = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
        # Remove bold / italic / bold-italic
        content = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", content)
        # Remove inline code
        content = re.sub(r"`(.+?)`", r"\1", content)
        # Remove links  [text](url)
        content = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", content)
        # Remove horizontal rules
        content = re.sub(r"^[-_*]{3,}\s*$", "", content, flags=re.MULTILINE)
        # Collapse excessive blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()
