"""
Controller Agent (Orchestrator)
================================
The ContentCreationController is the brain of the system.

Responsibilities
----------------
  1. Receive the user's topic.
  2. Validate input and initialise shared memory.
  3. Dynamically create Tasks for each specialised agent.
  4. Assemble and run the CrewAI Crew (sequential process).
  5. Handle errors with retry logic and graceful fallback.
  6. Persist workflow state in SharedMemory throughout the run.
  7. Return the aggregated final output.

Workflow
--------
  User Input → Idea Task → Writer Task → Editor Task → Output
"""
import os
import time
from typing import Dict, Optional

from crewai import Agent, Task, Crew, Process

from utils.memory import SharedMemory
from agents.idea_generator_agent import create_idea_generator_agent
from agents.content_writer_agent import create_content_writer_agent
from agents.content_editor_agent import create_content_editor_agent


class ContentCreationController:
    """
    High-level orchestrator for the multi-agent content creation pipeline.

    Parameters
    ----------
    memory : SharedMemory, optional
        External memory instance. A fresh one is created if not supplied.
    llm : optional
        LLM to pass to all child agents (useful for testing with cheaper models).
    max_retries : int
        Number of times the pipeline will retry on transient errors.
    """

    def __init__(
        self,
        memory: Optional[SharedMemory] = None,
        llm=None,
        max_retries: int = 2,
    ):
        self.memory      = memory or SharedMemory()
        self.llm         = llm
        self.max_retries = max_retries

        self._setup_agents()

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def _setup_agents(self) -> None:
        """Instantiate all specialised agents once at construction time."""
        self.idea_agent   = create_idea_generator_agent(self.llm)
        self.writer_agent = create_content_writer_agent(self.llm)
        self.editor_agent = create_content_editor_agent(self.llm)
        print("✓  Controller: All agents initialised successfully.")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self, topic: str) -> Dict:
        """
        Execute the full content creation pipeline for *topic*.

        Args:
            topic: The subject the system should write about.

        Returns:
            {
              "final_content": str,
              "status":        "success" | "error",
              "memory":        dict  (full memory snapshot),
              "error":         str   (only present on failure)
            }
        """
        print(f"\n🚀  Controller: Starting pipeline — topic='{topic}'")
        self.memory.update({"topic": topic, "status": "running"})

        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            if attempt > 0:
                wait = 2 ** attempt          # exponential back-off
                print(f"♻   Controller: Retry {attempt}/{self.max_retries} "
                      f"(waiting {wait}s)…")
                time.sleep(wait)

            try:
                result = self._execute_pipeline(topic)
                self.memory.set("status", "completed")
                print("✅  Controller: Pipeline completed successfully.")
                return result

            except Exception as exc:
                last_error = exc
                print(f"⚠   Controller: Attempt {attempt + 1} failed — {exc}")
                attempt += 1

        # All retries exhausted
        self.memory.update({"status": "error", "error": str(last_error)})
        return {
            "final_content": self.memory.get("draft_content", ""),
            "status":        "error",
            "error":         str(last_error),
            "memory":        self.memory.get_all(),
        }

    # ------------------------------------------------------------------ #
    # Pipeline internals
    # ------------------------------------------------------------------ #

    def _execute_pipeline(self, topic: str) -> Dict:
        """Build tasks, create the Crew, kick it off, and parse results."""

        # ---- Create tasks ------------------------------------------------
        idea_task, writer_task, editor_task = self._build_tasks(topic)

        # ---- Assemble the Crew -------------------------------------------
        crew = Crew(
            agents=[self.idea_agent, self.writer_agent, self.editor_agent],
            tasks=[idea_task, writer_task, editor_task],
            process=Process.sequential,
            verbose=True,
        )

        print("📋  Controller: Kicking off crew…")
        crew_output = crew.kickoff()

        # ---- Extract content ---------------------------------------------
        final_content = self._extract_content(crew_output)

        # Persist to shared memory
        self.memory.set("final_content", final_content)

        return {
            "final_content": final_content,
            "status":        "success",
            "memory":        self.memory.get_all(),
        }

    def _build_tasks(self, topic: str):
        """
        Create the three tasks and wire them together via context.

        Returns:
            Tuple[Task, Task, Task] — (idea_task, writer_task, editor_task)
        """

        # ── Task 1: Idea Generation ───────────────────────────────────────
        idea_task = Task(
            description=(
                f"You are researching and generating ideas for the topic: '{topic}'.\n\n"
                "Steps:\n"
                "1. Use the Web Search Tool to find current trends for this topic.\n"
                "2. Brainstorm 5-10 unique content angles.\n"
                "3. Present them as a numbered list, each with a 1-sentence pitch.\n"
                "4. On the very last line write exactly:\n"
                "   SELECTED IDEA: <your single best idea in one sentence>\n\n"
                "Be specific — avoid generic ideas like 'Introduction to <topic>'."
            ),
            expected_output=(
                "A numbered list of 5-10 content ideas with one-sentence descriptions, "
                "followed by a line starting with 'SELECTED IDEA:' naming the best idea."
            ),
            agent=self.idea_agent,
        )

        # ── Task 2: Content Drafting ──────────────────────────────────────
        writer_task = Task(
            description=(
                f"Using the ideas generated for '{topic}', write a full article "
                "based on the SELECTED IDEA from the previous task.\n\n"
                "Article requirements:\n"
                "• Title using `#` (level-1 heading)\n"
                "• Introduction paragraph (2-3 sentences, hook the reader)\n"
                "• At least 3 body sections, each with a `##` heading\n"
                "• Bullet points or numbered list in at least one section\n"
                "• Conclusion section with a clear takeaway\n"
                "• 1-2 rhetorical questions throughout the article\n"
                "• Total: 400-700 words\n\n"
                "Write in a clear, authoritative, and engaging style."
            ),
            expected_output=(
                "A complete Markdown article: # title, introduction, 3+ ## sections "
                "with at least one list, and a conclusion — 400-700 words total."
            ),
            agent=self.writer_agent,
            context=[idea_task],
        )

        # ── Task 3: Editing & Polishing ───────────────────────────────────
        editor_task = Task(
            description=(
                "Edit and polish the drafted article.\n\n"
                "Editing checklist:\n"
                "1. Fix all grammar, spelling, and punctuation errors.\n"
                "2. Replace passive voice with active voice where possible.\n"
                "3. Shorten sentences that exceed 30 words.\n"
                "4. Sharpen the opening hook to grab the reader in the first sentence.\n"
                "5. Ensure the conclusion ends with a memorable statement or call-to-action.\n"
                "6. Verify Markdown headings are correctly formatted.\n"
                "7. Use the Content Quality Analyzer Tool to self-check your draft — "
                "aim for a score of 8 or above before finalizing.\n"
                "8. Use the Output Formatter Tool to produce clean final Markdown.\n\n"
                "IMPORTANT: Return the COMPLETE edited article, not a summary."
            ),
            expected_output=(
                "The complete, publication-ready article in clean Markdown format, "
                "with improved clarity, grammar, tone, and engagement."
            ),
            agent=self.editor_agent,
            context=[writer_task],
        )

        return idea_task, writer_task, editor_task

    @staticmethod
    def _extract_content(crew_output) -> str:
        """Safely extract the string content from CrewAI's output object."""
        if crew_output is None:
            return ""
        # CrewAI ≥ 0.51 returns a CrewOutput with a .raw attribute
        if hasattr(crew_output, "raw"):
            return str(crew_output.raw).strip()
        if hasattr(crew_output, "output"):
            return str(crew_output.output).strip()
        return str(crew_output).strip()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def get_memory_state(self) -> Dict:
        """Return a snapshot of the current shared memory."""
        return self.memory.get_all()
