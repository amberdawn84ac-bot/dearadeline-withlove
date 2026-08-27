from app.schemas.api_models import Evidence, EvidenceVerdict


def test_archival_citation_evidence_does_not_require_witness_fields():
    evidence = Evidence(
        source_title="Pacific Railway Act (1862)",
        creator_or_issuer="United States Congress",
        date="July 1, 1862",
        holding_institution="U.S. National Archives",
        source_url="https://www.archives.gov/milestone-documents/pacific-railway-act",
        item_identifier="General Records of the United States Government",
        excerpt_or_observable_feature="The enacted land-grant and subsidy provisions.",
        claim_supported="Congress materially supported railroad construction.",
    )

    assert evidence.verdict is None
    assert evidence.similarity_score is None
    assert evidence.witness_citation.author == ""
    assert evidence.holding_institution == "U.S. National Archives"


def test_witness_protocol_evidence_keeps_score_and_verdict():
    evidence = Evidence(
        source_title="Verified archive passage",
        source_url="https://example.org/source",
        similarity_score=0.91,
        verdict=EvidenceVerdict.VERIFIED,
        chunk="Retrieved passage",
    )

    assert evidence.similarity_score == 0.91
    assert evidence.verdict == EvidenceVerdict.VERIFIED
