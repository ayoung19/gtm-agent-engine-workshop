"""Tests for the send_prospect_email disqualified-prospect guard."""

import os
from types import SimpleNamespace

# Importing the agent module constructs the chat models at import time.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent.gtm_agent import send_prospect_email

send_email = send_prospect_email.func
RUNTIME = SimpleNamespace(config={"metadata": {"user_id": ""}})


def test_disqualified_prospect_is_blocked():
    prospect = {
        "prospect_id": "LEAD-12853",
        "name": "Omar Okafor",
        "email": "omar.okafor@lakesideanalytics.com",
        "disqualified": True,
    }
    result = send_email(prospect, "Subject", "Body", RUNTIME, from_rep={})
    assert result["status"] == "blocked"
    assert result["reason"] == "prospect is disqualified"
    assert result["prospect_id"] == "LEAD-12853"
    assert "message_id" not in result


def test_active_prospect_is_sent():
    prospect = {
        "prospect_id": "LEAD-12853",
        "name": "Omar Okafor",
        "email": "omar.okafor@lakesideanalytics.com",
        "disqualified": False,
    }
    result = send_email(prospect, "Subject", "Body", RUNTIME, from_rep={})
    assert result["status"] == "sent"
    assert result["message_id"]
    assert result["to"] == "omar.okafor@lakesideanalytics.com"


def test_prospect_without_email_fails():
    prospect = {"prospect_id": "LEAD-12853", "name": "Omar Okafor"}
    result = send_email(prospect, "Subject", "Body", RUNTIME, from_rep={})
    assert result["status"] == "failed"
