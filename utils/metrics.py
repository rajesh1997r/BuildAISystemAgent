"""
Evaluation Metrics for the Content Creation Pipeline.

Tracks response time, content length, and quality score,
then exposes helper methods for display and export.
"""
from dataclasses import dataclass, asdict, field
from typing import Dict


@dataclass
class EvaluationMetrics:
    """
    Aggregated performance and quality metrics for one pipeline run.

    Attributes:
        response_time  : Wall-clock seconds from start to finish.
        content_length : Character count of the final content.
        quality_score  : Score 1-10 returned by ContentQualityAnalyzer.
    """
    response_time: float
    content_length: int
    quality_score: float

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #

    def print_metrics(self) -> None:
        """Pretty-print all metrics to stdout."""
        print(f"  Response Time  : {self.response_time:.2f} seconds")
        print(f"  Content Length : {self.content_length:,} characters")
        print(f"  Quality Score  : {self.quality_score:.1f} / 10")
        print(f"  Acceptable     : {'Yes ✅' if self.is_acceptable() else 'No ❌'}")

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict:
        """Convert metrics to a plain dictionary."""
        return asdict(self)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def is_acceptable(self) -> bool:
        """
        Return True when the run meets minimum quality thresholds:
          - Content has at least 100 characters
          - Quality score is 5.0 or higher
          - Pipeline finished within 5 minutes
        """
        return (
            self.content_length > 100
            and self.quality_score >= 5.0
            and self.response_time < 300
        )
