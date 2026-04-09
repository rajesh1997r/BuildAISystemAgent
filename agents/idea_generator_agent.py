"""
Idea Generator Agent
====================
Generates 5-10 creative, trend-aware content ideas for a given topic.

Tools used:
  - WebSearchTool        : research current trends
  - TextProcessingTool   : extract keywords from the topic
"""
from crewai import Agent
from tools.web_search_tool import WebSearchTool
from tools.text_processing_tool import TextProcessingTool


def create_idea_generator_agent(llm=None) -> Agent:
    """
    Build and return the Idea Generator Agent.

    Args:
        llm: Optional LLM override. When None, CrewAI uses the default
             model configured via OPENAI_API_KEY / OPENAI_MODEL_NAME.

    Returns:
        Configured CrewAI Agent instance.
    """
    tools = [WebSearchTool(), TextProcessingTool()]

    kwargs = dict(
        role="Creative Content Idea Generator",
        goal=(
            "Generate 5-10 creative, relevant, and compelling content ideas "
            "for the given topic. Research current trends to ensure the ideas "
            "are timely, audience-relevant, and highly engaging."
        ),
        backstory=(
            "You are an award-winning content strategist with a decade of "
            "experience in digital marketing, SEO, and audience engagement. "
            "Your superpower is identifying the intersection of trending topics "
            "and genuine audience curiosity. You always search for current "
            "trends before proposing ideas, and you rank ideas by their "
            "potential viral reach and educational value."
        ),
        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=2,
    )

    if llm:
        kwargs["llm"] = llm

    return Agent(**kwargs)
