import pytest

from backend.retrieval.pipeline import RetrievalPipeline
from backend.schemas.evidence import Evidence
from backend.schemas.intents import Constraint, Intent
from backend.session.manager import SessionManager


class MockPipeline(RetrievalPipeline):
    def __init__(self):
        self.call_count = 0
        self.executed_intents = []
        
    async def execute(self, queries, session_id):
        self.call_count += 1
        results = []
        for q in queries:
            self.executed_intents.append(q.query_text)
            results.append(Evidence(
                evidence_id=f"ev_{q.intent_id}",
                chunk_id=f"chunk_{q.intent_id}",
                document_id="d1",
                section_id="s1",
                text=f"evidence for {q.query_text}",
                intent_ids=[q.intent_id]
            ))
        return results

@pytest.mark.asyncio
async def test_delta_retrieval_scenario() -> None:
    pipeline = MockPipeline()
    manager = SessionManager(retrieval_pipeline=pipeline)
    
    # ---------------------------------------------------------
    # TURN 1: Initial request (Intent A and Intent B)
    # ---------------------------------------------------------
    intent_a_v1 = Intent(
        intent_id="A1", parent_request_id="req1",
        description="Intent A", constraints=[]
    )
    intent_b_v1 = Intent(
        intent_id="B1", parent_request_id="req1",
        description="Intent B", constraints=[]
    )
    
    session = await manager.process_intents("s1", "req1", [intent_a_v1, intent_b_v1])
    
    # Both should have triggered retrieval
    assert pipeline.call_count == 1
    assert "Intent A" in pipeline.executed_intents
    assert "Intent B" in pipeline.executed_intents
    assert len(session.evidence) == 2
    
    # ---------------------------------------------------------
    # TURN 2: User adds constraint affecting Intent A
    # ---------------------------------------------------------
    pipeline.executed_intents.clear() # reset mock tracking
    
    intent_a_v2 = Intent(
        intent_id="A2", parent_request_id="req2",
        description="Intent A", constraints=[Constraint(key="constraint_X", value="new_val")]
    )
    intent_b_v2 = Intent(
        intent_id="B2", parent_request_id="req2",
        description="Intent B", constraints=[] # Identical
    )
    
    session = await manager.process_intents("s1", "req2", [intent_a_v2, intent_b_v2])
    
    # ONLY Intent A should trigger retrieval
    assert pipeline.call_count == 2
    assert "Intent A" in pipeline.executed_intents
    assert "Intent B" not in pipeline.executed_intents  # Intent B -> retrieval X (ZERO)
    
    # Evidence validation: A updated, B preserved
    assert len(session.evidence) == 2
    
    ev_a = next(e for e in session.evidence if "A2" in e.intent_ids)
    ev_b = next(e for e in session.evidence if "B2" in e.intent_ids)
    
    # A is updated (has new chunk_id)
    assert ev_a.chunk_id == "chunk_A2"
    # B is preserved (retains old chunk_id but maps to new intent ID B2)
    assert ev_b.chunk_id == "chunk_B1"
