import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service

agent_module = importlib.import_module("gtm_agent.gtm_agent")


class ProspectTechnologyUpdateTests(unittest.TestCase):
    def setUp(self):
        self.prospect_id = "LEAD-12853"
        self.technology = "ClickHouse"
        self.original_stack = list(data_service.PROSPECTS[self.prospect_id]["tech_stack"])
        self.missing = object()
        self.original_profile = data_service._PROFILES.get(self.prospect_id, self.missing)
        data_service._PROFILES.pop(self.prospect_id, None)

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = self.original_stack
        if self.original_profile is self.missing:
            data_service._PROFILES.pop(self.prospect_id, None)
        else:
            data_service._PROFILES[self.prospect_id] = self.original_profile

    def test_update_is_visible_to_fetch_profile_and_scoring(self):
        stale_profile = {
            "prospect_id": self.prospect_id,
            "tech_stack": list(self.original_stack),
        }
        data_service.save_profile_to_db(self.prospect_id, stale_profile)

        result = data_service.update_prospect_info(self.prospect_id, self.technology)

        self.assertTrue(result["updated"])
        self.assertIn(self.technology, data_service.PROSPECTS[self.prospect_id]["tech_stack"])
        self.assertIn(self.technology, data_service.fetch_tech_stack(self.prospect_id))
        self.assertIsNone(data_service.get_profile_from_db(self.prospect_id)["prospect_profile"])

        built = agent_module.build_prospect_profile.invoke({"prospect_id": self.prospect_id})
        profile = built["prospect_profile"]
        self.assertIn(self.technology, profile["tech_stack"])

        scorer = Mock()
        scorer.invoke.return_value.model_dump.return_value = {"score": 100}
        offering = data_service.get_offering("OFFER-10001")
        with patch.object(agent_module, "_scoring_llm", scorer):
            agent_module.score_prospect.invoke({
                "prospect_profile": profile,
                "offering": offering,
            })

        messages = scorer.invoke.call_args.args[0]
        scoring_profile = json.loads(messages[1]["content"].split("\n\nProspect profile:\n", 1)[1])
        self.assertIn(self.technology, scoring_profile["tech_stack"])

    def test_repeated_update_is_idempotent_and_invalidates_cached_profile(self):
        data_service.save_profile_to_db(self.prospect_id, {"tech_stack": self.original_stack})
        data_service.update_prospect_info(self.prospect_id, self.technology)

        data_service.save_profile_to_db(self.prospect_id, {"tech_stack": self.original_stack})
        result = data_service.update_prospect_info(self.prospect_id, self.technology)

        self.assertEqual(result["tech_stack"].count(self.technology), 1)
        self.assertEqual(
            data_service.fetch_tech_stack(self.prospect_id).count(self.technology),
            1,
        )
        self.assertIsNone(data_service.get_profile_from_db(self.prospect_id)["prospect_profile"])

        rebuilt = agent_module.build_prospect_profile.invoke({"prospect_id": self.prospect_id})
        self.assertEqual(rebuilt["prospect_profile"]["tech_stack"].count(self.technology), 1)


if __name__ == "__main__":
    unittest.main()
