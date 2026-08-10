import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["LANGSMITH_TRACING"] = "false"

from gtm_agent import data_service
from gtm_agent.gtm_agent import build_prospect_profile, score_prospect
from gtm_agent.gtm_records import OFFERINGS, PROSPECTS


class ProspectUpdateTests(unittest.TestCase):
    def setUp(self):
        self.prospect_id = "LEAD-12853"
        self.original_tech_stack = PROSPECTS[self.prospect_id]["tech_stack"]
        self.original_profile = data_service._PROFILES.get(self.prospect_id)
        data_service._PROFILES.pop(self.prospect_id, None)

    def tearDown(self):
        PROSPECTS[self.prospect_id]["tech_stack"] = self.original_tech_stack
        data_service._PROFILES.pop(self.prospect_id, None)
        if self.original_profile is not None:
            data_service._PROFILES[self.prospect_id] = self.original_profile

    def test_updated_technologies_are_in_rebuilt_profile_and_score(self):
        build_prospect_profile.func(self.prospect_id)
        added_technologies = ["Snowflake", "Databricks", "Kubernetes"]

        for technology in added_technologies:
            data_service.update_prospect_info(self.prospect_id, technology)

        profile = build_prospect_profile.func(self.prospect_id)["prospect_profile"]
        offering = OFFERINGS["OFFER-10001"]

        def score_from_messages(messages):
            prospect = json.loads(messages[1]["content"].split("Prospect profile:\n", 1)[1])
            present = [
                technology
                for technology in offering["required_tech_stack"]
                if technology in prospect["tech_stack"]
            ]
            missing = [
                technology
                for technology in offering["required_tech_stack"]
                if technology not in prospect["tech_stack"]
            ]
            return SimpleNamespace(model_dump=lambda: {"present": present, "missing": missing})

        scoring_llm = SimpleNamespace(invoke=score_from_messages)
        with patch("gtm_agent.gtm_agent._scoring_llm", scoring_llm):
            score = score_prospect.func(profile, offering)

        self.assertTrue(set(added_technologies).issubset(profile["tech_stack"]))
        self.assertTrue(set(added_technologies).issubset(score["present"]))
        self.assertTrue(set(added_technologies).isdisjoint(score["missing"]))


if __name__ == "__main__":
    unittest.main()
