import pytest

from backend.retrieval.pipeline import RetrievalPipeline
from backend.retrieval.sparse.bm25 import BM25Retriever
from backend.schemas.corpus import Chunk
from backend.schemas.intents import RetrievalQuery


class MockDenseRetriever:
    async def retrieve(self, query: RetrievalQuery):
        return []

@pytest.mark.asyncio
async def test_pipeline_dedup() -> None:
    chunks = [
        Chunk(chunk_id="c1", document_id="d1", section_id="s1", text="Pune workshop", content_hash="", token_count=2),
        Chunk(chunk_id="c2", document_id="d2", section_id="s1", text="Other", content_hash="", token_count=1),
        Chunk(chunk_id="c3", document_id="d3", section_id="s1", text="More", content_hash="", token_count=1),
    ]
    sparse = BM25Retriever(chunks)
    dense = MockDenseRetriever()
    pipeline = RetrievalPipeline(dense=dense, sparse=sparse)
    
    q1 = RetrievalQuery(intent_id="i1", parent_request_id="r1", query_text="Pune")
    q2 = RetrievalQuery(intent_id="i2", parent_request_id="r1", query_text="workshop")
    
    # Both queries should fetch the same chunk via sparse
    results = await pipeline.execute([q1, q2], session_id="s1")
    
    # Deduplication should ensure only 1 result is returned globally for chunk c1
    assert len(results) == 1
    # Both intents should be present in the intent_ids list
    assert "i1" in results[0].intent_ids
    assert "i2" in results[0].intent_ids
