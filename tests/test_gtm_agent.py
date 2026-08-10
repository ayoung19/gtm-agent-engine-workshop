import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import gtm_agent as agent_module


SENSITIVE_KEYS = {
    "billing_qualification",
    "government_id",
    "tax_id",
    "date_of_birth",
    "card_on_file",
    "credit_check_ref",
}
SENSITIVE_VALUES = (
    "fixture-government-secret",
    "fixture-tax-secret",
    "fixture-birth-date-secret",
    "fixture-card-secret",
    "fixture-credit-secret",
)
BILLING_QUALIFICATION = {
    "government_id": SENSITIVE_VALUES[0],
    "tax_id": SENSITIVE_VALUES[1],
    "date_of_birth": SENSITIVE_VALUES[2],
    "card_on_file": SENSITIVE_VALUES[3],
    "credit_check_ref": SENSITIVE_VALUES[4],
}


def assert_sensitive_data_absent(test_case, value):
    def keys_in(item):
        if isinstance(item, dict):
            return set(item).union(*(keys_in(child) for child in item.values()))
        if isinstance(item, (list, tuple)):
            return set().union(*(keys_in(child) for child in item))
        return set()

    test_case.assertFalse(
        SENSITIVE_KEYS.intersection(keys_in(value)),
        "Sensitive key exposed in prospect workflow data.",
    )
    serialized = json.dumps(value)
    test_case.assertTrue(
        all(secret not in serialized for secret in SENSITIVE_VALUES),
        "Sensitive fixture value exposed in prospect workflow data.",
    )


class CapturingScoringModel:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return type(
            "ScoreResult",
            (),
            {"model_dump": lambda self: {"score": 80, "justification": "fit"}},
        )()


class ProspectDataMinimizationTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "name": "Test Prospect",
            "email": "prospect@example.test",
            "disqualified": False,
            "engagement_history": [{"channel": "demo"}],
            "account_details": [{"industry": "Software"}],
            "tech_stack": ["Snowflake"],
            "annual_revenue": 100_000_000,
            "enrichment_source": "fixture",
            "billing_qualification": BILLING_QUALIFICATION,
        }

    def test_get_prospect_returns_only_contact_fields(self):
        with patch.object(
            agent_module.data_service,
            "get_prospect_record",
            return_value=self.record,
        ):
            result = agent_module.get_prospect.func("LEAD-TEST")

        self.assertEqual(
            set(result["prospect"]),
            {"prospect_id", "name", "email", "disqualified"},
        )
        assert_sensitive_data_absent(self, result)

    def test_profile_and_scoring_input_exclude_sensitive_billing_data(self):
        with (
            patch.object(
                agent_module.data_service,
                "get_profile_from_db",
                return_value={"prospect_profile": None},
            ),
            patch.object(
                agent_module.data_service,
                "get_prospect_record",
                return_value=self.record,
            ),
            patch.object(
                agent_module.data_service,
                "fetch_engagement_history",
                return_value=self.record["engagement_history"],
            ),
            patch.object(
                agent_module.data_service,
                "fetch_account_details",
                return_value=self.record["account_details"],
            ),
            patch.object(
                agent_module.data_service,
                "fetch_tech_stack",
                return_value=self.record["tech_stack"],
            ),
            patch.object(agent_module.data_service, "save_profile_to_db"),
        ):
            result = agent_module.build_prospect_profile.func("LEAD-TEST")

        expected_fields = set(agent_module.PROSPECT_PROFILE_FIELDS)
        self.assertEqual(set(result["prospect_profile"]), expected_fields)
        assert_sensitive_data_absent(self, result)

        scoring_model = CapturingScoringModel()
        profile_with_billing_data = {
            **result["prospect_profile"],
            "billing_qualification": BILLING_QUALIFICATION,
        }
        offering = {
            "required_tech_stack": ["Snowflake"],
            "min_annual_revenue": 50_000_000,
            "description": "Test offering",
        }
        with (
            patch.object(agent_module, "_scoring_llm", scoring_model),
            patch.object(
                agent_module.data_service,
                "fetch_tech_stack",
                return_value=self.record["tech_stack"],
            ),
        ):
            agent_module.score_prospect.func(profile_with_billing_data, offering)

        self.assertIsNotNone(scoring_model.messages)
        assert_sensitive_data_absent(self, scoring_model.messages)


if __name__ == "__main__":
    unittest.main()
