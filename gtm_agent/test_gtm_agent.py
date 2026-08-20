import os
import sys
from pathlib import Path


repo_root = Path(__file__).parent
sys.path.remove(str(repo_root))
sys.path.insert(0, str(repo_root.parent))
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import ProspectScore, RubricBreakdown, score_prospect


class FakeScoringLLM:
    def __init__(self, segment_fit):
        self.segment_fit = segment_fit

    def invoke(self, messages):
        return ProspectScore(
            score=85,
            justification="Scored from available components.",
            rubric_breakdown=RubricBreakdown(
                revenue_fit=100,
                tech_stack_match=70,
                segment_fit=self.segment_fit,
            ),
        )


def offering():
    return {
        "required_tech_stack": ["Snowflake"],
        "min_annual_revenue": 1,
        "description": "Test offering",
        "target_segment": "Enterprise",
    }


def test_score_prospect_nulls_segment_fit_without_prospect_segment(monkeypatch):
    import gtm_agent.gtm_agent as module

    monkeypatch.setattr(module, "_scoring_llm", FakeScoringLLM(100))

    result = score_prospect.invoke(
        {"prospect_profile": {"annual_revenue": 10}, "offering": offering()}
    )

    assert result["rubric_breakdown"]["segment_fit"] is None


def test_score_prospect_preserves_numeric_segment_fit_with_prospect_segment(monkeypatch):
    import gtm_agent.gtm_agent as module

    monkeypatch.setattr(module, "_scoring_llm", FakeScoringLLM(75))

    result = score_prospect.invoke(
        {
            "prospect_profile": {"annual_revenue": 10, "segment": "Enterprise"},
            "offering": offering(),
        }
    )

    assert result["rubric_breakdown"]["segment_fit"] == 75
