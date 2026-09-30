from backend.schemas.corpus import Chunk, Citation


def test_stable_chunk_id() -> None:
    chunk = Chunk(
        chunk_id="Doc_1::S1::0001",
        document_id="Doc_1",
        section_id="S1",
        text="Hello world",
        content_hash="abc",
        token_count=2
    )
    assert chunk.chunk_id == "Doc_1::S1::0001"

def test_citation_mapping() -> None:
    cit = Citation(
        document_id="Doc_1",
        section_id="S1",
        chunk_id="Doc_1::S1::0001",
        display="[Doc_1 S1]"
    )
    assert cit.display == "[Doc_1 S1]"
