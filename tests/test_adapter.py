import os

from backend.ingest.adapters.markdown import MarkdownAdapter


def test_fixture_loading() -> None:
    adapter = MarkdownAdapter()
    fixture_path = os.path.join("data", "dev_fixture", "sample_policy.md")
    
    docs = list(adapter.load(fixture_path))
    assert len(docs) == 1
    doc = docs[0]
    assert doc.document_id == "Doc_dev1"
    assert len(doc.sections) == 3
    
    chunks = list(adapter.chunk(doc))
    assert len(chunks) == 3
    assert chunks[0].chunk_id == "Doc_dev1::S1::0001"


