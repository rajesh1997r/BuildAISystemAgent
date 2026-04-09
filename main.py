"""
Content Creation Agentic System
================================
University Assignment — Multi-Agent AI System using CrewAI

Entry point.  Run as:

    python main.py                         # default topic demo
    python main.py --topic "Your Topic"    # custom topic
    python main.py --test                  # run all three test cases
"""
import argparse
import os
import sys
import time

# ── Load environment variables first ──────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Validate API key before importing CrewAI (which calls OpenAI eagerly) ─
if not os.getenv("OPENAI_API_KEY"):
    print(
        "\n❌  OPENAI_API_KEY not found in environment variables.\n"
        "    Create a .env file (see .env.example) and add your key.\n"
    )
    sys.exit(1)

# ── Project imports ────────────────────────────────────────────────────────
from utils.memory import SharedMemory
from utils.metrics import EvaluationMetrics
from agents.controller_agent import ContentCreationController
from tools.content_quality_analyzer import ContentQualityAnalyzer


# ══════════════════════════════════════════════════════════════════════════ #
# Core pipeline runner
# ══════════════════════════════════════════════════════════════════════════ #

def run_content_creation(topic: str) -> dict:
    """
    Execute the full content-creation pipeline for *topic*.

    Orchestration steps:
      1. Validate input.
      2. Initialise SharedMemory.
      3. Delegate to ContentCreationController (3-agent crew).
      4. Run ContentQualityAnalyzer on the final output.
      5. Compute EvaluationMetrics.
      6. Return aggregated result dict.

    Args:
        topic: Subject for the article.

    Returns:
        {
          "status":           "success" | "error",
          "final_content":    str,
          "selected_idea":    str,
          "quality_score":    float,
          "quality_breakdown":dict,
          "suggestions":      list[str],
          "metrics":          dict,
          "error":            str  (only on failure)
        }
    """
    # ── Input validation ────────────────────────────────────────────────
    topic_stripped = topic.strip() if topic else ""

    if not topic_stripped:
        print("\n❌  Error: Topic cannot be empty.")
        return _error_result("empty_topic", "Please provide a non-empty topic string.")

    if len(topic_stripped) < 3:
        print(f"\n❌  Error: Topic '{topic_stripped}' is too short (< 3 chars).")
        return _error_result(
            "topic_too_short",
            "Topic must be at least 3 characters. Please be more descriptive.",
        )

    # ── Banner ──────────────────────────────────────────────────────────
    _print_banner(f"CONTENT CREATION SYSTEM  |  Topic: {topic_stripped}")

    start_time = time.time()

    # ── Initialise shared memory ────────────────────────────────────────
    memory = SharedMemory()

    # ── Run multi-agent pipeline via controller ──────────────────────────
    controller = ContentCreationController(memory=memory)
    pipeline_result = controller.run(topic=topic_stripped)

    final_content = pipeline_result.get("final_content", "")

    # ── Quality analysis ────────────────────────────────────────────────
    analyzer     = ContentQualityAnalyzer()
    quality      = analyzer.analyze(final_content)

    # ── Evaluation metrics ───────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 2)
    metrics = EvaluationMetrics(
        response_time=elapsed,
        content_length=len(final_content),
        quality_score=quality["score"],
    )

    # ── Print metrics to console ─────────────────────────────────────────
    _print_section("EVALUATION METRICS")
    metrics.print_metrics()

    _print_section("QUALITY ANALYSIS")
    print(f"  Overall Score : {quality['score']:.1f} / 10")
    if "breakdown" in quality:
        print("\n  Breakdown:")
        for dim, val in quality["breakdown"].items():
            bar = "█" * int(val) + "░" * (10 - int(val))
            print(f"    {dim.capitalize():15} {bar}  {val:.1f}")
    print("\n  Suggestions:")
    for tip in quality["suggestions"][:5]:
        print(f"    •  {tip}")

    return {
        "status":            pipeline_result.get("status", "unknown"),
        "final_content":     final_content,
        "selected_idea":     memory.get("selected_idea", "—"),
        "quality_score":     quality["score"],
        "quality_breakdown": quality.get("breakdown", {}),
        "suggestions":       quality["suggestions"],
        "metrics":           metrics.to_dict(),
    }


# ══════════════════════════════════════════════════════════════════════════ #
# Test-case runner
# ══════════════════════════════════════════════════════════════════════════ #

TEST_CASES = [
    {
        "id":              1,
        "name":            "Normal Topic",
        "topic":           "Artificial Intelligence in Healthcare",
        "description":     "A well-defined, substantive topic.",
        "expected_status": "success",
    },
    {
        "id":              2,
        "name":            "Very Vague Topic",
        "topic":           "technology",
        "description":     "An intentionally broad, one-word topic.",
        "expected_status": "success",
    },
    {
        "id":              3,
        "name":            "Edge Case — Empty Input",
        "topic":           "",
        "description":     "Empty string; system must reject gracefully before reaching agents.",
        "expected_status": "error",   # error IS the correct outcome here
    },
]


def run_test_cases() -> list:
    """Run all three required test cases and print a summary table."""
    results = []

    for tc in TEST_CASES:
        _print_section(
            f"TEST {tc['id']}: {tc['name']}  |  \"{tc['topic']}\""
        )
        print(f"  Purpose  : {tc['description']}")
        print(f"  Expected : status={tc['expected_status']}\n")

        result = run_content_creation(tc["topic"])
        result["test_id"]        = tc["id"]
        result["test_name"]      = tc["name"]
        result["test_topic"]     = tc["topic"]
        result["expected_status"]= tc["expected_status"]
        results.append(result)

        if result.get("status") == "success" and result.get("final_content"):
            _print_section("FINAL CONTENT (first 1 500 chars)")
            preview = result["final_content"][:1500]
            print(preview)
            if len(result["final_content"]) > 1500:
                print("\n… [truncated — full content in result dict] …")

        actual = result.get("status", "unknown")
        passed = actual == tc["expected_status"]
        print(f"\n  ↳ Status : {actual}  |  Expected: {tc['expected_status']}  |  "
              f"{'PASS ✅' if passed else 'FAIL ❌'}")

    # ── Summary table ───────────────────────────────────────────────────
    _print_section("TEST RESULTS SUMMARY")
    print(f"  {'#':<4} {'Test Name':<30} {'Topic':<38} {'Result':<8} {'Score':<8} {'Time (s)'}")
    print("  " + "-" * 102)
    for r in results:
        # A test PASSES when its actual status matches the expected status.
        # For test 3, returning "error" on empty input IS the correct behaviour.
        passed = r.get("status") == r.get("expected_status", "success")
        icon   = "✅" if passed else "❌"
        score  = f"{r['quality_score']:.1f}"          # always numeric, even 0.0
        secs   = f"{r['metrics']['response_time']:.1f}" if r.get("metrics") else "—"
        topic  = (r["test_topic"] or "(empty)")[:36]
        result_label = "PASS" if passed else "FAIL"
        print(f"  {icon} {r['test_id']:<3} {r['test_name']:<30} {topic:<38} "
              f"{result_label:<8} {score:<8} {secs}")

    return results


# ══════════════════════════════════════════════════════════════════════════ #
# Helpers
# ══════════════════════════════════════════════════════════════════════════ #

def _error_result(error_code: str, message: str) -> dict:
    return {
        "status":            "error",
        "error":             error_code,
        "final_content":     "",
        "selected_idea":     "—",
        "quality_score":     0,
        "quality_breakdown": {},
        "suggestions":       [message],
        "metrics":           EvaluationMetrics(0.0, 0, 0.0).to_dict(),
    }


def _print_banner(title: str) -> None:
    width = max(len(title) + 4, 64)
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


def _print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ══════════════════════════════════════════════════════════════════════════ #
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════ #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Content Creation Agentic System (CrewAI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py\n"
            "  python main.py --topic \"The Future of Remote Work\"\n"
            "  python main.py --test\n"
        ),
    )
    parser.add_argument("--topic", type=str, default=None,
                        help="Topic for content creation.")
    parser.add_argument("--test", action="store_true",
                        help="Run all three built-in test cases.")
    args = parser.parse_args()

    if args.test:
        run_test_cases()
    elif args.topic:
        result = run_content_creation(args.topic)
        if result.get("final_content"):
            _print_section("FINAL CONTENT")
            print(result["final_content"])
    else:
        # Default demo
        result = run_content_creation("The Future of Remote Work")
        if result.get("final_content"):
            _print_section("FINAL CONTENT")
            print(result["final_content"])


if __name__ == "__main__":
    main()
