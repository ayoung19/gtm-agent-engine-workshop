import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service, gtm_agent
from gtm_agent.gtm_records import OFFERINGS, PROSPECTS


class ScoringResult:
    def model_dump(self):
        return {
            "score": 100,
            "max_score": 100,
            "justification": "Updated technology is present.",
            "rubric_breakdown": {
                "revenue_fit": 100,
                "tech_stack_match": 100,
                "segment_fit": 100,
                "component_max": 100,
            },
        }


class CapturingScoringLlm:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return ScoringResult()


class ProspectUpdateTests(unittest.TestCase):
    cases = (
        ("LEAD-71001", "Kafka", "OFFER-10005"),
        ("LEAD-39002", "Terraform", "OFFER-10004"),
        ("LEAD-90001", "Okta", "OFFER-10007"),
    )

    def setUp(self):
        self.original_tech_stacks = {
            prospect_id: list(PROSPECTS[prospect_id]["tech_stack"])
            for prospect_id, _, _ in self.cases
        }
        for prospect_id, _, _ in self.cases:
            data_service._PROFILES.pop(prospect_id, None)

    def tearDown(self):
        for prospect_id, tech_stack in self.original_tech_stacks.items():
            PROSPECTS[prospect_id]["tech_stack"] = tech_stack
            data_service._PROFILES.pop(prospect_id, None)

    def test_updates_persist_across_fetch_profile_and_scoring(self):
        for prospect_id, technology, offering_id in self.cases:
            with self.subTest(technology=technology):
                stale_profile = {
                    "prospect_id": prospect_id,
                    "tech_stack": list(PROSPECTS[prospect_id]["tech_stack"]),
                }
                data_service.save_profile_to_db(prospect_id, stale_profile)

                result = data_service.update_prospect_info(prospect_id, technology)
                data_service.update_prospect_info(prospect_id, technology)

                self.assertIn(technology, result["tech_stack"])
                self.assertEqual(
                    data_service.fetch_tech_stack(prospect_id).count(technology), 1
                )
                self.assertIsNone(
                    data_service.get_profile_from_db(prospect_id)["prospect_profile"]
                )

                profile = gtm_agent.build_prospect_profile.invoke(
                    {"prospect_id": prospect_id}
                )["prospect_profile"]
                self.assertIn(technology, profile["tech_stack"])

                scoring_llm = CapturingScoringLlm()
                with patch.object(gtm_agent, "_scoring_llm", scoring_llm):
                    gtm_agent.score_prospect.invoke(
                        {
                            "prospect_profile": stale_profile,
                            "offering": OFFERINGS[offering_id],
                        }
                    )

                score_input = json.loads(
                    scoring_llm.messages[1]["content"].split(
                        "\n\nProspect profile:\n", 1
                    )[1]
                )
                self.assertIn(technology, score_input["tech_stack"])


if __name__ == "__main__":
    unittest.main()
