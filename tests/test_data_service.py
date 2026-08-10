"""Regression tests for the prospect data-access layer."""

from gtm_agent import data_service


def test_update_prospect_info_persists_tech_stack():
    result = data_service.update_prospect_info("LEAD-71001", "Kafka")
    assert result == {
        "updated": True,
        "found": True,
        "tech_stack": data_service.fetch_tech_stack("LEAD-71001"),
    }
    assert "Kafka" in data_service.fetch_tech_stack("LEAD-71001")

    profile = data_service.get_profile_from_db("LEAD-71001")["prospect_profile"]
    assert profile is None or "Kafka" in profile["tech_stack"]


def test_update_prospect_info_is_idempotent():
    data_service.update_prospect_info("LEAD-71001", "Kafka")

    result = data_service.update_prospect_info("LEAD-71001", "Kafka")
    assert result["updated"] is False
    assert result["found"] is True
    assert data_service.fetch_tech_stack("LEAD-71001").count("Kafka") == 1


def test_update_prospect_info_unknown_prospect():
    assert data_service.update_prospect_info("LEAD-00000", "Kafka") == {
        "updated": False,
        "found": False,
    }
