"""
Content Editor Agent
====================
Reviews and polishes the drafted article.

Focus areas:
  1. Grammar, spelling, and punctuation
  2. Sentence clarity and conciseness
  3. Consistent, engaging tone
  4. Structural coherence
  5. Reader engagement (opening hook, rhetorical questions, strong CTA)

Tools used:
  - TextProcessingTool  : clean and format text
  - OutputFormatterTool : ensure final Markdown is publication-ready
"""
from crewai import Agent
from tools.text_processing_tool import TextProcessingTool
from tools.output_formatter_tool import OutputFormatterTool
from tools.content_quality_analyzer import ContentQualityAnalyzer


def create_content_editor_agent(llm=None) -> Agent:
    """
    Build and return the Content Editor Agent.

    Args:
        llm: Optional LLM override.

    Returns:
        Configured CrewAI Agent instance.
    """
    tools = [TextProcessingTool(), OutputFormatterTool(), ContentQualityAnalyzer()]

    kwargs = dict(
        role="Expert Content Editor",
        goal=(
            "Thoroughly review and improve the drafted article. "
            "Fix grammar and spelling, sharpen sentence clarity, "
            "enhance engagement through active voice and rhetorical questions, "
            "and ensure the Markdown structure is clean and publication-ready. "
            "Return the COMPLETE edited article — do NOT summarise it."
        ),
        backstory=(
            "You are a veteran editor who has shaped content for major digital "
            "publications for over 15 years. You have an unrelenting eye for "
            "passive voice, redundant phrases, and murky logic. Your edits always "
            "make content shorter, clearer, and more persuasive — without losing "
            "the author's voice. You treat every article as a product that must "
            "earn the reader's attention in the first sentence."
        ),
        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=2,
    )

    if llm:
        kwargs["llm"] = llm

    return Agent(**kwargs)
