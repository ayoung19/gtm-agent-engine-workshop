import importlib
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test")

gtm_agent = importlib.import_module("gtm_agent.gtm_agent")
get_prospect = gtm_agent.get_prospect
send_prospect_email = gtm_agent.send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def test_disqualified_prospect_direct_send_is_refused(self):
        prospect = get_prospect.func("LEAD-50001")["prospect"]

        result = send_prospect_email.func(
            prospect,
            "Following up",
            "Would you like to learn more?",
            runtime=None,
        )

        self.assertEqual(
            result,
            {"status": "failed", "error": "Prospect is disqualified; email not sent."},
        )

    def test_qualified_prospect_send_succeeds(self):
        prospect = get_prospect.func("LEAD-12853")["prospect"]
        rep = {"name": "Ava Mills", "email": "ava.mills@northpoint.com"}

        result = send_prospect_email.func(
            prospect,
            "Following up",
            "Would you like to learn more?",
            runtime=None,
            from_rep=rep,
        )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["to"], prospect["email"])
        self.assertEqual(result["from"], rep["email"])
        self.assertEqual(result["subject"], "Following up")
        self.assertEqual(result["body"], "Would you like to learn more?")


if __name__ == "__main__":
    unittest.main()
