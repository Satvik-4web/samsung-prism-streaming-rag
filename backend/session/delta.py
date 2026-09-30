
from backend.schemas.delta import DeltaPlan
from backend.schemas.intents import Intent
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class DeltaEngine:
    def compute(self, current_intents: list[Intent], new_intents: list[Intent], session_id: str, request_id: str) -> DeltaPlan:
        plan = DeltaPlan()
        
        # Simple heuristic mapping by description
        # In a full system, an LLM or semantic similarity would align intents
        current_map = {i.description: i for i in current_intents}
        
        for new_intent in new_intents:
            if new_intent.description in current_map:
                curr = current_map[new_intent.description]
                
                # Check if constraints changed
                curr_c = sorted([(c.key, c.value) for c in curr.constraints])
                new_c = sorted([(c.key, c.value) for c in new_intent.constraints])
                
                if curr_c != new_c:
                    plan.affected_intents.append(new_intent)
                    plan.changed_constraints.append({
                        "intent_id": new_intent.intent_id,
                        "old": curr_c,
                        "new": new_c
                    })
                else:
                    plan.preserved_intents.append(new_intent)
            else:
                # Completely new intent
                plan.affected_intents.append(new_intent)
                
        # Any current intents not in new_intents are technically obsolete
        new_map = {i.description: i for i in new_intents}
        for curr_intent in current_intents:
            if curr_intent.description not in new_map:
                plan.obsolete_intents.append(curr_intent)
                
        telemetry_bus.emit(TelemetryEvent(
            event_type="delta_computed",
            session_id=session_id,
            request_id=request_id,
            payload={
                "affected_count": len(plan.affected_intents),
                "preserved_count": len(plan.preserved_intents),
                "changed_constraints": plan.changed_constraints
            }
        ))
        
        return plan
