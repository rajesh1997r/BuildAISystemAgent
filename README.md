# Content Creation Agentic System

A multi-agent AI system built with **CrewAI** and **OpenAI** that autonomously generates, writes, edits, and evaluates article-style content for any topic.

---

## Project Overview

This system demonstrates a complete agentic AI pipeline where a **Controller Agent** orchestrates three specialised agents through a sequential workflow. Users provide a topic; the system returns a publication-ready Markdown article together with quality scores and actionable improvement suggestions.

### Key Features

| Feature | Detail |
|---|---|
| Multi-agent orchestration | Controller → Idea Generator → Writer → Editor |
| Shared memory | Dictionary-based state store across all agents |
| 4 integrated tools | Web Search, Text Processing, Output Formatter, Quality Analyzer |
| Custom tool | `ContentQualityAnalyzer` with heuristic scoring (1–10) |
| Evaluation metrics | Response time · content length · quality score |
| Error handling | Exponential-backoff retry, graceful fallback |
| 3 test cases | Normal topic · vague topic · empty-input edge case |

---

## Architecture

```
User Input (topic)
        │
        ▼
┌───────────────────────┐
│   ContentCreation     │  ← Controller Agent (Python class)
│   Controller          │    • Validates input
│                       │    • Manages SharedMemory
│   ┌───────────────┐   │    • Builds & runs CrewAI Crew
│   │  SharedMemory │   │    • Handles retries
│   └───────────────┘   │
└──────────┬────────────┘
           │  CrewAI sequential process
    ┌──────┴──────────────────────────────┐
    │                                     │
    ▼                                     │
┌──────────────────┐  context             │
│  Idea Generator  │──────────────────────►
│  Agent           │                      │
│  Tools:          │  context             │
│  • WebSearch     │──────────────────────►
│  • TextProcess   │                      │
└──────────────────┘                      │
    │ ideas (5-10)                        │
    ▼                                     │
┌──────────────────┐                      │
│  Content Writer  │                      │
│  Agent           │  context             │
│  Tools:          │──────────────────────►
│  • WebSearch     │
│  • OutputFormat  │
└──────────────────┘
    │ draft article
    ▼
┌──────────────────┐
│  Content Editor  │
│  Agent           │
│  Tools:          │
│  • TextProcess   │
│  • OutputFormat  │
└──────────────────┘
    │ polished article
    ▼
ContentQualityAnalyzer  ← Custom Tool
    │
    ▼
Final Output + Metrics
```

### Agent Roles

| Agent | Role | Key Output |
|---|---|---|
| **Idea Generator** | Researches trends; produces 5-10 ranked ideas | Numbered list + `SELECTED IDEA:` |
| **Content Writer** | Turns selected idea into full structured article | Markdown article (400-700 words) |
| **Content Editor** | Fixes grammar, sharpens sentences, improves engagement | Polished publication-ready Markdown |

---

## Directory Structure

```
BuildAISystemAgent/
├── main.py                        ← Entry point / CLI
├── agents/
│   ├── __init__.py
│   ├── controller_agent.py        ← Orchestrator class
│   ├── idea_generator_agent.py
│   ├── content_writer_agent.py
│   └── content_editor_agent.py
├── tools/
│   ├── __init__.py
│   ├── web_search_tool.py         ← DuckDuckGo search
│   ├── text_processing_tool.py    ← Clean/summarise/format/keywords
│   ├── output_formatter_tool.py   ← Markdown/HTML/plain output
│   └── content_quality_analyzer.py  ← Custom heuristic scorer ★
├── utils/
│   ├── __init__.py
│   ├── memory.py                  ← Shared memory store
│   └── metrics.py                 ← Evaluation metrics dataclass
├── tests/
│   ├── __init__.py
│   └── test_cases.py              ← Unit + integration tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## How to Run

### 1. Clone / navigate to the project

```bash
cd BuildAISystemAgent
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 5. Run the system

```bash
# Default demo topic
python main.py

# Custom topic
python main.py --topic "Sustainable Energy Solutions"

# All three test cases
python main.py --test
```

### 6. Run unit tests (no API key needed)

```bash
python tests/test_cases.py
```

---

## Example Input / Output

**Input:**
```
Topic: "Artificial Intelligence in Healthcare"
```

**Output (abbreviated):**
```markdown
# How AI is Quietly Revolutionising Patient Care

Modern hospitals face a paradox: more data than ever, yet diagnostic
errors persist. Artificial intelligence is changing that — one scan at a time.

## AI-Powered Diagnostics

Deep learning models now analyse radiology images with accuracy
comparable to specialist physicians...

- Early cancer detection in mammograms (94 % accuracy)
- Diabetic retinopathy screening from a smartphone
- Real-time sepsis alerts in ICU patients

## Personalised Treatment Plans

...

## Ethical Considerations

Who is responsible when an algorithm makes a wrong call? ...

## Conclusion

AI will not replace doctors — it will make them superhuman.
```

**Metrics:**
```
  Response Time  : 42.31 seconds
  Content Length : 2,847 characters
  Quality Score  : 7.8 / 10
  Acceptable     : Yes ✅

  Breakdown:
    Length          ██████████  9.0
    Readability     ████████░░  8.0
    Engagement      ███████░░░  7.5
    Structure       ████████░░  7.8

  Suggestions:
    •  Add 1–2 rhetorical questions to engage readers.
    •  Consider expanding to 500+ words for best engagement.
```

---

## Tools Explanation

### 1. Web Search Tool (`tools/web_search_tool.py`)

Uses the `duckduckgo-search` library to fetch current trends and references. Falls back to curated mock results in offline mode.

**Input:** `query: str`, `max_results: int (1-10)`
**Output:** Numbered list of titles + 250-char snippets

### 2. Text Processing Tool (`tools/text_processing_tool.py`)

Four text-manipulation operations in a single tool:

| Operation | Effect |
|---|---|
| `clean` | Remove extra whitespace, tabs, excessive blank lines |
| `summarize` | Three-sentence extractive summary |
| `format` | Fix capitalisation and paragraph spacing |
| `extract_keywords` | Top-10 non-stop-word frequency list |

### 3. Output Formatter Tool (`tools/output_formatter_tool.py`)

Converts content to clean Markdown, minimal HTML5, or plain text.

| Format | Use Case |
|---|---|
| `markdown` | Blog platforms, GitHub, default |
| `html` | Web pages |
| `plain` | Email, plain-text export |

### 4. Content Quality Analyzer ★ (`tools/content_quality_analyzer.py`)

**Custom tool.** Scores content 1–10 across four dimensions:

| Dimension | Weight | What it checks |
|---|---|---|
| Length | 20 % | Word count vs. ideal range (400-1500) |
| Readability | 30 % | Average and max sentence length |
| Engagement | 30 % | Questions, headings, lists, emphasis |
| Structure | 20 % | Paragraph count, intro/conclusion detection |

Returns a score, per-dimension breakdown, and actionable suggestions.

---

## Test Cases

| # | Name | Input | Expected |
|---|---|---|---|
| 1 | Normal Topic | `"Artificial Intelligence in Healthcare"` | Complete article, score ≥ 5.0 |
| 2 | Vague Topic | `"technology"` | Valid article generated from narrowed angle |
| 3 | Empty Input | `""` | Graceful error, no crash |

Run with `python main.py --test`.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | — | Your OpenAI API key |
| `OPENAI_MODEL_NAME` | No | `gpt-4o-mini` | Model used by all agents |

---

## Dependencies

| Package | Purpose |
|---|---|
| `crewai` | Multi-agent orchestration framework |
| `crewai-tools` | BaseTool base class for custom tools |
| `openai` | LLM API access |
| `python-dotenv` | .env file loading |
| `duckduckgo-search` | Web search backend |
| `pydantic` | Tool input schema validation |
