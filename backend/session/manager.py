from backend.generation.store import AnswerVersionStore
from backend.intents.planner import QueryPlanner
from backend.retrieval.pipeline import RetrievalPipeline
from backend.schemas.evidence import Evidence
from backend.schemas.generation import AnswerVersion, Claim
from backend.schemas.intents import Intent
from backend.schemas.session import SessionState
from backend.schemas.telemetry import TelemetryEvent
from backend.session.delta import DeltaEngine
from backend.telemetry.bus import telemetry_bus


class SessionManager:
    def __init__(self, retrieval_pipeline: RetrievalPipeline) -> None:
        self.sessions: dict[str, SessionState] = {}
        self.answers: dict[str, list[AnswerVersion]] = {}
        self.answer_store = AnswerVersionStore()
        self.delta_engine = DeltaEngine()
        self.planner = QueryPlanner()
        self.pipeline = retrieval_pipeline

    def get_or_create_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id=session_id)
        return self.sessions[session_id]

    async def process_intents(self, session_id: str, request_id: str, new_intents: list[Intent]) -> SessionState:
        session = self.get_or_create_session(session_id)
        
        # 1. Compute Delta
        delta_plan = self.delta_engine.compute(session.intents, new_intents, session_id, request_id)
        
        # 2. Plan Queries for AFFECTED intents ONLY
        queries = self.planner.plan(delta_plan.affected_intents, session_id)

        for intent in delta_plan.preserved_intents:
            telemetry_bus.emit(TelemetryEvent(
                event_type="intent_preserved",
                session_id=session_id,
                request_id=request_id,
                payload={"intent_id": intent.intent_id, "description": intent.description},
            ))
        for intent in delta_plan.affected_intents:
            telemetry_bus.emit(TelemetryEvent(
                event_type="intent_retrieved",
                session_id=session_id,
                request_id=request_id,
                payload={"intent_id": intent.intent_id, "description": intent.description},
            ))
        
        # 3. Execute Retrieval
        new_evidence = []
        if queries:
            new_evidence = await self.pipeline.execute(queries, session_id)
        else:
            telemetry_bus.emit(TelemetryEvent(
                event_type="retrieval_suppressed",
                session_id=session_id,
                request_id=request_id,
                payload={"reason": "no_affected_intents"},
            ))
            
        # 4. Merge Evidence (Preserve untouched evidence, drop obsolete/replaced evidence)
        # We also need to map the old intent IDs to the new intent IDs for preserved intents
        # so we can keep their evidence. 
        # In this heuristic, we map by description.
        desc_to_new_id = {i.description: i.intent_id for i in delta_plan.preserved_intents}
        desc_to_old_id = {i.description: i.intent_id for i in session.intents if i.description in desc_to_new_id}
        
        old_id_to_new_id = {desc_to_old_id[desc]: desc_to_new_id[desc] for desc in desc_to_new_id}
        
        merged_evidence = []
        for ev in session.evidence:
            kept_intent_ids = []
            for old_i_id in ev.intent_ids:
                if old_i_id in old_id_to_new_id:
                    kept_intent_ids.append(old_id_to_new_id[old_i_id])
            
            if kept_intent_ids:
                ev_copy = ev.model_copy()
                ev_copy.intent_ids = kept_intent_ids
                merged_evidence.append(ev_copy)
                
        # Combine and global deduplicate
        all_evidence = merged_evidence + new_evidence
        final_evidence = self.pipeline._deduplicate(all_evidence)
        
        # 5. Update Session State
        session.current_version += 1
        session.intents = new_intents
        session.evidence = final_evidence
        
        telemetry_bus.emit(TelemetryEvent(
            event_type="session_state_updated",
            session_id=session_id,
            request_id=request_id,
            payload={
                "version": session.current_version,
                "total_evidence": len(session.evidence),
                "affected_executed": len(queries)
            }
        ))
        
        return session

    def create_answer_version(
        self,
        session_id: str,
        request_id: str,
        claims: list[Claim],
        evidence: list[Evidence] | None = None,
        trigger_delta: dict[str, object] | None = None,
    ) -> AnswerVersion:
        """Render and append an answer for the current closed-corpus state."""
        session = self.get_or_create_session(session_id)
        answer = self.answer_store.create(
            session_id,
            request_id,
            claims,
            evidence if evidence is not None else session.evidence,
            trigger_delta,
        )
        self.answers[session_id] = self.answer_store.list(session_id)
        return answer
