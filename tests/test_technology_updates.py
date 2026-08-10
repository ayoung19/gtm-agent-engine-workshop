import json
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service, gtm_agent


class FakeScore:
    def model_dump(self):
        return {
            "score": 100,
            "max_score": 100,
            "justification": "Updated technology was scored.",
            "rubric_breakdown": {
                "revenue_fit": 100,
                "tech_stack_match": 100,
                "segment_fit": 100,
                "component_max": 100,
            },
        }


class RecordingScoringModel:
    def __init__(self):
        self.prospect_profile = None

    def invoke(self, messages):
        user_message = messages[1]["content"]
        self.prospect_profile = json.loads(
            user_message.split("\n\nProspect profile:\n", 1)[1]
        )
        return FakeScore()


class TechnologyUpdateTests(unittest.TestCase):
    def test_updates_are_visible_to_stack_profile_and_scoring(self):
        cases = (
            ("LEAD-39002", "Kafka", "OFFER-10001"),
            ("LEAD-12853", "Terraform", "OFFER-10004"),
            ("LEAD-12853", "Okta", "OFFER-10007"),
        )

        for prospect_id, technology, offering_id in cases:
            with self.subTest(technology=technology):
                record = data_service.PROSPECTS[prospect_id]
                original_stack = list(record["tech_stack"])
                original_model = gtm_agent._scoring_llm
                scoring_model = RecordingScoringModel()
                try:
                    data_service._PROFILES.pop(prospect_id, None)
                    cached_profile = gtm_agent.build_prospect_profile.invoke(
                        {"prospect_id": prospect_id}
                    )["prospect_profile"]
                    self.assertNotIn(technology, cached_profile["tech_stack"])

                    first_update = data_service.update_prospect_info(
                        prospect_id, technology
                    )
                    second_update = data_service.update_prospect_info(
                        prospect_id, technology
                    )

                    self.assertEqual(first_update, second_update)
                    self.assertEqual(
                        data_service.fetch_tech_stack(prospect_id).count(technology), 1
                    )

                    rebuilt_profile = gtm_agent.build_prospect_profile.invoke(
                        {"prospect_id": prospect_id}
                    )["prospect_profile"]
                    self.assertIn(technology, rebuilt_profile["tech_stack"])
                    self.assertIs(
                        data_service.get_profile_from_db(prospect_id)[
                            "prospect_profile"
                        ],
                        rebuilt_profile,
                    )

                    gtm_agent._scoring_llm = scoring_model
                    gtm_agent.score_prospect.invoke(
                        {
                            "prospect_profile": cached_profile,
                            "offering": data_service.OFFERINGS[offering_id],
                        }
                    )
                    self.assertIn(
                        technology, scoring_model.prospect_profile["tech_stack"]
                    )
                finally:
                    gtm_agent._scoring_llm = original_model
                    record["tech_stack"] = original_stack
                    data_service._PROFILES.pop(prospect_id, None)


if __name__ == "__main__":
    unittest.main()
