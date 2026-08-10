import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service
from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={"metadata": {"user_id": "rep_amills"}})

    def send(self, prospect):
        return send_prospect_email.func(
            prospect,
            "Introduction",
            "Would you like to learn more?",
            self.runtime,
        )

    def test_disqualified_prospects_are_blocked(self):
        for prospect_id in (
            "LEAD-50001",
            "LEAD-50002",
            "LEAD-50003",
            "LEAD-50004",
            "LEAD-50005",
        ):
            with self.subTest(prospect_id=prospect_id):
                prospect = {
                    "prospect_id": prospect_id,
                    **data_service.get_prospect_record(prospect_id),
                }

                result = self.send(prospect)

                self.assertEqual(
                    result,
                    {
                        "status": "blocked",
                        "error": "Outreach is blocked until prospect eligibility is resolved.",
                    },
                )

    def test_disqualified_source_record_cannot_be_bypassed(self):
        prospect = {
            "prospect_id": "LEAD-50001",
            "name": "Priya Nair",
            "email": "priya.nair@brightwaveapps.com",
        }

        result = self.send(prospect)

        self.assertEqual(result["status"], "blocked")

    def test_qualified_prospect_email_is_sent(self):
        prospect_id = "LEAD-90002"
        prospect = {
            "prospect_id": prospect_id,
            **data_service.get_prospect_record(prospect_id),
        }

        result = self.send(prospect)

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["to"], prospect["email"])
        self.assertEqual(result["from"], "ava.mills@northpoint.com")
        self.assertEqual(result["subject"], "Introduction")
        self.assertEqual(result["body"], "Would you like to learn more?")


if __name__ == "__main__":
    unittest.main()
