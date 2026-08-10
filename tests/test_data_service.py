from gtm_agent.data_service import fetch_tech_stack, update_prospect_info


def test_update_prospect_info_persists_to_record():
    result = update_prospect_info("LEAD-71001", "Kafka")
    assert result["updated"] is True
    assert "Kafka" in fetch_tech_stack("LEAD-71001")
