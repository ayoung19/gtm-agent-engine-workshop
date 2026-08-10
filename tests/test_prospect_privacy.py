import importlib
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

with patch.dict(
    os.environ,
    {"OPENAI_API_KEY": "test-key", "LANGSMITH_TRACING": "false"},
    clear=False,
):
    data_service = importlib.import_module("gtm_agent.data_service")
    agent_module = importlib.import_module("gtm_agent.gtm_agent")

build_prospect_profile = agent_module.build_prospect_profile
get_prospect = agent_module.get_prospect
score_prospect = agent_module.score_prospect
send_prospect_email = agent_module.send_prospect_email


SENSITIVE_FIELDS = {
    "billing_qualification",
    "card_on_file",
    "credit_check_ref",
    "date_of_birth",
    "tax_id",
}


def nested_keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(
            *(nested_keys(item) for item in value.values()), set()
        )
    if isinstance(value, list):
        return set().union(*(nested_keys(item) for item in value), set())
    return set()


class ProspectPrivacyTests(unittest.TestCase):
    def setUp(self):
        data_service._PROFILES.clear()
        self.prospect_id = "LEAD-12853"

    def test_prospect_tools_exclude_sensitive_crm_fields(self):
        prospect = get_prospect.func(self.prospect_id)["prospect"]
        profile = build_prospect_profile.func(self.prospect_id)["prospect_profile"]

        self.assertFalse(SENSITIVE_FIELDS & nested_keys(prospect))
        self.assertFalse(SENSITIVE_FIELDS & nested_keys(profile))
        sensitive_values = data_service.get_prospect_record(self.prospect_id)[
            "billing_qualification"
        ].values()
        for value in sensitive_values:
            self.assertNotIn(str(value), json.dumps(prospect))
            self.assertNotIn(str(value), json.dumps(profile))

    def test_cached_profiles_are_projected_before_returning(self):
        data_service._PROFILES[self.prospect_id] = {
            "prospect_id": self.prospect_id,
            "name": "Omar Okafor",
            "email": "omar.okafor@lakesideanalytics.com",
            "annual_revenue": 90000000,
            "disqualified": False,
            "tech_stack": ["Salesforce"],
            "account_details": [{"industry": "Software"}],
            "billing_qualification": {"tax_id": "541-88-2307"},
        }

        profile = build_prospect_profile.func(self.prospect_id)["prospect_profile"]

        self.assertFalse(SENSITIVE_FIELDS & nested_keys(profile))

    def test_scoring_compliance_and_email_fields_remain_available(self):
        prospect = get_prospect.func(self.prospect_id)["prospect"]
        profile = build_prospect_profile.func(self.prospect_id)["prospect_profile"]
        offering = data_service.get_offering("OFFER-10003")
        score_result = SimpleNamespace(
            model_dump=lambda: {
                "score": 90,
                "max_score": 100,
                "justification": "Strong fit.",
                "rubric_breakdown": {
                    "revenue_fit": 90,
                    "tech_stack_match": 100,
                    "segment_fit": 80,
                    "component_max": 100,
                },
            }
        )

        with patch("gtm_agent.gtm_agent._scoring_llm") as scoring_llm:
            scoring_llm.invoke.return_value = score_result
            scored = score_prospect.func(profile, offering)

        sent = send_prospect_email.func(
            prospect,
            "Introduction",
            "Hello Omar",
            SimpleNamespace(config={"metadata": {"user_id": "REP-1001"}}),
            {"name": "Ava Mills", "email": "ava@example.com"},
        )

        self.assertIn("disqualified", prospect)
        self.assertIn("annual_revenue", profile)
        self.assertIn("tech_stack", profile)
        self.assertEqual(90, scored["score"])
        self.assertEqual("sent", sent["status"])
        self.assertEqual(self.prospect_id, sent["prospect_id"])
        self.assertEqual(prospect["name"], sent["to_name"])
        self.assertNotIn("to", sent)
        self.assertNotIn("from", sent)
        self.assertNotIn(prospect["email"], json.dumps(sent))


if __name__ == "__main__":
    unittest.main()
