import os
import unittest
from types import SimpleNamespace

os.environ["LANGSMITH_TRACING"] = "false"
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import get_prospect, send_prospect_email


class ProspectEmailPolicyTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={"metadata": {"user_id": "rep_amills"}})
        self.rep = {"name": "Ava Mills", "email": "ava.mills@northpoint.com"}

    def test_get_prospect_returns_safe_disqualification_status(self):
        result = get_prospect.func("LEAD-50001")

        self.assertEqual(
            result,
            {
                "prospect": {
                    "prospect_id": "LEAD-50001",
                    "name": "Priya Nair",
                    "email": "priya.nair@brightwaveapps.com",
                    "disqualified": True,
                },
                "found": True,
            },
        )

    def test_disqualified_prospect_is_blocked_without_message_id(self):
        result = send_prospect_email.func(
            {
                "prospect_id": "LEAD-50001",
                "name": "Priya Nair",
                "email": "priya.nair@brightwaveapps.com",
                "disqualified": False,
            },
            "Hello",
            "Would you like to talk?",
            self.runtime,
            self.rep,
        )

        self.assertEqual(
            result,
            {"status": "blocked", "reason": "prospect_disqualified"},
        )
        self.assertNotEqual(result["status"], "sent")
        self.assertNotIn("message_id", result)

    def test_qualified_prospect_is_sent(self):
        prospect = get_prospect.func("LEAD-12853")["prospect"]

        result = send_prospect_email.func(
            prospect,
            "Hello",
            "Would you like to talk?",
            self.runtime,
            self.rep,
        )

        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["message_id"].startswith("msg-"))
        self.assertEqual(result["to"], "omar.okafor@lakesideanalytics.com")


if __name__ == "__main__":
    unittest.main()
