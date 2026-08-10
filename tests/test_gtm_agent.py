import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def test_disqualified_prospect_requests_are_blocked(self):
        requests = (
            ("Product introduction", "Sharing an introduction."),
            ("Following up", "Following up on your request."),
            ("Meeting request", "Would you like to meet?"),
            ("Event invitation", "You are invited to our event."),
            ("Account update", "Here is an account update."),
        )

        for subject, body in requests:
            with self.subTest(subject=subject):
                result = send_prospect_email.func(
                    prospect={
                        "prospect_id": "TEST-DISQUALIFIED",
                        "name": "Test Prospect",
                        "email": "disqualified@test.invalid",
                        "disqualified": True,
                    },
                    subject=subject,
                    body=body,
                    runtime=None,
                )

                self.assertEqual(
                    result,
                    {"status": "blocked", "reason": "prospect_disqualified"},
                )
                self.assertNotIn("message_id", result)

    def test_qualified_prospect_request_is_sent(self):
        result = send_prospect_email.func(
            prospect={
                "prospect_id": "TEST-QUALIFIED",
                "name": "Test Prospect",
                "email": "qualified@test.invalid",
                "disqualified": False,
            },
            subject="Product introduction",
            body="Sharing an introduction.",
            runtime=None,
            from_rep={"name": "Test Rep", "email": "rep@test.invalid"},
        )

        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["message_id"].startswith("msg-"))


if __name__ == "__main__":
    unittest.main()
