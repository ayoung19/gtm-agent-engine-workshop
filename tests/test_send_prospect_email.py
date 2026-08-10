import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={"metadata": {"user_id": "REP-1001"}})
        self.rep = {"name": "Test Rep", "email": "rep@example.com"}

    def test_disqualified_prospect_is_blocked_before_send(self):
        prospect = {
            "prospect_id": "LEAD-50001",
            "name": "Priya Nair",
            "email": "priya.nair@brightwaveapps.com",
            "disqualified": False,
        }

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            result = send_prospect_email.func(
                prospect=prospect,
                subject="Following up",
                body="Hello",
                runtime=self.runtime,
                from_rep=self.rep,
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["prospect_id"], "LEAD-50001")
        self.assertIn("disqualified", result["error"])
        uuid4.assert_not_called()

    def test_eligible_prospect_is_sent(self):
        prospect = {
            "prospect_id": "LEAD-12853",
            "name": "Omar Okafor",
            "email": "omar.okafor@lakesideanalytics.com",
            "disqualified": True,
        }

        result = send_prospect_email.func(
            prospect=prospect,
            subject="Following up",
            body="Hello",
            runtime=self.runtime,
            from_rep=self.rep,
        )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["to"], "omar.okafor@lakesideanalytics.com")
        self.assertEqual(result["from"], "rep@example.com")


if __name__ == "__main__":
    unittest.main()
