from rank_bm25 import BM25Okapi

from backend.interfaces.retriever import Retriever
from backend.schemas.corpus import Chunk
from backend.schemas.evidence import Evidence
from backend.schemas.intents import RetrievalQuery


class BM25Retriever(Retriever):
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        tokenized_corpus = [c.text.lower().split() for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus) if chunks else None

    async def retrieve(self, query: RetrievalQuery) -> list[Evidence]:
        if not self.bm25 or not self.chunks:
            return []
            
        tokenized_query = query.query_text.lower().split()
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_k_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:query.top_k]
        
        results = []
        for rank, idx in enumerate(top_k_indices):
            if doc_scores[idx] <= 0:
                continue
            chunk = self.chunks[idx]
            evidence = Evidence(
                evidence_id=f"bm25_{chunk.chunk_id}",
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                section_id=chunk.section_id,
                text=chunk.text,
                intent_ids=[query.intent_id],
                scores={"bm25": float(doc_scores[idx])},
                retrieval_source="sparse",
                citation_reference=f"[{chunk.document_id} S{chunk.section_id}]"
            )
            results.append(evidence)
            
        return results
