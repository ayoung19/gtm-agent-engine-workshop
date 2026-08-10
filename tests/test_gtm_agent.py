import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def test_disqualified_prospect_is_blocked_before_message_id_generation(self):
        prospect = {
            "prospect_id": "LEAD-50001",
            "name": "Outdated Name",
            "email": "outdated@example.com",
            "disqualified": False,
        }

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            result = send_prospect_email.func(
                prospect,
                "Hello",
                "Message body",
                None,
                {"name": "Sales Rep", "email": "rep@example.com"},
            )

        self.assertEqual(
            result,
            {
                "status": "blocked",
                "reason": "prospect_disqualified",
                "prospect_id": "LEAD-50001",
            },
        )
        uuid4.assert_not_called()

    def test_eligible_prospect_is_sent_using_authoritative_contact(self):
        prospect = {
            "prospect_id": "LEAD-12853",
            "name": "Outdated Name",
            "email": "outdated@example.com",
        }

        result = send_prospect_email.func(
            prospect,
            "Hello",
            "Message body",
            None,
            {"name": "Sales Rep", "email": "rep@example.com"},
        )

        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["message_id"].startswith("msg-"))
        self.assertEqual(result["to"], "omar.okafor@lakesideanalytics.com")
        self.assertEqual(result["to_name"], "Omar Okafor")
        self.assertEqual(result["from"], "rep@example.com")
        self.assertEqual(result["subject"], "Hello")
        self.assertEqual(result["body"], "Message body")


if __name__ == "__main__":
    unittest.main()
