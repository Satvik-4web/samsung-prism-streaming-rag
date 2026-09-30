import asyncio

from backend.interfaces.retriever import Retriever
from backend.retrieval.fusion.reranker import Reranker
from backend.retrieval.fusion.rrf import reciprocal_rank_fusion
from backend.schemas.evidence import Evidence
from backend.schemas.intents import RetrievalQuery
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class RetrievalPipeline:
    def __init__(self, dense: Retriever, sparse: Retriever, reranker: Reranker | None = None) -> None:
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker

    async def execute(self, queries: list[RetrievalQuery], session_id: str) -> list[Evidence]:
        all_evidence = []
        
        for query in queries:
            telemetry_bus.emit(TelemetryEvent(
                event_type="retrieval_started",
                session_id=session_id,
                request_id=query.parent_request_id,
                payload={"intent_id": query.intent_id, "query_text": query.query_text}
            ))
            
            # Parallel Dense + Sparse
            dense_task = asyncio.create_task(self.dense.retrieve(query))
            sparse_task = asyncio.create_task(self.sparse.retrieve(query))
            
            dense_res, sparse_res = await asyncio.gather(dense_task, sparse_task)
            
            telemetry_bus.emit(TelemetryEvent(
                event_type="dense_retrieval",
                session_id=session_id,
                request_id=query.parent_request_id,
                payload={"intent_id": query.intent_id, "candidates": len(dense_res)}
            ))
            telemetry_bus.emit(TelemetryEvent(
                event_type="sparse_retrieval",
                session_id=session_id,
                request_id=query.parent_request_id,
                payload={"intent_id": query.intent_id, "candidates": len(sparse_res)}
            ))
            
            # RRF Fusion
            fused = reciprocal_rank_fusion([dense_res, sparse_res], k=60)
            
            telemetry_bus.emit(TelemetryEvent(
                event_type="evidence_fused",
                session_id=session_id,
                request_id=query.parent_request_id,
                payload={"intent_id": query.intent_id, "fused_count": len(fused)}
            ))
            
            # Optional Reranking
            if self.reranker:
                fused = await self.reranker.rerank(query, fused)
                telemetry_bus.emit(TelemetryEvent(
                    event_type="reranking",
                    session_id=session_id,
                    request_id=query.parent_request_id,
                    payload={"intent_id": query.intent_id}
                ))
                
            all_evidence.extend(fused)
            
        # Global Deduplication across intents based on chunk_id
        deduped = self._deduplicate(all_evidence)
        
        telemetry_bus.emit(TelemetryEvent(
            event_type="evidence_deduplicated",
            session_id=session_id,
            request_id=queries[0].parent_request_id if queries else "unknown",
            payload={"initial_count": len(all_evidence), "final_count": len(deduped)}
        ))
        
        return deduped

    def _deduplicate(self, evidence_list: list[Evidence]) -> list[Evidence]:
        seen = set()
        deduped = []
        for ev in evidence_list:
            if ev.chunk_id not in seen:
                seen.add(ev.chunk_id)
                deduped.append(ev)
            else:
                # Merge intent IDs if chunk was retrieved by multiple queries
                for existing in deduped:
                    if existing.chunk_id == ev.chunk_id:
                        for intent_id in ev.intent_ids:
                            if intent_id not in existing.intent_ids:
                                existing.intent_ids.append(intent_id)
        return deduped
