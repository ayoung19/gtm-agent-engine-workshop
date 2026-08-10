import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service
from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def test_blocks_all_disqualified_prospects_before_creating_message_id(self):
        prospect_ids = (
            "LEAD-50001",
            "LEAD-50002",
            "LEAD-50003",
            "LEAD-50004",
            "LEAD-50005",
        )

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            for prospect_id in prospect_ids:
                with self.subTest(prospect_id=prospect_id):
                    prospect = data_service.get_prospect_record(prospect_id)
                    result = send_prospect_email.func(
                        prospect,
                        "Hello",
                        "Message body",
                        runtime=None,
                        from_rep={"name": "Ava Mills", "email": "ava@example.com"},
                    )
                    self.assertEqual(
                        result,
                        {"status": "blocked", "reason": "prospect_disqualified"},
                    )

            uuid4.assert_not_called()

    def test_sends_email_to_eligible_prospect(self):
        prospect = data_service.get_prospect_record("LEAD-12853")

        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            uuid4.return_value.hex = "1234567890abcdef"
            result = send_prospect_email.func(
                prospect,
                "Hello",
                "Message body",
                runtime=None,
                from_rep={"name": "Ava Mills", "email": "ava@example.com"},
            )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], "msg-1234567890ab")
        self.assertEqual(result["to"], prospect["email"])
        self.assertEqual(result["from"], "ava@example.com")


if __name__ == "__main__":
    unittest.main()
