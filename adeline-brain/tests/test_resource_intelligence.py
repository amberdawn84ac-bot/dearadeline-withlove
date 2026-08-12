from app.agents.resource_intelligence import ResourceIntelligenceAgent


def test_history_mission_prefers_primary_sources():
    packet = ResourceIntelligenceAgent().select("child labor factory history", "JUSTICE_CHANGEMAKING")
    ids = [source["id"] for source in packet["sources"]]
    assert "loc-primary" in ids
    assert any("Free access is not permission" in rule for rule in packet["rules"])


def test_homestead_seed_mission_can_find_baker_creek_without_marking_it_reusable():
    packet = ResourceIntelligenceAgent().select("heirloom seed saving garden", "HOMESTEADING")
    baker = next(source for source in packet["sources"] if source["id"] == "baker-creek")
    assert baker["use_mode"] == "LINK_ONLY"


def test_public_domain_books_are_available_for_literature_missions():
    packet = ResourceIntelligenceAgent().select("public domain book literature", "ENGLISH_LITERATURE")
    gutenberg = next(source for source in packet["sources"] if source["id"] == "project-gutenberg")
    assert gutenberg["use_mode"] == "PUBLIC_DOMAIN_EDITION_ONLY"
