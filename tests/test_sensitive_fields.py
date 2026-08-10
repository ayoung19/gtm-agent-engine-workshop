"""Regulated prospect billing data must never reach the agent or a prompt."""

import json
import os

# ChatOpenAI is constructed at import time by gtm_agent; no request is made here.
os.environ.setdefault("OPENAI_API_KEY", "placeholder-not-a-credential")

from gtm_agent import data_service
from gtm_agent.gtm_agent import (
    _build_scoring_payload,
    build_prospect_profile,
    get_prospect,
)

PROSPECT_ID = "LEAD-12853"

SENSITIVE_KEYS = (
    "billing_qualification",
    "tax_id",
    "date_of_birth",
    "card_on_file",
    "credit_check_ref",
)


def assert_no_sensitive_keys(payload):
    serialized = json.dumps(payload, default=str)
    for key in SENSITIVE_KEYS:
        assert key not in serialized, f"{key} leaked into {serialized[:200]}"


def test_get_prospect_record_is_redacted():
    assert_no_sensitive_keys(data_service.get_prospect_record(PROSPECT_ID))


def test_get_prospect_returns_only_allow_listed_fields():
    result = get_prospect.invoke({"prospect_id": PROSPECT_ID})
    assert result["found"] is True
    assert set(result["prospect"]) <= {"prospect_id", "name", "email", "disqualified"}
    assert_no_sensitive_keys(result)


def test_build_prospect_profile_and_cache_are_redacted():
    data_service._PROFILES.clear()
    result = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert_no_sensitive_keys(result)
    assert_no_sensitive_keys(data_service._PROFILES[PROSPECT_ID])


def test_build_prospect_profile_redacts_stale_cache_entry():
    data_service._PROFILES.clear()
    data_service._PROFILES[PROSPECT_ID] = {
        "prospect_id": PROSPECT_ID,
        "billing_qualification": {"tax_id": "PLACEHOLDER"},
    }
    result = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert_no_sensitive_keys(result)
    data_service._PROFILES.clear()


def test_scoring_payload_only_carries_scoring_fields():
    profile = dict(data_service.PROSPECTS[PROSPECT_ID], prospect_id=PROSPECT_ID)
    payload = _build_scoring_payload(profile)
    assert set(payload) == {"prospect_id", "annual_revenue", "account_details", "tech_stack"}
    assert_no_sensitive_keys(payload)
