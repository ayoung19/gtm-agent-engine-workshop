import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent.gtm_agent import (
    ProspectScore,
    build_prospect_profile,
    score_prospect,
)
from gtm_agent.gtm_records import OFFERINGS, PROSPECTS


class FakeScoringLlm:
    def invoke(self, messages):
        payload = json.loads(messages[1]["content"].split("Prospect profile:\n", 1)[1])
        offering = json.loads(
            messages[1]["content"].split("Offering:\n", 1)[1].split("\n\nProspect profile:", 1)[0]
        )
        present = [
            technology
            for technology in offering["required_tech_stack"]
            if technology in payload["tech_stack"]
        ]
        missing = [
            technology
            for technology in offering["required_tech_stack"]
            if technology not in payload["tech_stack"]
        ]
        return ProspectScore(
            score=100 if not missing else 80,
            justification=f"Has: {', '.join(present)}. Missing: {', '.join(missing) or 'none'}.",
            rubric_breakdown={
                "revenue_fit": 100,
                "tech_stack_match": 100 if not missing else 80,
                "segment_fit": 100,
            },
        )


class ProspectTechnologyUpdateTests(unittest.TestCase):
    def test_updates_survive_refetch_profile_rebuild_and_scoring(self):
        scenarios = (
            ("LEAD-50002", "OFFER-10001", "Kafka"),
            ("LEAD-39002", "OFFER-10004", "Terraform"),
            ("LEAD-90001", "OFFER-10007", "Okta"),
        )

        for prospect_id, offering_id, technology in scenarios:
            with self.subTest(technology=technology):
                original_stack = PROSPECTS[prospect_id]["tech_stack"]
                original_profile = data_service._PROFILES.get(prospect_id)
                try:
                    data_service._PROFILES.pop(prospect_id, None)
                    cached = build_prospect_profile.invoke({"prospect_id": prospect_id})[
                        "prospect_profile"
                    ]
                    self.assertNotIn(technology, cached["tech_stack"])

                    result = data_service.update_prospect_info(prospect_id, technology)

                    self.assertIn(technology, result["tech_stack"])
                    self.assertIn(technology, data_service.fetch_tech_stack(prospect_id))
                    self.assertIsNone(
                        data_service.get_profile_from_db(prospect_id)["prospect_profile"]
                    )

                    rebuilt = build_prospect_profile.invoke({"prospect_id": prospect_id})[
                        "prospect_profile"
                    ]
                    self.assertIn(technology, rebuilt["tech_stack"])

                    with patch("gtm_agent.gtm_agent._scoring_llm", FakeScoringLlm()):
                        score = score_prospect.invoke(
                            {
                                "prospect_profile": rebuilt,
                                "offering": OFFERINGS[offering_id],
                            }
                        )

                    has, missing = score["justification"].split(". Missing: ", 1)
                    self.assertIn(technology, has)
                    self.assertNotIn(technology, missing)
                finally:
                    PROSPECTS[prospect_id]["tech_stack"] = original_stack
                    data_service._PROFILES.pop(prospect_id, None)
                    if original_profile is not None:
                        data_service._PROFILES[prospect_id] = original_profile


if __name__ == "__main__":
    unittest.main()
