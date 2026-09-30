from backend.schemas.streaming import StreamChunk, UtteranceState
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class StreamBuffer:
    def __init__(self) -> None:
        self.sessions: dict[str, UtteranceState] = {}
        self.seen_chunks: set[str] = set()
        self.reorder_window_ms: int = 500
        
    def add_chunk(self, chunk: StreamChunk) -> UtteranceState:
        # Idempotency / duplicates
        if chunk.chunk_id in self.seen_chunks:
            telemetry_bus.emit(TelemetryEvent(
                event_type="chunk_duplicate_ignored",
                session_id=chunk.session_id,
                seq=chunk.seq,
                t_stream_ms=chunk.t_ms,
                payload={"chunk_id": chunk.chunk_id}
            ))
            return self.sessions.get(chunk.session_id, UtteranceState(session_id=chunk.session_id))
        
        self.seen_chunks.add(chunk.chunk_id)
        
        telemetry_bus.emit(TelemetryEvent(
            event_type="stream_received",
            session_id=chunk.session_id,
            seq=chunk.seq,
            t_stream_ms=chunk.t_ms,
            payload={"text": chunk.text, "is_final": chunk.is_final}
        ))

        if chunk.session_id not in self.sessions:
            self.sessions[chunk.session_id] = UtteranceState(session_id=chunk.session_id)
            
        state = self.sessions[chunk.session_id]
        
        # Late chunk handling (seq older than last_seq)
        if chunk.seq <= state.last_seq:
            telemetry_bus.emit(TelemetryEvent(
                event_type="chunk_late",
                session_id=chunk.session_id,
                seq=chunk.seq,
                t_stream_ms=chunk.t_ms,
                payload={"last_seq": state.last_seq}
            ))
            # simplified late handling: just append to volatile tail to not lose it
            state.volatile_tail = (state.volatile_tail + " " + chunk.text).strip()
        else:
            state.volatile_tail = (state.volatile_tail + " " + chunk.text).strip()
            state.last_seq = chunk.seq
            
        if chunk.is_final:
            state.ended = True
            state.committed_text = state.full_text
            state.volatile_tail = ""
            telemetry_bus.emit(TelemetryEvent(
                event_type="utterance_end",
                session_id=chunk.session_id,
                seq=chunk.seq,
                t_stream_ms=chunk.t_ms
            ))
            
        return state
