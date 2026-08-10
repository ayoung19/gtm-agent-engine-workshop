import copy
import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent.gtm_agent import (
    ProspectScore,
    RubricBreakdown,
    build_prospect_profile,
    score_prospect,
)


class UpdateProspectInfoTests(unittest.TestCase):
    prospect_id = "LEAD-39002"

    def setUp(self):
        self.original_record = copy.deepcopy(data_service.PROSPECTS[self.prospect_id])
        self.original_profile = data_service._PROFILES.get(self.prospect_id)

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id] = self.original_record
        if self.original_profile is None:
            data_service._PROFILES.pop(self.prospect_id, None)
        else:
            data_service._PROFILES[self.prospect_id] = self.original_profile

    def test_updates_are_visible_to_fetch_profile_and_scoring(self):
        for technology in ("Kafka", "Terraform", "Okta"):
            with self.subTest(technology=technology):
                data_service.PROSPECTS[self.prospect_id] = copy.deepcopy(
                    self.original_record
                )
                data_service._PROFILES.pop(self.prospect_id, None)
                stale_profile = build_prospect_profile.invoke(
                    {"prospect_id": self.prospect_id}
                )["prospect_profile"]
                self.assertNotIn(technology, stale_profile["tech_stack"])

                result = data_service.update_prospect_info(self.prospect_id, technology)

                self.assertTrue(result["updated"])
                self.assertIn(
                    technology, data_service.fetch_tech_stack(self.prospect_id)
                )
                refreshed_profile = build_prospect_profile.invoke(
                    {"prospect_id": self.prospect_id}
                )["prospect_profile"]
                self.assertIn(technology, refreshed_profile["tech_stack"])

                offering = {
                    "description": "Regression test offering",
                    "required_tech_stack": [technology],
                    "min_annual_revenue": 1,
                }

                def score_from_request(messages, required=technology):
                    profile_json = messages[1]["content"].split(
                        "\n\nProspect profile:\n", 1
                    )[1]
                    tech_stack = json.loads(profile_json)["tech_stack"]
                    missing = required not in tech_stack
                    return ProspectScore(
                        score=50 if missing else 100,
                        justification=(
                            f"Missing {required}." if missing else f"Has {required}."
                        ),
                        rubric_breakdown=RubricBreakdown(
                            revenue_fit=100,
                            tech_stack_match=0 if missing else 100,
                            segment_fit=100,
                        ),
                    )

                scoring_llm = Mock()
                scoring_llm.invoke.side_effect = score_from_request
                with patch("gtm_agent.gtm_agent._scoring_llm", scoring_llm):
                    scored = score_prospect.invoke(
                        {"prospect_profile": refreshed_profile, "offering": offering}
                    )

                self.assertEqual(scored["justification"], f"Has {technology}.")

    def test_not_found_and_duplicate_updates_remain_unchanged(self):
        missing = data_service.update_prospect_info("LEAD-NOT-FOUND", "Kafka")
        self.assertEqual(missing, {"updated": False, "found": False})

        existing = self.original_record["tech_stack"][0]
        cached_profile = {"prospect_id": self.prospect_id, "cached": True}
        data_service._PROFILES[self.prospect_id] = cached_profile

        result = data_service.update_prospect_info(self.prospect_id, existing)

        self.assertEqual(
            result,
            {
                "updated": True,
                "found": True,
                "tech_stack": self.original_record["tech_stack"],
            },
        )
        self.assertIs(data_service._PROFILES[self.prospect_id], cached_profile)
        self.assertEqual(
            data_service.fetch_tech_stack(self.prospect_id).count(existing), 1
        )


if __name__ == "__main__":
    unittest.main()
