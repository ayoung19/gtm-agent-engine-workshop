"""Regression tests for the disqualified-prospect guard in send_prospect_email."""

from types import SimpleNamespace

from gtm_agent import data_service
from gtm_agent.gtm_agent import send_prospect_email

REP = {"rep_id": "REP-1", "name": "Dana Rep", "email": "dana.rep@example.com"}

DISQUALIFIED_ID = "LEAD-50001"
QUALIFIED_ID = "LEAD-12853"

SUCCESS_KEYS = {
    "status", "message_id", "to", "to_name", "from", "from_name", "subject", "body",
}


def _send(prospect_id, **extra):
    record = data_service.get_prospect_record(prospect_id)
    prospect = {"prospect_id": prospect_id, "name": record["name"], "email": record["email"]}
    return send_prospect_email.func(
        prospect=prospect,
        subject="Quick question",
        body="Hello there.",
        runtime=SimpleNamespace(config={}),
        from_rep=REP,
        **extra,
    )


def test_disqualified_prospect_is_blocked():
    result = _send(DISQUALIFIED_ID)
    assert result == {
        "status": "blocked",
        "reason": "prospect is disqualified",
        "prospect_id": DISQUALIFIED_ID,
    }


def test_disqualified_prospect_sends_with_override():
    result = _send(DISQUALIFIED_ID, override_disqualified=True)
    assert set(result) == SUCCESS_KEYS
    assert result["status"] == "sent"
    assert result["to"] == "priya.nair@brightwaveapps.com"
    assert result["from"] == REP["email"]


def test_qualified_prospect_sends_as_before():
    result = _send(QUALIFIED_ID)
    assert set(result) == SUCCESS_KEYS
    assert result["status"] == "sent"
    assert result["subject"] == "Quick question"
    assert result["body"] == "Hello there."
