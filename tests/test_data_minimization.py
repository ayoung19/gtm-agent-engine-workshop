import json
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service
from gtm_agent.gtm_agent import (
    SYSTEM_PROMPT,
    build_prospect_profile,
    get_current_rep,
    get_prospect,
    send_prospect_email,
)


class DataMinimizationTests(unittest.TestCase):
    def setUp(self):
        data_service._PROFILES.clear()
        self.runtime = SimpleNamespace(
            config={"metadata": {"user_id": "rep_amills"}}
        )

    def assert_no_sensitive_contact_data(self, value):
        serialized = json.dumps(value)
        self.assertNotIn("email", serialized.lower())
        self.assertNotIn("billing_qualification", serialized)
        self.assertNotIn("@", serialized)

    def test_prospect_lookup_allowlists_safe_fields(self):
        result = get_prospect.invoke({"prospect_id": "LEAD-12853"})

        self.assertEqual(
            set(result["prospect"]),
            {"prospect_id", "name", "disqualified", "enrichment_source"},
        )
        self.assert_no_sensitive_contact_data(result)

    def test_profile_omits_contact_and_billing_fields(self):
        result = build_prospect_profile.invoke({"prospect_id": "LEAD-12853"})

        self.assertEqual(
            set(result["prospect_profile"]),
            {
                "prospect_id",
                "name",
                "disqualified",
                "engagement_history",
                "account_details",
                "tech_stack",
                "annual_revenue",
                "enrichment_source",
            },
        )
        self.assert_no_sensitive_contact_data(result)

    def test_cached_profile_is_sanitized_before_returning(self):
        data_service._PROFILES["LEAD-12853"] = {
            **data_service.get_prospect_record("LEAD-12853"),
            "prospect_id": "LEAD-12853",
        }

        result = build_prospect_profile.invoke({"prospect_id": "LEAD-12853"})

        self.assert_no_sensitive_contact_data(result)

    def test_send_receipt_omits_addresses_and_body(self):
        result = send_prospect_email.func(
            prospect_id="LEAD-12853",
            subject="Platform follow-up",
            body="Confidential draft body",
            runtime=self.runtime,
        )

        self.assertEqual(
            set(result), {"status", "message_id", "display_name", "subject"}
        )
        self.assertEqual(result["status"], "sent")
        self.assertNotIn("Confidential draft body", json.dumps(result))
        self.assert_no_sensitive_contact_data(result)

    def test_rep_lookup_and_final_response_guidance_omit_contact_details(self):
        result = get_current_rep.func(runtime=self.runtime)

        self.assertEqual(set(result["rep"]), {"rep_id", "name"})
        self.assert_no_sensitive_contact_data(result)
        self.assertIn("Never repeat an email address", SYSTEM_PROMPT)
        self.assertIn("or the message body", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
