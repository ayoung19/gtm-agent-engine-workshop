"""Prospect read paths must never hand billing identity data to the model."""

import os

# Importing the agent module constructs the chat models at import time.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service
from gtm_agent.gtm_agent import build_prospect_profile, get_prospect
from gtm_agent.gtm_records import PROSPECTS

SENSITIVE_KEYS = ("billing_qualification", "tax_id", "date_of_birth",
                  "card_on_file", "credit_check_ref")


def _sensitive_keys_in(payload):
    if isinstance(payload, dict):
        found = [k for k in payload if k in SENSITIVE_KEYS]
        for value in payload.values():
            found.extend(_sensitive_keys_in(value))
        return found
    if isinstance(payload, list):
        return [k for item in payload for k in _sensitive_keys_in(item)]
    return []


def test_source_records_still_carry_billing_qualification():
    assert all("billing_qualification" in rec for rec in PROSPECTS.values())


def test_get_prospect_returns_no_sensitive_fields():
    for prospect_id in PROSPECTS:
        result = get_prospect.invoke({"prospect_id": prospect_id})
        assert _sensitive_keys_in(result) == []
        assert set(result["prospect"]) == {"prospect_id", "name", "email",
                                           "disqualified", "annual_revenue",
                                           "enrichment_source"}


def test_build_prospect_profile_neither_returns_nor_persists_sensitive_fields():
    data_service._PROFILES.clear()
    for prospect_id in PROSPECTS:
        result = build_prospect_profile.invoke({"prospect_id": prospect_id})
        assert _sensitive_keys_in(result) == []
        cached = data_service.get_profile_from_db(prospect_id)["prospect_profile"]
        assert cached is not None
        assert _sensitive_keys_in(cached) == []
    data_service._PROFILES.clear()


def test_redact_leaves_other_fields_intact():
    record = PROSPECTS["LEAD-12853"]
    redacted = data_service.redact(record)
    assert "billing_qualification" not in redacted
    assert redacted["email"] == record["email"]
    assert data_service.redact(None) is None
