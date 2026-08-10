import importlib
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

gtm_agent = importlib.import_module("gtm_agent.gtm_agent")


class GetProspectTest(unittest.TestCase):
    def test_returns_only_allowlisted_contact_fields(self):
        record = {
            "name": "Test Prospect",
            "email": "prospect@example.test",
            "disqualified": False,
            "billing_qualification": {
                "tax_identifier": "test-tax-id",
                "birth_date": "2000-01-01",
                "payment_card": "test-card",
            },
            "engagement_history": ["test-event"],
            "account_details": {"segment": "test-segment"},
            "tech_stack": ["test-tech"],
            "future_sensitive_field": "test-sensitive-value",
        }

        with patch.object(gtm_agent.data_service, "get_prospect_record", return_value=record):
            result = gtm_agent.get_prospect.invoke({"prospect_id": "LEAD-TEST"})

        self.assertTrue(result["found"])
        self.assertEqual(
            result["prospect"],
            {
                "prospect_id": "LEAD-TEST",
                "name": "Test Prospect",
                "email": "prospect@example.test",
                "disqualified": False,
            },
        )
        self.assertNotIn("billing_qualification", result["prospect"])


if __name__ == "__main__":
    unittest.main()
