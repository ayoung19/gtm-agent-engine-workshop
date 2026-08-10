"""Regression tests for persisting prospect tech-stack updates."""

import json
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent import gtm_agent as agent_module
from gtm_agent.gtm_records import PROSPECTS

PROSPECT_ID = "LEAD-71001"
OFFERING_ID = "OFFER-10005"
NEW_TECH = "Kafka"


@pytest.fixture(autouse=True)
def restore_records():
    original = list(PROSPECTS[PROSPECT_ID]["tech_stack"])
    data_service._PROFILES.pop(PROSPECT_ID, None)
    yield
    PROSPECTS[PROSPECT_ID]["tech_stack"] = original
    data_service._PROFILES.pop(PROSPECT_ID, None)


class _StubScoringLLM:
    "Scoring stand-in that names the required technologies absent from the profile it receives."

    def invoke(self, messages):
        offering_json, profile_json = messages[-1]["content"].split("\n\nProspect profile:\n")
        offering = json.loads(offering_json.split("Offering:\n", 1)[1])
        profile = json.loads(profile_json)
        missing = [t for t in offering["required_tech_stack"] if t not in profile["tech_stack"]]
        justification = (
            "Missing required technologies: " + ", ".join(missing) if missing
            else "The prospect has every required technology."
        )
        return agent_module.ProspectScore(
            score=100.0 - 10.0 * len(missing),
            justification=justification,
            rubric_breakdown=agent_module.RubricBreakdown(
                revenue_fit=100.0,
                tech_stack_match=100.0 - 10.0 * len(missing),
                segment_fit=100.0,
            ),
        )


def test_update_is_visible_to_the_source_of_record():
    result = data_service.update_prospect_info(PROSPECT_ID, NEW_TECH)
    assert result == {
        "updated": True,
        "found": True,
        "tech_stack": PROSPECTS[PROSPECT_ID]["tech_stack"],
    }
    assert NEW_TECH in data_service.fetch_tech_stack(PROSPECT_ID)


def test_update_invalidates_the_cached_profile():
    built = agent_module.build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert NEW_TECH not in built["prospect_profile"]["tech_stack"]
    data_service.update_prospect_info(PROSPECT_ID, NEW_TECH)
    assert data_service.get_profile_from_db(PROSPECT_ID)["prospect_profile"] is None
    rebuilt = agent_module.build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert NEW_TECH in rebuilt["prospect_profile"]["tech_stack"]


def test_update_reports_no_op_when_technology_already_present():
    data_service.update_prospect_info(PROSPECT_ID, NEW_TECH)
    result = data_service.update_prospect_info(PROSPECT_ID, NEW_TECH)
    assert result["updated"] is False
    assert result["already_present"] is True
    assert PROSPECTS[PROSPECT_ID]["tech_stack"].count(NEW_TECH) == 1


def test_score_after_update_does_not_report_technology_as_missing(monkeypatch):
    monkeypatch.setattr(agent_module, "_scoring_llm", _StubScoringLLM())
    profile = agent_module.build_prospect_profile.invoke(
        {"prospect_id": PROSPECT_ID})["prospect_profile"]
    offering = agent_module.lookup_offering.invoke({"offering_id": OFFERING_ID})["offering"]

    before = agent_module.score_prospect.invoke(
        {"prospect_profile": profile, "offering": offering})
    assert NEW_TECH in before["justification"]

    data_service.update_prospect_info(PROSPECT_ID, NEW_TECH)

    after = agent_module.score_prospect.invoke(
        {"prospect_profile": profile, "offering": offering})
    assert NEW_TECH not in after["justification"]
    assert after["score"] > before["score"]
