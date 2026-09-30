
import faiss
import numpy as np

from backend.interfaces.retriever import Retriever
from backend.retrieval.dense.embedder import Embedder
from backend.schemas.corpus import Chunk
from backend.schemas.evidence import Evidence
from backend.schemas.intents import RetrievalQuery


class FaissRetriever(Retriever):
    def __init__(self, chunks: list[Chunk], embedder: Embedder) -> None:
        self.chunks = chunks
        self.embedder = embedder
        
        if not chunks:
            self.index = None
            return
            
        texts = [c.text for c in chunks]
        embeddings = np.array(self.embedder.embed(texts)).astype('float32')
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    async def retrieve(self, query: RetrievalQuery) -> list[Evidence]:
        if not self.index or not self.chunks:
            return []
            
        query_emb = np.array(self.embedder.embed([query.query_text])).astype('float32')
        distances, indices = self.index.search(query_emb, query.top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx]
            # Convert L2 distance to a pseudo-similarity score (inverse)
            score = 1.0 / (1.0 + float(distances[0][i]))
            
            evidence = Evidence(
                evidence_id=f"dense_{chunk.chunk_id}",
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                section_id=chunk.section_id,
                text=chunk.text,
                intent_ids=[query.intent_id],
                scores={"dense": score},
                retrieval_source="dense",
                citation_reference=f"[{chunk.document_id} S{chunk.section_id}]"
            )
            results.append(evidence)
            
        return results
