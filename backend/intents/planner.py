
from backend.schemas.intents import Intent, RetrievalQuery
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class QueryPlanner:
    def plan(self, intents: list[Intent], session_id: str) -> list[RetrievalQuery]:
        queries = []
        for intent in intents:
            query = RetrievalQuery(
                intent_id=intent.intent_id,
                parent_request_id=intent.parent_request_id,
                query_text=intent.description,
                constraints=intent.constraints,
                top_k=5,
                retrieval_strategy="hybrid"
            )
            queries.append(query)
            
            telemetry_bus.emit(TelemetryEvent(
                event_type="subquery_created",
                session_id=session_id,
                request_id=intent.parent_request_id,
                payload={"intent_id": intent.intent_id, "query_text": query.query_text}
            ))
        return queries
