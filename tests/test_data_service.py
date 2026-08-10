import unittest

from gtm_agent import data_service


class UpdateProspectInfoTests(unittest.TestCase):
    prospect_id = "LEAD-70001"
    technologies = ("Kafka", "Terraform", "Okta")

    def setUp(self):
        self.original_stack = data_service.PROSPECTS[self.prospect_id]["tech_stack"]
        self.original_profile = data_service._PROFILES.get(self.prospect_id)
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = list(
            self.original_stack
        )
        data_service._PROFILES.pop(self.prospect_id, None)

    def tearDown(self):
        data_service.PROSPECTS[self.prospect_id]["tech_stack"] = self.original_stack
        if self.original_profile is None:
            data_service._PROFILES.pop(self.prospect_id, None)
        else:
            data_service._PROFILES[self.prospect_id] = self.original_profile

    def test_updates_persist_and_invalidate_cached_profiles(self):
        for technology in self.technologies:
            with self.subTest(technology=technology):
                data_service.save_profile_to_db(
                    self.prospect_id,
                    {"prospect_id": self.prospect_id, "tech_stack": []},
                )

                result = data_service.update_prospect_info(self.prospect_id, technology)

                self.assertTrue(result["updated"])
                self.assertIn(
                    technology, data_service.fetch_tech_stack(self.prospect_id)
                )
                self.assertIsNone(
                    data_service.get_profile_from_db(self.prospect_id)[
                        "prospect_profile"
                    ]
                )


if __name__ == "__main__":
    unittest.main()
