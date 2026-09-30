from backend.schemas.evidence import Evidence
from backend.schemas.session import SessionState


def test_session_isolation() -> None:
    s1 = SessionState(session_id="1")
    s2 = SessionState(session_id="2")
    
    ev = Evidence(
        evidence_id="ev1",
        chunk_id="chunk1",
        document_id="doc1",
        section_id="s1",
        text="text"
    )
    s1.evidence.append(ev)
    
    assert len(s1.evidence) == 1
    assert len(s2.evidence) == 0
