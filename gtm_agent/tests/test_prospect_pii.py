"""Prospect-facing tools must never surface billing PII."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent.gtm_agent import build_prospect_profile, get_prospect

PROSPECT_ID = "LEAD-12853"
SENSITIVE_FIELDS = ("tax_id", "date_of_birth", "card_on_file", "credit_check_ref")


def _assert_clean(payload):
    assert "billing_qualification" not in payload
    flat = repr(payload)
    for field in SENSITIVE_FIELDS:
        assert field not in flat


def test_get_prospect_record_scrubs_billing_qualification():
    _assert_clean(data_service.get_prospect_record(PROSPECT_ID))


def test_get_prospect_returns_only_safe_fields():
    prospect = get_prospect.invoke({"prospect_id": PROSPECT_ID})["prospect"]
    _assert_clean(prospect)
    assert prospect["name"] and prospect["email"] and prospect["annual_revenue"]


def test_build_prospect_profile_returns_and_saves_no_billing_data():
    data_service._PROFILES.pop(PROSPECT_ID, None)
    profile = build_prospect_profile.invoke({"prospect_id": PROSPECT_ID})["prospect_profile"]
    _assert_clean(profile)
    assert profile["name"] and profile["email"] and profile["annual_revenue"]
    saved = data_service.get_profile_from_db(PROSPECT_ID)["prospect_profile"]
    _assert_clean(saved)
