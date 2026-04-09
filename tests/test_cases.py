"""
Test Suite for the Content Creation Agentic System
====================================================
Sections:
  1. Unit tests for ContentQualityAnalyzer  (no API key required)
  2. Unit tests for SharedMemory            (no API key required)
  3. Unit tests for EvaluationMetrics       (no API key required)
  4. Unit tests for tool helpers            (no API key required)
  5. Integration test definitions           (requires OPENAI_API_KEY)

Run all unit tests:
    python tests/test_cases.py

Run integration tests (requires API key):
    python main.py --test
"""
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from module files to avoid triggering crewai imports
# in tools/__init__.py (crewai is only needed for live pipeline runs).
import importlib.util, pathlib

_ROOT = pathlib.Path(__file__).parent.parent

def _load(rel_path):
    spec = importlib.util.spec_from_file_location(rel_path, _ROOT / rel_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_qa_mod   = _load("tools/content_quality_analyzer.py")
_tp_mod   = _load("tools/text_processing_tool.py")
_of_mod   = _load("tools/output_formatter_tool.py")
_mem_mod  = _load("utils/memory.py")
_met_mod  = _load("utils/metrics.py")

ContentQualityAnalyzer = _qa_mod.ContentQualityAnalyzer
TextProcessingTool     = _tp_mod.TextProcessingTool
OutputFormatterTool    = _of_mod.OutputFormatterTool
SharedMemory           = _mem_mod.SharedMemory
EvaluationMetrics      = _met_mod.EvaluationMetrics


# ══════════════════════════════════════════════════════════════════════════ #
# Base test harness
# ══════════════════════════════════════════════════════════════════════════ #

class _TestRunner:
    """Minimal test harness — no external dependencies."""

    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.passed = 0
        self.failed = 0

    # ── Assertions ─────────────────────────────────────────────────────

    def eq(self, actual, expected, name: str) -> None:
        if actual == expected:
            self._ok(name)
        else:
            self._fail(name, f"expected {expected!r}, got {actual!r}")

    def true(self, condition, name: str) -> None:
        if condition:
            self._ok(name)
        else:
            self._fail(name, "condition is False")

    def false(self, condition, name: str) -> None:
        if not condition:
            self._ok(name)
        else:
            self._fail(name, "condition is True")

    def in_range(self, value, lo, hi, name: str) -> None:
        if lo <= value <= hi:
            self._ok(f"{name} ({value})")
        else:
            self._fail(name, f"{value} not in [{lo}, {hi}]")

    def has_key(self, d: dict, key: str, name: str) -> None:
        if key in d:
            self._ok(name)
        else:
            self._fail(name, f"key '{key}' missing from {list(d.keys())}")

    # ── Internals ──────────────────────────────────────────────────────

    def _ok(self, name: str) -> None:
        print(f"    ✅  {name}")
        self.passed += 1

    def _fail(self, name: str, reason: str) -> None:
        print(f"    ❌  {name}  ({reason})")
        self.failed += 1

    def summary(self) -> bool:
        total = self.passed + self.failed
        print(f"\n  [{self.suite_name}]  {self.passed}/{total} tests passed.")
        return self.failed == 0


# ══════════════════════════════════════════════════════════════════════════ #
# 1. ContentQualityAnalyzer
# ══════════════════════════════════════════════════════════════════════════ #

def test_quality_analyzer() -> bool:
    t = _TestRunner("ContentQualityAnalyzer")
    analyzer = ContentQualityAnalyzer()

    print("\n  ── ContentQualityAnalyzer ──")

    # Empty string
    r = analyzer.analyze("")
    t.eq(r["score"], 0, "Empty string → score 0")
    t.true(len(r["suggestions"]) > 0, "Empty string → has suggestions")

    # None input
    r = analyzer.analyze(None)
    t.eq(r["score"], 0, "None input → score 0")
    t.true("Content is empty" in r["suggestions"][0], "None → meaningful message")

    # Integer input (wrong type)
    r = analyzer.analyze(42)
    t.eq(r["score"], 0, "Integer input → score 0")

    # Very short content
    r = analyzer.analyze("Hello world.")
    t.in_range(r["score"], 0, 3, "Very short → low score")

    # Minimal valid content
    r = analyzer.analyze("This is a test sentence. " * 20)
    t.in_range(r["score"], 1.0, 10.0, "Repetitive content → score in range")

    # Well-structured content (should score well)
    article = (
        "# The Rise of AI\n\n"
        "Artificial intelligence is transforming every industry. "
        "Are you ready for this shift?\n\n"
        "## Healthcare Applications\n\n"
        "AI diagnoses diseases faster than human doctors in many cases.\n"
        "- Radiology image analysis\n"
        "- Drug discovery acceleration\n"
        "- Personalised treatment plans\n\n"
        "## Education Transformation\n\n"
        "Adaptive learning platforms tailor lessons to each student. "
        "This approach improves retention by up to 40 %.\n\n"
        "## Ethical Considerations\n\n"
        "Bias in training data remains a critical challenge. "
        "Who is responsible when an AI makes a mistake?\n\n"
        "## Conclusion\n\n"
        "In conclusion, AI is not a threat — it is a tool. "
        "Our job is to wield it responsibly.\n"
    )
    r = analyzer.analyze(article)
    t.in_range(r["score"], 5.0, 10.0, "Good article → high score")
    t.has_key(r, "breakdown", "Result contains breakdown")
    t.in_range(r["breakdown"]["engagement"], 1.0, 10.0, "Engagement sub-score in range")
    t.in_range(r["breakdown"]["structure"],  1.0, 10.0, "Structure sub-score in range")

    # Score ceiling / floor
    for content in ["A" * 5, "word " * 500, article]:
        r = analyzer.analyze(content)
        if content.strip():
            t.in_range(r["score"], 1.0, 10.0, f"Score in [1,10] for len={len(content)}")

    return t.summary()


# ══════════════════════════════════════════════════════════════════════════ #
# 2. SharedMemory
# ══════════════════════════════════════════════════════════════════════════ #

def test_shared_memory() -> bool:
    t = _TestRunner("SharedMemory")
    print("\n  ── SharedMemory ──")

    mem = SharedMemory()

    # Basic set / get
    mem.set("topic", "AI")
    t.eq(mem.get("topic"), "AI", "set/get basic string")

    # Default value
    t.eq(mem.get("missing", "default"), "default", "get missing key returns default")
    t.eq(mem.get("missing"),            None,      "get missing key returns None by default")

    # Overwrite
    mem.set("topic", "ML")
    t.eq(mem.get("topic"), "ML", "Overwrite existing key")

    # Bulk update
    mem.update({"a": 1, "b": 2, "c": 3})
    t.eq(mem.get("a"), 1, "bulk update — key a")
    t.eq(mem.get("c"), 3, "bulk update — key c")

    # has()
    t.true(mem.has("a"),       "has() returns True for existing key")
    t.false(mem.has("zzz"),    "has() returns False for missing key")

    # get_all()
    all_data = mem.get_all()
    t.true(isinstance(all_data, dict), "get_all returns dict")
    t.true("topic" in all_data,        "get_all contains 'topic'")

    # History
    history = mem.get_history()
    t.true(len(history) >= 5,   "history has recorded operations")
    t.has_key(history[0], "timestamp", "history entries have timestamp")
    t.has_key(history[0], "key",       "history entries have key")

    # Delete
    mem.set("temp", "x")
    mem.delete("temp")
    t.eq(mem.get("temp"), None, "delete removes key")

    # Clear
    mem.clear()
    t.eq(mem.get("a"), None, "clear removes all keys")
    t.eq(len(mem.get_all()), 0, "get_all empty after clear")

    # to_json
    mem.set("score", 8.5)
    json_str = mem.to_json()
    t.true('"score"' in json_str, "to_json serialises correctly")

    return t.summary()


# ══════════════════════════════════════════════════════════════════════════ #
# 3. EvaluationMetrics
# ══════════════════════════════════════════════════════════════════════════ #

def test_evaluation_metrics() -> bool:
    t = _TestRunner("EvaluationMetrics")
    print("\n  ── EvaluationMetrics ──")

    # Acceptable run
    m = EvaluationMetrics(response_time=12.5, content_length=800, quality_score=7.5)
    t.true(m.is_acceptable(), "Good metrics → acceptable")
    d = m.to_dict()
    t.has_key(d, "response_time",  "to_dict has response_time")
    t.has_key(d, "content_length", "to_dict has content_length")
    t.has_key(d, "quality_score",  "to_dict has quality_score")
    t.eq(d["quality_score"], 7.5, "to_dict preserves quality_score value")

    # Unacceptable — too short
    m2 = EvaluationMetrics(response_time=5.0, content_length=50, quality_score=8.0)
    t.false(m2.is_acceptable(), "Short content → not acceptable")

    # Unacceptable — low quality
    m3 = EvaluationMetrics(response_time=5.0, content_length=500, quality_score=3.0)
    t.false(m3.is_acceptable(), "Low quality score → not acceptable")

    # Unacceptable — timeout
    m4 = EvaluationMetrics(response_time=400.0, content_length=500, quality_score=7.0)
    t.false(m4.is_acceptable(), "Slow response → not acceptable")

    return t.summary()


# ══════════════════════════════════════════════════════════════════════════ #
# 4. Tool helpers (no LLM / network calls)
# ══════════════════════════════════════════════════════════════════════════ #

def test_text_processing_tool() -> bool:
    t = _TestRunner("TextProcessingTool")
    print("\n  ── TextProcessingTool ──")

    tool = TextProcessingTool()

    # empty input
    r = tool._run("", "clean")
    t.true("Error" in r, "Empty text → error message")

    # unknown operation
    r = tool._run("hello world", "nonexistent")
    t.true("Unknown operation" in r, "Unknown op → error message")

    # clean
    dirty = "hello   world\n\n\n\nfoo   bar"
    cleaned = tool._run(dirty, "clean")
    t.false("   " in cleaned, "clean removes multiple spaces")
    t.false("\n\n\n" in cleaned, "clean collapses blank lines")

    # summarize — short text passes through
    short = "One sentence only here."
    r = tool._run(short, "summarize")
    t.true("Summary" in r, "summarize returns Summary label")

    # extract_keywords
    text = "artificial intelligence machine learning deep learning neural networks"
    r = tool._run(text, "extract_keywords")
    t.true("Top Keywords" in r, "extract_keywords returns keyword list")

    # format — lowercase first char gets capitalised
    r = tool._run("hello world. this is a test.", "format")
    t.true(r[0].isupper(), "format capitalises first character")

    return t.summary()


def test_output_formatter_tool() -> bool:
    t = _TestRunner("OutputFormatterTool")
    print("\n  ── OutputFormatterTool ──")

    tool = OutputFormatterTool()

    # empty content
    r = tool._run("", "markdown")
    t.true("Error" in r, "Empty content → error message")

    # unknown format falls back to markdown
    sample = "# Title\n\nParagraph text."
    r = tool._run(sample, "unknown_format")
    t.true("Title" in r, "Unknown format falls back to markdown")

    # markdown output ends with newline
    r = tool._run(sample, "markdown")
    t.true(r.endswith("\n"), "Markdown output ends with newline")

    # html output contains doctype
    r = tool._run(sample, "html")
    t.true("<!DOCTYPE html>" in r, "HTML output contains DOCTYPE")
    t.true("<h1>" in r,            "HTML output converts # heading to <h1>")

    # plain strips # headings
    r = tool._run("# Title\n\nBody text.", "plain")
    t.false(r.startswith("#"), "Plain output has no # heading marker")
    t.true("Title" in r,          "Plain output preserves heading text")

    return t.summary()


# ══════════════════════════════════════════════════════════════════════════ #
# 5. Integration test descriptions
# ══════════════════════════════════════════════════════════════════════════ #

def describe_integration_tests() -> None:
    """Print a description of the three end-to-end test cases."""
    TESTS = [
        {
            "id":    1,
            "name":  "Normal Topic",
            "input": "Artificial Intelligence in Healthcare",
            "expected": {
                "status":           "success",
                "min_word_count":   200,
                "min_quality_score": 5.0,
            },
            "rationale": (
                "A well-defined topic should produce a complete, high-quality "
                "article with title, body sections, and conclusion."
            ),
        },
        {
            "id":    2,
            "name":  "Very Vague Topic",
            "input": "technology",
            "expected": {
                "status":           "success",
                "min_word_count":   100,
                "min_quality_score": 4.0,
            },
            "rationale": (
                "A one-word broad topic tests the Idea Generator's ability to "
                "narrow scope creatively and still produce relevant content."
            ),
        },
        {
            "id":    3,
            "name":  "Edge Case — Empty Input",
            "input": "",
            "expected": {
                "status":           "error",
                "min_word_count":   0,
                "min_quality_score": 0,
            },
            "rationale": (
                "Empty input must be caught by input validation before "
                "reaching any agent, returning a meaningful error message."
            ),
        },
    ]

    print("\n" + "─" * 60)
    print("  INTEGRATION TEST CASES  (require OPENAI_API_KEY)")
    print("─" * 60)
    for tc in TESTS:
        print(f"\n  Test {tc['id']}: {tc['name']}")
        print(f"    Input    : \"{tc['input']}\"")
        print(f"    Expected : {tc['expected']}")
        print(f"    Rationale: {tc['rationale']}")
    print(
        "\n  ▶  Run with:  python main.py --test\n"
    )


# ══════════════════════════════════════════════════════════════════════════ #
# Runner
# ══════════════════════════════════════════════════════════════════════════ #

if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  UNIT TEST SUITE — Content Creation Agentic System")
    print("═" * 60)

    results = [
        test_quality_analyzer(),
        test_shared_memory(),
        test_evaluation_metrics(),
        test_text_processing_tool(),
        test_output_formatter_tool(),
    ]

    describe_integration_tests()

    # Final summary
    print("\n" + "═" * 60)
    print("  UNIT TEST SUMMARY")
    print("═" * 60)
    all_passed = all(results)
    suite_names = [
        "ContentQualityAnalyzer",
        "SharedMemory",
        "EvaluationMetrics",
        "TextProcessingTool",
        "OutputFormatterTool",
    ]
    for name, passed in zip(suite_names, results):
        icon = "✅" if passed else "❌"
        print(f"  {icon}  {name}")

    final_status = "ALL UNIT TESTS PASSED ✅" if all_passed else "SOME TESTS FAILED ❌"
    print(f"\n  {final_status}")
    sys.exit(0 if all_passed else 1)
