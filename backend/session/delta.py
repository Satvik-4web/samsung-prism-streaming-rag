from backend.schemas.delta import DeltaPlan, DeltaType
from backend.schemas.intents import Intent
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus

class DeltaEngine:
    def compute(self, current_intents: list[Intent], new_intents: list[Intent], session_id: str, request_id: str) -> DeltaPlan:
        plan = DeltaPlan()
        current_map = {i.description: i for i in current_intents}
        
        for new_intent in new_intents:
            if new_intent.description in current_map:
                curr = current_map[new_intent.description]
                curr_c = sorted([(c.key, c.value) for c in curr.constraints])
                new_c = sorted([(c.key, c.value) for c in new_intent.constraints])
                
                if curr_c != new_c:
                    plan.affected_intents.append(new_intent)
                    plan.delta_states[new_intent.intent_id] = DeltaType.CHANGED
                    plan.changed_constraints.append({
                        "intent_id": new_intent.intent_id,
                        "old": curr_c,
                        "new": new_c
                    })
                else:
                    plan.preserved_intents.append(new_intent)
                    plan.delta_states[new_intent.intent_id] = DeltaType.UNCHANGED
            else:
                plan.affected_intents.append(new_intent)
                plan.delta_states[new_intent.intent_id] = DeltaType.ADDED
                
        new_map = {i.description: i for i in new_intents}
        for curr_intent in current_intents:
            if curr_intent.description not in new_map:
                plan.obsolete_intents.append(curr_intent)
                plan.delta_states[curr_intent.intent_id] = DeltaType.REMOVED
                
        telemetry_bus.emit(TelemetryEvent(
            event_type="delta_computed",
            session_id=session_id,
            request_id=request_id,
            payload={
                "affected_count": len(plan.affected_intents),
                "preserved_count": len(plan.preserved_intents),
                "obsolete_count": len(plan.obsolete_intents),
                "changed_constraints": plan.changed_constraints,
                "delta_states": {k: v.value for k, v in plan.delta_states.items()}
            }
        ))
        return plan
