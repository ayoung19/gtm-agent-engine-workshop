"""Tests that the prospect lookup tools never expose billing/identity data."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service
from gtm_agent.gtm_agent import build_prospect_profile, get_prospect

PROSPECT_ID = "LEAD-12853"

SENSITIVE_KEYS = (
    "billing_qualification",
    "tax_id",
    "date_of_birth",
    "card_on_file",
    "credit_check_ref",
)


def _assert_no_sensitive_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in SENSITIVE_KEYS, f"sensitive key exposed: {key}"
            _assert_no_sensitive_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_sensitive_keys(item)


def test_get_prospect_omits_sensitive_fields():
    result = get_prospect.invoke({"prospect_id": PROSPECT_ID})
    assert result["found"] is True
    _assert_no_sensitive_keys(result)
    assert result["prospect"]["email"] == data_service.get_prospect_record(PROSPECT_ID)["email"]
    assert result["prospect"]["disqualified"] is False


def test_build_prospect_profile_omits_sensitive_fields():
    result = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})
    assert result["found"] is True
    _assert_no_sensitive_keys(result)
    profile = result["prospect_profile"]
    assert profile["annual_revenue"] and profile["enrichment_source"] and profile["tech_stack"]
    _assert_no_sensitive_keys(data_service.get_profile_from_db(PROSPECT_ID))
