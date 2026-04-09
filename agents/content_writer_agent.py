"""
Content Writer Agent
====================
Converts the selected content idea into a full, structured article.

Expected output structure:
  # Title
  ## Introduction
  ## Section 1  ...  ## Section N
  ## Conclusion

Tools used:
  - WebSearchTool       : gather supporting facts / statistics
  - OutputFormatterTool : emit clean Markdown
"""
from crewai import Agent
from tools.web_search_tool import WebSearchTool
from tools.output_formatter_tool import OutputFormatterTool


def create_content_writer_agent(llm=None) -> Agent:
    """
    Build and return the Content Writer Agent.

    Args:
        llm: Optional LLM override.

    Returns:
        Configured CrewAI Agent instance.
    """
    tools = [WebSearchTool(), OutputFormatterTool()]

    kwargs = dict(
        role="Professional Content Writer",
        goal=(
            "Transform the selected content idea into a fully structured, "
            "informative, and engaging article. "
            "Produce clean Markdown with a title, introduction, "
            "at least three body sections with headings, and a conclusion. "
            "Total length should be 400-700 words."
        ),
        backstory=(
            "You are a seasoned content writer and journalist who has "
            "authored hundreds of well-researched articles for top-tier "
            "publications. You excel at translating complex ideas into clear, "
            "compelling narratives. Your writing is always fact-checked, "
            "logically structured, and tailored to the target audience. "
            "You believe a great article teaches something new AND tells a story."
        ),
        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=2,
    )

    if llm:
        kwargs["llm"] = llm

    return Agent(**kwargs)
