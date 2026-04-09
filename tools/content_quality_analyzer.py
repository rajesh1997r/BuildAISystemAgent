"""
Custom Content Quality Analyzer Tool  (MANDATORY CUSTOM TOOL)
=============================================================
Evaluates generated content using rule-based heuristics across
four dimensions:

  1. Length      – word-count adequacy
  2. Readability – average sentence length
  3. Engagement  – headings, questions, lists, emphasis
  4. Structure   – paragraphs, intro/conclusion signals

Returns:
    score       : float  1–10
    suggestions : list[str]  actionable improvement tips
    breakdown   : dict   per-dimension scores
"""
import re
from typing import Dict, List, Tuple, Any


class ContentQualityAnalyzer:
    """
    Heuristic content quality analyzer with full input validation.

    Usage::

        analyzer = ContentQualityAnalyzer()
        result   = analyzer.analyze(my_article_text)
        print(result["score"])          # e.g. 7.8
        print(result["suggestions"])    # list of strings
    """

    # Tuning constants
    MIN_WORDS_IDEAL = 400
    MAX_AVG_SENTENCE_WORDS = 25
    MAX_SENTENCE_WORDS = 35
    LONG_SENTENCE_THRESHOLD = 0.30   # fraction of sentences that may be long

    def analyze(self, content: Any) -> Dict:
        """
        Analyse *content* and return a quality report.

        Args:
            content: The article / blog text to evaluate (must be a string).

        Returns:
            {
              "score":       float (1–10),
              "suggestions": list[str],
              "breakdown":   {"length": f, "readability": f,
                              "engagement": f, "structure": f}
            }
        """
        # ---- Input validation ------------------------------------------------
        if content is None or content == "":
            return self._error_result("Content is empty. Please provide valid content.")

        if not isinstance(content, str):
            return self._error_result(
                f"Invalid input type '{type(content).__name__}'. Content must be a string."
            )

        content = content.strip()

        if len(content) < 20:
            return {
                "score": 1.0,
                "suggestions": [
                    "Content is too short to evaluate meaningfully. "
                    "Please provide at least a full paragraph."
                ],
                "breakdown": {"length": 1, "readability": 1, "engagement": 1, "structure": 1},
            }

        # ---- Run sub-analyses ------------------------------------------------
        length_score,      length_tips      = self._analyze_length(content)
        readability_score, readability_tips = self._analyze_readability(content)
        engagement_score,  engagement_tips  = self._analyze_engagement(content)
        structure_score,   structure_tips   = self._analyze_structure(content)

        # ---- Weighted aggregation --------------------------------------------
        weights = [0.20, 0.30, 0.30, 0.20]
        scores  = [length_score, readability_score, engagement_score, structure_score]
        final   = sum(s * w for s, w in zip(scores, weights))
        final   = round(max(1.0, min(10.0, final)), 1)

        suggestions = length_tips + readability_tips + engagement_tips + structure_tips
        if not suggestions:
            suggestions = ["Content quality looks great! Minor polishing may still add value."]

        return {
            "score": final,
            "suggestions": suggestions,
            "breakdown": {
                "length":      round(length_score,      1),
                "readability": round(readability_score,  1),
                "engagement":  round(engagement_score,   1),
                "structure":   round(structure_score,    1),
            },
        }

    # ------------------------------------------------------------------ #
    # Sub-analyses
    # ------------------------------------------------------------------ #

    def _analyze_length(self, content: str) -> Tuple[float, List[str]]:
        """Score based on word count relative to ideal range."""
        word_count = len(content.split())
        suggestions: List[str] = []

        if word_count < 100:
            score = 3.0
            suggestions.append(
                f"Content is very short ({word_count} words). "
                "Aim for at least 300–500 words for a meaningful article."
            )
        elif word_count < 300:
            score = 6.0
            suggestions.append(
                f"Content length ({word_count} words) is below recommended. "
                "Expand to 400–700 words for best engagement."
            )
        elif word_count < self.MIN_WORDS_IDEAL:
            score = 8.0
        elif word_count <= 1500:
            score = 10.0
        else:
            score = 7.0
            suggestions.append(
                f"Content is quite long ({word_count} words). "
                "Consider condensing to keep readers engaged."
            )

        return score, suggestions

    def _analyze_readability(self, content: str) -> Tuple[float, List[str]]:
        """Score based on average and maximum sentence length."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip()]
        suggestions: List[str] = []

        if not sentences:
            return 5.0, ["Could not detect sentence structure."]

        word_counts   = [len(s.split()) for s in sentences]
        avg_length    = sum(word_counts) / len(word_counts)
        long_count    = sum(1 for wc in word_counts if wc > self.MAX_SENTENCE_WORDS)
        long_fraction = long_count / len(sentences)

        score = 10.0

        if avg_length > self.MAX_AVG_SENTENCE_WORDS:
            score -= 3.0
            suggestions.append(
                f"Average sentence length is {avg_length:.0f} words (target ≤ 20). "
                "Break long sentences for better readability."
            )
        elif avg_length > 20:
            score -= 1.5
            suggestions.append(
                "Some sentences are quite long. Aim for 15–20 words on average."
            )

        if long_fraction > self.LONG_SENTENCE_THRESHOLD:
            score -= 2.0
            suggestions.append(
                f"{long_count} sentence(s) exceed {self.MAX_SENTENCE_WORDS} words. "
                "Split them into shorter, punchier sentences."
            )

        return max(1.0, score), suggestions

    def _analyze_engagement(self, content: str) -> Tuple[float, List[str]]:
        """Score based on questions, headings, lists, and emphasis."""
        suggestions: List[str] = []
        score = 5.0

        # Questions engage readers
        question_count = content.count("?")
        if question_count >= 2:
            score += 1.5
        elif question_count == 1:
            score += 0.75
        else:
            suggestions.append(
                "Add 1–2 rhetorical or thought-provoking questions to engage readers."
            )

        # Markdown headings improve scannability
        heading_count = len(re.findall(r"^#{1,6}\s", content, re.MULTILINE))
        if heading_count >= 3:
            score += 2.0
        elif heading_count >= 1:
            score += 1.0
        else:
            suggestions.append(
                "Add section headings (## Heading) to break up the text and guide readers."
            )

        # Bullet / numbered lists
        has_list = bool(re.search(r"^[\-\*\•\d+\.]\s", content, re.MULTILINE))
        if has_list:
            score += 1.0
        else:
            suggestions.append(
                "Include bullet points or a numbered list to highlight key takeaways."
            )

        # Bold emphasis
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", content))
        if has_bold:
            score += 0.5

        return min(10.0, score), suggestions

    def _analyze_structure(self, content: str) -> Tuple[float, List[str]]:
        """Score based on paragraph count and intro/conclusion signals."""
        suggestions: List[str] = []
        score = 5.0

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if len(paragraphs) >= 5:
            score += 3.5
        elif len(paragraphs) >= 3:
            score += 2.0
        elif len(paragraphs) >= 2:
            score += 1.0
            suggestions.append(
                "Add more paragraph / section breaks to improve readability."
            )
        else:
            suggestions.append(
                "Structure content into multiple sections with clear paragraph breaks."
            )

        # Conclusion detection
        conclusion_kw = [
            "conclusion", "in summary", "to summarize", "in closing",
            "finally,", "to conclude", "wrap up", "in short",
        ]
        if any(kw in content.lower() for kw in conclusion_kw):
            score += 1.5
        else:
            suggestions.append(
                "Add a clear conclusion or 'Key Takeaways' section to round off the article."
            )

        # Introduction detection
        intro_kw = [
            "introduction", "in this article", "this post", "we will explore",
            "this guide", "overview", "let's dive",
        ]
        if any(kw in content.lower() for kw in intro_kw):
            score += 0.5

        return min(10.0, score), suggestions

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _error_result(message: str) -> Dict:
        """Return a standardized error result."""
        return {
            "score": 0,
            "suggestions": [message],
            "breakdown": {"length": 0, "readability": 0, "engagement": 0, "structure": 0},
        }
