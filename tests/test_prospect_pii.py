"""Prospect lookups must not hand billing PII to the model."""

import json
import os

import pytest

# The agent module builds a ChatOpenAI client at import time; no call is made.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import build_prospect_profile, get_prospect
from gtm_agent.gtm_records import PROSPECTS

SENSITIVE_KEYS = ("billing_qualification", "tax_id", "card_on_file", "credit_check_ref")


@pytest.mark.parametrize("prospect_id", sorted(PROSPECTS))
def test_prospect_tools_withhold_billing_fields(prospect_id):
    for tool in (get_prospect, build_prospect_profile):
        payload = json.dumps(tool.invoke({"prospect_id": prospect_id}))
        for key in SENSITIVE_KEYS:
            assert key not in payload, f"{tool.name} leaked {key} for {prospect_id}"
