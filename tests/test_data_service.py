import json
import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("LANGSMITH_TRACING", "false")

from gtm_agent import data_service


class UpdateProspectInfoTests(unittest.TestCase):
    def setUp(self):
        self.prospect_id = "LEAD-12853"
        self.original_tech_stack = list(
            data_service.PROSPECTS[self.prospect_id]["tech_stack"]
        )
        self.original_profiles = data_service._PROFILES.copy()
        data_service._PROFILES.pop(self.prospect_id, None)

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = (
            self.original_tech_stack
        )
        data_service._PROFILES.clear()
        data_service._PROFILES.update(self.original_profiles)

    def test_update_is_visible_to_profile_rebuild_and_scoring_fetch(self):
        data_service.save_profile_to_db(
            self.prospect_id,
            {"prospect_id": self.prospect_id, "tech_stack": self.original_tech_stack},
        )

        result = data_service.update_prospect_info(self.prospect_id, "Terraform")

        self.assertTrue(result["updated"])
        self.assertIn("Terraform", data_service.PROSPECTS[self.prospect_id]["tech_stack"])
        self.assertIsNone(
            data_service.get_profile_from_db(self.prospect_id)["prospect_profile"]
        )
        self.assertIn("Terraform", data_service.fetch_tech_stack(self.prospect_id))

    def test_update_then_rescore_uses_the_new_technology(self):
        from gtm_agent import gtm_agent as agent_module

        profile = agent_module.build_prospect_profile.func(self.prospect_id)[
            "prospect_profile"
        ]
        self.assertNotIn("Terraform", profile["tech_stack"])

        agent_module.update_prospect_info.func(self.prospect_id, "Terraform")
        rebuilt_profile = agent_module.build_prospect_profile.func(self.prospect_id)[
            "prospect_profile"
        ]

        class ScoringResult:
            def model_dump(self):
                return {"score": 100}

        class CapturingScoringLlm:
            messages = None

            def invoke(self, messages):
                self.messages = messages
                return ScoringResult()

        scoring_llm = CapturingScoringLlm()
        original_scoring_llm = agent_module._scoring_llm
        agent_module._scoring_llm = scoring_llm
        try:
            agent_module.score_prospect.func(
                rebuilt_profile, data_service.OFFERINGS["OFFER-10004"]
            )
        finally:
            agent_module._scoring_llm = original_scoring_llm

        prospect_input = json.loads(
            scoring_llm.messages[1]["content"].split(
                "\n\nProspect profile:\n", maxsplit=1
            )[1]
        )
        self.assertIn("Terraform", prospect_input["tech_stack"])

    def test_repeated_update_is_idempotent(self):
        data_service.update_prospect_info(self.prospect_id, "Terraform")
        result = data_service.update_prospect_info(self.prospect_id, "Terraform")

        self.assertEqual(result["tech_stack"].count("Terraform"), 1)

    def test_unknown_prospect_is_not_updated(self):
        result = data_service.update_prospect_info("LEAD-UNKNOWN", "Terraform")

        self.assertEqual(result, {"updated": False, "found": False})


if __name__ == "__main__":
    unittest.main()
