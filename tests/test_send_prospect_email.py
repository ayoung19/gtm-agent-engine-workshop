"""Tests for the disqualified-prospect guard in send_prospect_email."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from langchain.tools import ToolRuntime

from gtm_agent.gtm_agent import send_prospect_email

RUNTIME = ToolRuntime(state=None, context=None, config={"metadata": {}}, stream_writer=None, tool_call_id=None, store=None)

DISQUALIFIED = {"prospect_id": "LEAD-50001", "name": "Priya Nair", "email": "priya.nair@brightwaveapps.com"}
QUALIFIED = {"prospect_id": "LEAD-12853", "name": "Omar Okafor", "email": "omar.okafor@lakesideanalytics.com"}


def _send(prospect, **kwargs):
    return send_prospect_email.invoke({
        "prospect": prospect,
        "subject": "Book a demo",
        "body": "Are you free this week?",
        "runtime": RUNTIME,
        "from_rep": {"name": "Marco Rossi", "email": "marco.rossi@example.com"},
        **kwargs,
    })


def test_disqualified_prospect_is_blocked():
    result = _send(DISQUALIFIED)
    assert result["status"] == "blocked"
    assert result["reason"] == "prospect_disqualified"
    assert result["prospect_id"] == "LEAD-50001"
    assert "message_id" not in result


def test_disqualified_prospect_sends_with_override():
    result = _send(DISQUALIFIED, override_disqualified=True)
    assert result["status"] == "sent"
    assert result["message_id"]


def test_qualified_prospect_still_sends():
    result = _send(QUALIFIED)
    assert result["status"] == "sent"
    assert result["message_id"]
