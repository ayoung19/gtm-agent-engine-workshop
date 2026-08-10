"""Tests for the disqualified-prospect guard in send_prospect_email."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from langchain.tools import ToolRuntime

from gtm_agent.gtm_agent import send_prospect_email

FROM_REP = {"name": "Kavya Patel", "email": "kavya.patel@example.com"}


def _runtime():
    "Build a minimal ToolRuntime for calling a tool outside the agent loop."
    return ToolRuntime(
        state=None,
        context=None,
        config={"metadata": {"user_id": "REP-1001"}},
        stream_writer=None,
        tool_call_id=None,
        store=None,
    )


def test_send_to_disqualified_prospect_is_blocked():
    result = send_prospect_email.func(
        prospect={
            "prospect_id": "LEAD-50001",
            "name": "Priya Nair",
            "email": "priya.nair@brightwaveapps.com",
        },
        subject="Quick intro",
        body="Wanted to share our latest platform update.",
        runtime=_runtime(),
        from_rep=FROM_REP,
    )
    assert result["status"] == "blocked"
    assert result["prospect_id"] == "LEAD-50001"
    assert "message_id" not in result


def test_send_to_qualified_prospect_is_unchanged():
    result = send_prospect_email.func(
        prospect={
            "prospect_id": "LEAD-71001",
            "name": "Noah Williams",
            "email": "noah.williams@arcadiadata.com",
        },
        subject="Quick intro",
        body="Wanted to share our latest platform update.",
        runtime=_runtime(),
        from_rep=FROM_REP,
    )
    assert result["status"] == "sent"
    assert result["to"] == "noah.williams@arcadiadata.com"
