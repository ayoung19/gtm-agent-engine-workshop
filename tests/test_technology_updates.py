import json
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent import gtm_agent


class _ScoreResult:
    def __init__(self, missing):
        self.missing = missing

    def model_dump(self):
        return {
            "score": 100 if not self.missing else 50,
            "justification": f"Missing technologies: {', '.join(self.missing) or 'none'}",
        }


class _ScoringModel:
    def invoke(self, messages):
        user_message = messages[-1]["content"]
        offering_json, prospect_json = user_message.removeprefix("Offering:\n").split(
            "\n\nProspect profile:\n"
        )
        offering = json.loads(offering_json)
        prospect = json.loads(prospect_json)
        missing = [
            technology
            for technology in offering["required_tech_stack"]
            if technology not in prospect["tech_stack"]
        ]
        return _ScoreResult(missing)


class TechnologyUpdateTests(unittest.TestCase):
    scenarios = (
        ("LEAD-12853", "Terraform"),
        ("LEAD-15229", "ServiceNow"),
    )

    def setUp(self):
        self.original_stacks = {
            prospect_id: list(data_service.PROSPECTS[prospect_id]["tech_stack"])
            for prospect_id, _ in self.scenarios
        }
        self.original_profiles = dict(data_service._PROFILES)
        self.original_scoring_llm = gtm_agent._scoring_llm
        gtm_agent._scoring_llm = _ScoringModel()

    def tearDown(self):
        for prospect_id, tech_stack in self.original_stacks.items():
            data_service.PROSPECTS[prospect_id]["tech_stack"] = tech_stack
        data_service._PROFILES.clear()
        data_service._PROFILES.update(self.original_profiles)
        gtm_agent._scoring_llm = self.original_scoring_llm

    def test_updates_persist_through_fetch_build_and_score(self):
        for prospect_id, technology in self.scenarios:
            with self.subTest(technology=technology):
                old_profile = gtm_agent.build_prospect_profile.invoke(
                    {"prospect_id": prospect_id}
                )["prospect_profile"]
                self.assertNotIn(technology, old_profile["tech_stack"])

                result = data_service.update_prospect_info(prospect_id, technology)

                self.assertTrue(result["updated"])
                self.assertIn(
                    technology,
                    data_service.get_prospect_record(prospect_id)["tech_stack"],
                )
                self.assertIn(technology, data_service.fetch_tech_stack(prospect_id))

                built_profile = gtm_agent.build_prospect_profile.invoke(
                    {"prospect_id": prospect_id}
                )["prospect_profile"]
                self.assertIsNot(built_profile, old_profile)
                self.assertIn(technology, built_profile["tech_stack"])

                offering = {
                    "required_tech_stack": [technology],
                    "min_annual_revenue": 1,
                    "description": "Requires the newly added technology.",
                }
                score = gtm_agent.score_prospect.invoke(
                    {"prospect_profile": built_profile, "offering": offering}
                )
                self.assertEqual(score["score"], 100)
                self.assertEqual(score["justification"], "Missing technologies: none")


if __name__ == "__main__":
    unittest.main()
