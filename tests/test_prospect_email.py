import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service
from gtm_agent.gtm_agent import SYSTEM_PROMPT, send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={"metadata": {"user_id": "REP-10001"}})
        self.rep = {"name": "Test Rep", "email": "rep@example.com"}

    def test_direct_send_succeeds_for_eligible_prospect(self):
        prospect = {"prospect_id": "LEAD-12853", "name": "Stale Name", "email": "stale@example.com"}

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            uuid4.return_value.hex = "1234567890abcdef"
            result = send_prospect_email.func(
                prospect,
                "Hello",
                "Checking in.",
                self.runtime,
                self.rep,
            )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], "msg-1234567890ab")
        self.assertEqual(result["to"], data_service.get_prospect_record("LEAD-12853")["email"])
        uuid4.assert_called_once_with()

    def test_direct_send_is_blocked_for_currently_disqualified_prospect(self):
        prospect = {
            "prospect_id": "LEAD-50001",
            "name": "Priya Nair",
            "email": "priya.nair@brightwaveapps.com",
            "disqualified": False,
        }

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            result = send_prospect_email.func(
                prospect,
                "Hello",
                "Checking in.",
                self.runtime,
                self.rep,
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("disqualified", result["error"])
        self.assertNotIn("message_id", result)
        uuid4.assert_not_called()

    def test_agent_must_report_a_block_instead_of_success(self):
        self.assertIn("clearly tell the rep the send was blocked", SYSTEM_PROMPT)
        self.assertIn("never claim that the email was sent", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
