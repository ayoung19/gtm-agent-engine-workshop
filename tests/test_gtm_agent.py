import json
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service, gtm_agent


class _ScoringResult:
    def __init__(self, technology, has_requirement):
        self.technology = technology
        self.has_requirement = has_requirement

    def model_dump(self):
        missing = "none" if self.has_requirement else self.technology
        return {
            "score": 100 if self.has_requirement else 50,
            "max_score": 100,
            "justification": f"Missing required technologies: {missing}",
            "rubric_breakdown": {
                "revenue_fit": 100,
                "tech_stack_match": 100 if self.has_requirement else 0,
                "segment_fit": 100,
                "component_max": 100,
            },
        }


class _RecordingScoringModel:
    def invoke(self, messages):
        offering_text, profile_text = messages[-1]["content"].split(
            "\n\nProspect profile:\n"
        )
        offering = json.loads(offering_text.removeprefix("Offering:\n"))
        profile = json.loads(profile_text)
        technology = offering["required_tech_stack"][0]
        return _ScoringResult(technology, technology in profile["tech_stack"])


class UpdateThenScoreTests(unittest.TestCase):
    prospect_id = "LEAD-70001"
    technologies = ("Kafka", "Terraform", "Okta")

    def setUp(self):
        self.original_stack = data_service.PROSPECTS[self.prospect_id]["tech_stack"]
        self.original_profile = data_service._PROFILES.get(self.prospect_id)
        self.original_scoring_model = gtm_agent._scoring_llm
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = list(
            self.original_stack
        )
        data_service._PROFILES.pop(self.prospect_id, None)
        gtm_agent._scoring_llm = _RecordingScoringModel()

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = self.original_stack
        if self.original_profile is None:
            data_service._PROFILES.pop(self.prospect_id, None)
        else:
            data_service._PROFILES[self.prospect_id] = self.original_profile
        gtm_agent._scoring_llm = self.original_scoring_model

    def test_update_then_score_recognizes_each_added_requirement(self):
        for technology in self.technologies:
            with self.subTest(technology=technology):
                gtm_agent.build_prospect_profile.invoke(
                    {"prospect_id": self.prospect_id}
                )

                update = gtm_agent.update_prospect_info.invoke(
                    {"prospect_id": self.prospect_id, "technology": technology}
                )
                fetched_stack = data_service.fetch_tech_stack(self.prospect_id)
                profile = gtm_agent.build_prospect_profile.invoke(
                    {"prospect_id": self.prospect_id}
                )["prospect_profile"]
                offering = {
                    "required_tech_stack": [technology],
                    "min_annual_revenue": 1,
                    "description": "Regression test offering",
                }
                score = gtm_agent.score_prospect.invoke(
                    {"prospect_profile": profile, "offering": offering}
                )

                self.assertTrue(update["updated"])
                self.assertIn(technology, fetched_stack)
                self.assertIn(technology, profile["tech_stack"])
                self.assertEqual(100, score["rubric_breakdown"]["tech_stack_match"])
                self.assertEqual(
                    "Missing required technologies: none", score["justification"]
                )


if __name__ == "__main__":
    unittest.main()
