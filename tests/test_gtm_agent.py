import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent.gtm_agent import SYSTEM_PROMPT, get_prospect


SENSITIVE_RECORD = {
    "name": "Test Prospect",
    "email": "prospect@example.com",
    "disqualified": False,
    "billing_qualification": {
        "tax_id": "541-88-2307",
        "date_of_birth": "1984-03-11",
        "card_on_file": "4539882100437712",
        "credit_check_ref": "EXPN-88213",
    },
    "annual_revenue": 90_000_000,
}
EXPECTED_RESULT = {
    "prospect": {
        "name": "Test Prospect",
        "email": "prospect@example.com",
        "disqualified": False,
    },
    "found": True,
}
SENSITIVE_KEYS = {
    "billing_qualification",
    "tax_id",
    "date_of_birth",
    "card_on_file",
    "credit_check_ref",
}


def collect_keys(value):
    if isinstance(value, dict):
        return set(value).union(
            key for nested in value.values() for key in collect_keys(nested)
        )
    if isinstance(value, list):
        return {key for nested in value for key in collect_keys(nested)}
    return set()


class GetProspectPrivacyTests(unittest.TestCase):
    @patch(
        "gtm_agent.gtm_agent.data_service.get_prospect_record",
        return_value=SENSITIVE_RECORD,
    )
    def test_direct_tool_output_only_contains_required_fields(self, _get_record):
        result = get_prospect.invoke({"prospect_id": "LEAD-TEST"})

        self.assertEqual(result, EXPECTED_RESULT)
        self.assertTrue(SENSITIVE_KEYS.isdisjoint(collect_keys(result)))

    @patch(
        "gtm_agent.gtm_agent.data_service.get_prospect_record",
        return_value=SENSITIVE_RECORD,
    )
    def test_model_visible_tool_payload_excludes_sensitive_fields(self, _get_record):
        message = get_prospect.invoke(
            {
                "name": "get_prospect",
                "args": {"prospect_id": "LEAD-TEST"},
                "id": "call-1",
                "type": "tool_call",
            }
        )
        payload = json.loads(message.content)

        self.assertEqual(payload, EXPECTED_RESULT)
        self.assertTrue(SENSITIVE_KEYS.isdisjoint(collect_keys(payload)))

    def test_final_summary_guidance_limits_contact_address_repetition(self):
        self.assertIn(
            "Do not repeat contact email addresses in your final summary unless "
            "the rep explicitly needs the address.",
            SYSTEM_PROMPT,
        )


if __name__ == "__main__":
    unittest.main()
