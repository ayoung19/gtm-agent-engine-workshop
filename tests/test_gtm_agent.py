import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import gtm_agent as agent_module


class SendProspectEmailTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={"metadata": {"user_id": "REP-10001"}})
        self.rep = {"name": "Sales Rep", "email": "rep@example.com"}

    @patch.object(agent_module, "_send_email_via_provider")
    def test_disqualified_canonical_prospect_is_blocked(self, send_email):
        result = agent_module.send_prospect_email.func(
            prospect={
                "prospect_id": "LEAD-50001",
                "name": "Eligible Name",
                "email": "eligible@example.com",
                "disqualified": False,
            },
            subject="Introduction",
            body="Let's connect.",
            runtime=self.runtime,
            from_rep=self.rep,
        )

        self.assertEqual(
            result,
            {
                "status": "blocked",
                "reason": "prospect_disqualified",
                "prospect_id": "LEAD-50001",
            },
        )
        send_email.assert_not_called()

    @patch.object(agent_module, "_send_email_via_provider")
    def test_eligible_canonical_prospect_is_sent(self, send_email):
        send_email.return_value = {"status": "sent", "message_id": "msg-test"}

        result = agent_module.send_prospect_email.func(
            prospect={
                "prospect_id": "LEAD-90002",
                "name": "Spoofed Name",
                "email": "spoofed@example.com",
                "disqualified": True,
            },
            subject="Introduction",
            body="Let's connect.",
            runtime=self.runtime,
            from_rep=self.rep,
        )

        self.assertEqual(result["status"], "sent")
        canonical_prospect = send_email.call_args.args[0]
        self.assertEqual(canonical_prospect["email"], "tomas.herrera@northgatesolutions.com")

    @patch.object(agent_module.gtm_agent, "invoke")
    def test_direct_request_does_not_report_success_when_send_is_blocked(self, invoke):
        invoke.return_value = {
            "messages": [
                SimpleNamespace(
                    name="send_prospect_email",
                    content='{"status": "blocked", "reason": "prospect_disqualified"}',
                ),
                SimpleNamespace(name=None, content="The email was sent successfully."),
            ]
        }

        result = agent_module.run_agent(
            "Email Priya Nair now and tell her about our offering.",
            user_id="REP-10001",
        )

        self.assertEqual(
            result["reply"],
            "No email was sent because the prospect is disqualified.",
        )
        self.assertNotIn("success", result["reply"].lower())


if __name__ == "__main__":
    unittest.main()
