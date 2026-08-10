import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent.gtm_agent import get_prospect, send_prospect_email


class ProspectEmailTests(unittest.TestCase):
    def test_get_prospect_returns_contact_and_eligibility_only(self):
        record = {
            "name": "Example Prospect",
            "email": "prospect@example.com",
            "disqualified": True,
            "billing_qualification": {"card_on_file": "not-for-agent-use"},
            "annual_revenue": 100,
        }

        with patch("gtm_agent.gtm_agent.data_service.get_prospect_record", return_value=record):
            result = get_prospect.func("LEAD-1")

        self.assertEqual(
            result,
            {
                "prospect": {
                    "prospect_id": "LEAD-1",
                    "name": "Example Prospect",
                    "email": "prospect@example.com",
                    "disqualified": True,
                },
                "found": True,
            },
        )

    def test_send_blocks_disqualified_prospect_using_crm_eligibility(self):
        record = {
            "name": "Example Prospect",
            "email": "prospect@example.com",
            "disqualified": True,
        }
        prospect = {**record, "prospect_id": "LEAD-1", "disqualified": False}

        with patch("gtm_agent.gtm_agent.data_service.get_prospect_record", return_value=record):
            result = send_prospect_email.func(
                prospect,
                "Subject",
                "Body",
                None,
                {"name": "Example Rep", "email": "rep@example.com"},
            )

        self.assertEqual(
            result,
            {"status": "blocked", "error": "Prospect is disqualified and cannot be emailed."},
        )

    def test_send_allows_qualified_prospect(self):
        record = {
            "name": "Example Prospect",
            "email": "prospect@example.com",
            "disqualified": False,
        }
        prospect = {**record, "prospect_id": "LEAD-1"}

        with patch("gtm_agent.gtm_agent.data_service.get_prospect_record", return_value=record):
            result = send_prospect_email.func(
                prospect,
                "Subject",
                "Body",
                None,
                {"name": "Example Rep", "email": "rep@example.com"},
            )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["to"], "prospect@example.com")
        self.assertEqual(result["subject"], "Subject")
        self.assertEqual(result["body"], "Body")


if __name__ == "__main__":
    unittest.main()
