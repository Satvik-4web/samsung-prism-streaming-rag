
import pytest

from backend.retrieval.dense.embedder import Embedder
from backend.retrieval.dense.faiss_index import FaissRetriever
from backend.retrieval.fusion.rrf import reciprocal_rank_fusion
from backend.retrieval.sparse.bm25 import BM25Retriever
from backend.schemas.corpus import Chunk
from backend.schemas.evidence import Evidence
from backend.schemas.intents import RetrievalQuery


class MockEmbedder(Embedder):
    def __init__(self):
        pass
    def embed(self, texts):
        return [[len(t) * 0.1, len(t) * 0.2] for t in texts]

@pytest.mark.asyncio
async def test_bm25_retrieval() -> None:
    chunks = [
        Chunk(chunk_id="1", document_id="d1", section_id="s1", text="Customer workshop in Pune", content_hash="", token_count=4),
        Chunk(chunk_id="2", document_id="d2", section_id="s1", text="Cancellation policy", content_hash="", token_count=2),
        Chunk(chunk_id="3", document_id="d3", section_id="s1", text="Something completely unrelated", content_hash="", token_count=3)
    ]
    retriever = BM25Retriever(chunks)
    q = RetrievalQuery(intent_id="i1", parent_request_id="r1", query_text="Pune workshop")
    results = await retriever.retrieve(q)
    
    assert len(results) > 0
    assert results[0].chunk_id == "1"

@pytest.mark.asyncio
async def test_faiss_retrieval() -> None:
    chunks = [
        Chunk(chunk_id="c1", document_id="d1", section_id="s1", text="Tiny text", content_hash="", token_count=2),
        Chunk(chunk_id="c2", document_id="d2", section_id="s2", text="A much longer piece of text for embedding", content_hash="", token_count=8)
    ]
    embedder = MockEmbedder()
    retriever = FaissRetriever(chunks, embedder=embedder)
    q = RetrievalQuery(intent_id="i1", parent_request_id="r1", query_text="Tiny")
    results = await retriever.retrieve(q)
    
    assert len(results) > 0

def test_rrf() -> None:
    ev1 = Evidence(evidence_id="e1", chunk_id="c1", document_id="d1", section_id="s1", text="t1")
    
    list_a2 = [ev1]
    list_b2 = [ev1]
    results = reciprocal_rank_fusion([list_a2, list_b2])
    assert len(results) == 1
    assert results[0].chunk_id == "c1"
    assert results[0].scores["rrf"] > 0
