"""Regression tests for persistence of update_prospect_info writes."""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service
from gtm_agent.gtm_agent import build_prospect_profile
from gtm_agent.gtm_records import PROSPECTS

PROSPECT_ID = "LEAD-12853"
TECHNOLOGY = "Databricks"


@pytest.fixture(autouse=True)
def restore_records():
    original = list(PROSPECTS[PROSPECT_ID]["tech_stack"])
    data_service._PROFILES.pop(PROSPECT_ID, None)
    yield
    PROSPECTS[PROSPECT_ID]["tech_stack"] = original
    data_service._PROFILES.pop(PROSPECT_ID, None)


def test_update_persists_to_record():
    assert TECHNOLOGY not in data_service.fetch_tech_stack(PROSPECT_ID)

    result = data_service.update_prospect_info(PROSPECT_ID, TECHNOLOGY)

    assert result["updated"] is True
    assert TECHNOLOGY in data_service.fetch_tech_stack(PROSPECT_ID)


def test_update_invalidates_cached_profile():
    before = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert TECHNOLOGY not in before["prospect_profile"]["tech_stack"]

    data_service.update_prospect_info(PROSPECT_ID, TECHNOLOGY)

    after = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert TECHNOLOGY in after["prospect_profile"]["tech_stack"]


def test_repeat_update_is_a_no_op():
    data_service.update_prospect_info(PROSPECT_ID, TECHNOLOGY)

    result = data_service.update_prospect_info(PROSPECT_ID, TECHNOLOGY)

    assert result["updated"] is False
    assert result["found"] is True
    assert result["tech_stack"].count(TECHNOLOGY) == 1
