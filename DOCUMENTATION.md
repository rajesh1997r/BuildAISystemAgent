# Technical Documentation
## Content Creation Agentic System

**Course:** Building AI Systems with Agents
**Framework:** CrewAI (Python)
**Model:** OpenAI GPT-4o-mini / GPT-4o

---

## 1. Architecture Description

The system follows a **hierarchical orchestration pattern** with a controller layer sitting above a specialised agent layer.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 0 — User Interface                                    │
│  main.py  (CLI with --topic / --test flags)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Layer 1 — Controller (Orchestration)                        │
│  ContentCreationController                                   │
│  • Input validation & memory initialisation                  │
│  • Dynamic task creation                                     │
│  • CrewAI Crew assembly (sequential process)                 │
│  • Retry logic (exponential back-off)                        │
│  • Output extraction and quality handoff                     │
└──────────┬─────────────────┬─────────────────┬──────────────┘
           │                 │                 │
┌──────────▼───┐  ┌──────────▼───┐  ┌──────────▼───┐
│  Agent A     │  │  Agent B     │  │  Agent C     │
│  Idea        │→ │  Content     │→ │  Content     │
│  Generator   │  │  Writer      │  │  Editor      │
└──────────────┘  └──────────────┘  └──────────────┘
           │                 │                 │
┌──────────▼─────────────────▼─────────────────▼──────────────┐
│  Layer 3 — Tools                                             │
│  WebSearch  │  TextProcessing  │  OutputFormatter            │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Layer 4 — Evaluation                                        │
│  ContentQualityAnalyzer  +  EvaluationMetrics               │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns** — each agent owns a single responsibility.
2. **Shared State via Memory** — `SharedMemory` replaces ad-hoc variable passing.
3. **Graceful Degradation** — tools fall back to offline mode; the controller retries before giving up.
4. **Observability** — verbose logging and printed metrics at every stage.

---

## 2. Agent Roles

### 2.1 Controller Agent — `ContentCreationController`

**File:** `agents/controller_agent.py`

The controller is implemented as a plain Python class (not a CrewAI `Agent`). This choice was deliberate: the controller needs access to Python flow-control constructs (loops, exception handling, shared-memory writes) that cannot be expressed purely in an LLM prompt.

| Responsibility | Implementation |
|---|---|
| Input validation | Enforced in `main.py` before the controller is even called |
| Memory init | `SharedMemory.update({"topic": ..., "status": "running"})` |
| Task creation | `_build_tasks()` creates three `Task` objects wired via `context=` |
| Crew assembly | `Crew(agents=[...], tasks=[...], process=Process.sequential)` |
| Retry logic | `while attempt <= max_retries` with `time.sleep(2 ** attempt)` |
| Output extraction | `_extract_content()` handles both `.raw` and legacy `.output` attributes |

**Error handling strategy:**

```
Attempt 1 → failure → wait 2 s → Attempt 2 → failure → wait 4 s → Attempt 3
    → all failed → return last draft from SharedMemory + error message
```

### 2.2 Idea Generator Agent

**File:** `agents/idea_generator_agent.py`

- **Role:** `"Creative Content Idea Generator"`
- **Tools:** `WebSearchTool`, `TextProcessingTool`
- **Output contract:** numbered list of 5-10 ideas, ending with `SELECTED IDEA: <text>`

The `SELECTED IDEA:` sentinel is parsed by the writer task prompt automatically since CrewAI passes the full output as `context` to the next task.

### 2.3 Content Writer Agent

**File:** `agents/content_writer_agent.py`

- **Role:** `"Professional Content Writer"`
- **Tools:** `WebSearchTool`, `OutputFormatterTool`
- **Output contract:** Markdown article with `#` title, at least three `##` sections, a bullet list, and 400-700 words.

Receives the idea task's full output via `context=[idea_task]`, so it has access to all generated ideas and the selected one.

### 2.4 Content Editor Agent

**File:** `agents/content_editor_agent.py`

- **Role:** `"Expert Content Editor"`
- **Tools:** `TextProcessingTool`, `OutputFormatterTool`
- **Output contract:** Complete, edited Markdown article (NOT a summary).

The task description explicitly instructs the agent to return the full article. This is necessary because LLMs tend to summarise when asked to "review."

---

## 3. Memory System

**File:** `utils/memory.py`

### Design

A synchronous, dictionary-backed store implemented as a Python class. This was chosen over CrewAI's built-in memory system (which uses ChromaDB) to avoid heavyweight dependencies and to give full programmatic control over what is stored and when.

### Schema

| Key | Type | Set By | Read By |
|---|---|---|---|
| `topic` | str | Controller | All agents (via task description) |
| `status` | str | Controller | main.py |
| `final_content` | str | Controller (post-crew) | main.py, Analyzer |
| `error` | str | Controller (on failure) | main.py |

### API Summary

```python
mem = SharedMemory()
mem.set("key", value)          # store
mem.get("key", default=None)   # retrieve
mem.update({"a": 1, "b": 2})   # bulk store
mem.has("key")                 # existence check
mem.delete("key")              # remove single key
mem.clear()                    # wipe all
mem.get_history()              # operation audit log
mem.to_json()                  # serialise to JSON string
```

---

## 4. Tool Descriptions

### 4.1 Web Search Tool

**File:** `tools/web_search_tool.py`
**Class:** `WebSearchTool(BaseTool)`

Uses `duckduckgo-search` (DDGS) to retrieve real-time web results. The tool is wrapped in a `try/except` so it degrades cleanly to pre-written mock results if the network is unreachable or the library is missing.

Input schema (Pydantic):
```python
class WebSearchInput(BaseModel):
    query: str
    max_results: int = Field(default=5, ge=1, le=10)
```

### 4.2 Text Processing Tool

**File:** `tools/text_processing_tool.py`
**Class:** `TextProcessingTool(BaseTool)`

A single tool exposing four string-manipulation operations via a dispatch table. This avoids creating four separate tool instances while keeping each operation's logic isolated.

| Operation | Algorithm |
|---|---|
| `clean` | Regex normalisation of whitespace, tabs, blank lines |
| `summarize` | Sentence splitting → pick first, middle, last |
| `format` | Capitalise first character of each paragraph |
| `extract_keywords` | Word-frequency map minus stop-words, top-10 |

### 4.3 Output Formatter Tool

**File:** `tools/output_formatter_tool.py`
**Class:** `OutputFormatterTool(BaseTool)`

Transforms content into three output formats:

- **Markdown:** Normalises heading spacing, collapses blank lines, trims trailing whitespace.
- **HTML:** Converts ATX headings, bold, italic, and lists to HTML elements; wraps in a minimal HTML5 shell.
- **Plain:** Strips all Markdown syntax using regex substitutions.

---

## 5. Custom Tool — ContentQualityAnalyzer

**File:** `tools/content_quality_analyzer.py`
**Class:** `ContentQualityAnalyzer`

### Purpose

Evaluate the quality of generated content without requiring another LLM call. This reduces latency and cost while giving deterministic, auditable scores.

### Input Validation

```python
if content is None or content == "":   → score 0
if not isinstance(content, str):       → score 0
if content.strip() length < 20:        → score 1
```

### Scoring Algorithm

```
final_score = (
    length_score      * 0.20  +
    readability_score * 0.30  +
    engagement_score  * 0.30  +
    structure_score   * 0.20
)
final_score = clamp(final_score, 1.0, 10.0)
```

#### Length Dimension (20 %)

| Word Count | Score |
|---|---|
| < 100 | 3.0 |
| 100 – 299 | 6.0 |
| 300 – 399 | 8.0 |
| 400 – 1500 | 10.0 (ideal) |
| > 1500 | 7.0 |

#### Readability Dimension (30 %)

Starts at 10.0; deductions:
- Average sentence > 25 words → −3.0
- Average sentence > 20 words → −1.5
- > 30 % of sentences exceed 35 words → −2.0

#### Engagement Dimension (30 %)

Starts at 5.0; additions:
- ≥ 2 question marks → +1.5
- 1 question mark → +0.75
- ≥ 3 Markdown headings → +2.0
- 1-2 headings → +1.0
- Bullet/numbered list present → +1.0
- Bold emphasis present → +0.5

#### Structure Dimension (20 %)

Starts at 5.0; additions:
- ≥ 5 paragraphs → +3.5
- ≥ 3 paragraphs → +2.0
- 2 paragraphs → +1.0
- Conclusion keyword detected → +1.5
- Introduction keyword detected → +0.5

### Output Example

```python
{
    "score": 7.8,
    "suggestions": [
        "Add 1–2 rhetorical questions to engage readers.",
        "Add a clear conclusion section."
    ],
    "breakdown": {
        "length":      9.0,
        "readability": 8.0,
        "engagement":  7.5,
        "structure":   6.5
    }
}
```

---

## 6. Evaluation Metrics

**File:** `utils/metrics.py`

Three metrics are captured on every run:

| Metric | Measurement | Acceptable Threshold |
|---|---|---|
| Response Time | `time.time()` delta | < 300 seconds |
| Content Length | `len(final_content)` in characters | > 100 characters |
| Quality Score | `ContentQualityAnalyzer.analyze()` | ≥ 5.0 / 10 |

All three must pass for `is_acceptable()` to return `True`.

---

## 7. Orchestration Flow (Step-by-Step)

```
1.  User provides topic string via CLI or programmatic call.

2.  main.py validates input:
      - Empty string → return error immediately
      - Length < 3 chars → return error immediately

3.  SharedMemory initialised; topic stored.

4.  ContentCreationController instantiated; all three agents created.

5.  Controller calls _build_tasks(topic):
      - Creates idea_task (agent=idea_agent)
      - Creates writer_task (agent=writer_agent, context=[idea_task])
      - Creates editor_task (agent=editor_agent, context=[writer_task])

6.  Crew(agents, tasks, process=sequential).kickoff() called.

7.  CrewAI runs tasks sequentially:
      7a. idea_agent executes idea_task
          → calls WebSearchTool("trends for <topic>")
          → generates 5-10 ideas
          → outputs list + "SELECTED IDEA: ..."

      7b. writer_agent executes writer_task
          → receives idea_task output as context
          → optionally calls WebSearchTool for stats
          → outputs full Markdown article

      7c. editor_agent executes editor_task
          → receives writer_task output as context
          → cleans, sharpens, formats content
          → calls OutputFormatterTool("markdown")
          → returns complete edited article

8.  Controller extracts final_content from CrewOutput.raw.

9.  final_content stored in SharedMemory.

10. ContentQualityAnalyzer.analyze(final_content) called.

11. EvaluationMetrics computed.

12. Results printed to console; result dict returned to caller.
```

---

## 8. Challenges and Solutions

### Challenge 1: LLM Output Variability

**Problem:** LLMs do not always follow output format instructions precisely. The editor sometimes returned a summary instead of the full article.

**Solution:** The editor task description includes an explicit `IMPORTANT: Return the COMPLETE edited article, not a summary.` instruction, and the task `expected_output` field reinforces this.

### Challenge 2: Tool Unavailability

**Problem:** DuckDuckGo rate-limits or network issues could abort the pipeline.

**Solution:** `WebSearchTool._run()` wraps all search calls in `try/except`. On failure it returns `_mock_search()` output with a warning message. The pipeline continues uninterrupted.

### Challenge 3: CrewAI Version API Changes

**Problem:** CrewAI has made breaking changes across minor versions; `crew_result.raw` vs `crew_result.output` differs by version.

**Solution:** `ContentCreationController._extract_content()` checks for both attributes with `hasattr()` guards and falls back to `str(crew_output)` as a last resort.

### Challenge 4: Retry Without Infinite Loops

**Problem:** Unconditional retries on deterministic errors (e.g., invalid API key) waste time.

**Solution:** The retry loop uses exponential back-off (`time.sleep(2 ** attempt)`) and caps at `max_retries=2` (3 total attempts). Validation errors are caught before the retry loop.

### Challenge 5: Quality Evaluation Without Extra LLM Cost

**Problem:** Using another LLM call to score content adds latency and API cost.

**Solution:** The `ContentQualityAnalyzer` uses pure Python heuristics (regex, string methods, word counts). Zero API calls; deterministic results.

---

## 9. Limitations

1. **Heuristic quality scoring** — The `ContentQualityAnalyzer` uses rule-based metrics that do not capture semantic coherence, factual accuracy, or domain appropriateness. It is a proxy, not a ground-truth measure.

2. **Sequential pipeline** — The current architecture runs all three agents serially. For longer content pipelines, a parallel sub-crew could reduce latency.

3. **No persistent memory across sessions** — `SharedMemory` is an in-process dictionary. State is lost when the process exits. Adding Redis or SQLite persistence would enable cross-session continuity.

4. **Single-language support** — All prompts, agents, and tools are English-only.

5. **Web search reliability** — DuckDuckGo's free API is rate-limited and may fail under heavy use. A Serper or Bing API key would provide more reliable search.

6. **No human-in-the-loop** — The system is fully automated. Adding a review/approval step after idea generation would improve output relevance for domain-specific topics.

7. **Cost and rate limits** — GPT-4o calls can be expensive for long content. Using `gpt-4o-mini` as the default balances cost and quality for a demonstration system.

---

## 10. Future Work

- Add a **Fact-Checker Agent** that verifies claims against live web sources.
- Implement **CrewAI built-in memory** (ChromaDB) for cross-session idea persistence.
- Add a **content scheduler** that produces a week's worth of posts on a single call.
- Build a **Streamlit web interface** for non-technical users.
- Integrate **Serper API** for higher-reliability web search.
- Support **multi-language** output via locale-aware agent prompts.
