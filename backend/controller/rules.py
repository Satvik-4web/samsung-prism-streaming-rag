from backend.config import settings
from backend.controller.classifier import classify_query
from backend.controller.features import extract_features
from backend.schemas.controller import ControllerDecision
from backend.schemas.streaming import UtteranceState
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class RetrievalController:
    def __init__(self) -> None:
        self.last_retrieval_ms: dict[str, int] = {}
        self.last_chunk_text: dict[str, str] = {}
        
    def evaluate(self, state: UtteranceState, current_t_ms: int) -> ControllerDecision:
        prev_text = self.last_chunk_text.get(state.session_id, "")
        features = extract_features(state, prev_text)
        features.query_type = classify_query(state.full_text)
        
        last_ms = self.last_retrieval_ms.get(state.session_id, 0)
        features.cooldown_ok = (current_t_ms - last_ms) >= settings.controller.thresholds.debounce_ms
        
        # Always track the text of the last chunk for stability calculations
        self.last_chunk_text[state.session_id] = state.full_text
        
        if not state.full_text.strip():
            decision = ControllerDecision(decision="WAIT", reason="empty", features=features)
            self._emit(state, current_t_ms, decision)
            return decision
            
        if features.query_type == "transformation":
            decision = ControllerDecision(decision="NO_RETRIEVE", reason="presentation_restructuring", features=features)
            self._emit(state, current_t_ms, decision)
            return decision
            
        if features.utterance_end:
            decision = ControllerDecision(
                decision="RETRIEVE", 
                trigger="final", 
                reason="utterance_ended", 
                retrieval_required=True, 
                features=features
            )
            self.last_retrieval_ms[state.session_id] = current_t_ms
            self._emit(state, current_t_ms, decision)
            return decision
            
        if features.dangling_tail:
            decision = ControllerDecision(decision="WAIT", reason="dangling_tail", features=features)
            self._emit(state, current_t_ms, decision)
            return decision
            
        w = settings.controller.weights
        score = (w.stability * features.stability) + (w.completeness * features.completeness) + (w.info_gain * min(1.0, features.new_content_tokens / 5.0))
        
        if score >= settings.controller.thresholds.retrieve and features.cooldown_ok and features.new_content_tokens >= settings.controller.thresholds.min_info_gain:
            decision = ControllerDecision(
                decision="RETRIEVE",
                trigger="provisional",
                confidence=score,
                reason="stable_entities_and_information_seeking",
                retrieval_required=True,
                features=features
            )
            self.last_retrieval_ms[state.session_id] = current_t_ms
            self._emit(state, current_t_ms, decision)
            return decision
            
        decision = ControllerDecision(decision="WAIT", reason="score_below_threshold", confidence=score, features=features)
        self._emit(state, current_t_ms, decision)
        return decision
        
    def _emit(self, state: UtteranceState, t_ms: int, dec: ControllerDecision) -> None:
        event_type = "retrieval_suppressed" if dec.decision == "NO_RETRIEVE" else "retrieval_decision"
        telemetry_bus.emit(TelemetryEvent(
            event_type=event_type,
            session_id=state.session_id,
            t_stream_ms=t_ms,
            seq=state.last_seq,
            payload=dec.model_dump()
        ))
