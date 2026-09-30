import re
import uuid

from backend.schemas.intents import Constraint, Intent
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class HeuristicSegmenter:
    def __init__(self) -> None:
        self.split_patterns = [r"\band what\b", r"\band also\b", r"\bwhat are\b", r"\bcan you\b", r"\?"]
        self.location_pattern = r"\bin ([A-Z][a-z]+)\b"

    def segment(self, text: str, request_id: str, session_id: str) -> list[Intent]:
        # Extract shared constraints (e.g., location)
        shared_constraints = []
        loc_match = re.search(self.location_pattern, text)
        if loc_match:
            shared_constraints.append(Constraint(key="location", value=loc_match.group(1)))
            
        # Basic split heuristic
        segments = [text]
        for pattern in self.split_patterns:
            new_segments = []
            for seg in segments:
                parts = re.split(pattern, seg, flags=re.IGNORECASE)
                for i, part in enumerate(parts):
                    if i > 0 and pattern != r"\?":
                        # re-attach a rough heuristic of the split word if needed, or just keep it simple
                        part = part.strip()
                    if part.strip():
                        new_segments.append(part.strip())
            segments = new_segments
            
        # Deduplicate and filter small fragments to avoid over-fragmentation
        valid_segments = [s for s in segments if len(s.split()) >= 3]
        if not valid_segments:
            valid_segments = [text]  # Fallback to full text if over-fragmented
            
        intents = []
        for i, seg in enumerate(valid_segments):
            intent = Intent(
                intent_id=str(uuid.uuid4()),
                parent_request_id=request_id,
                description=seg,
                constraints=shared_constraints.copy()
            )
            intents.append(intent)
            
            telemetry_bus.emit(TelemetryEvent(
                event_type="intent_decomposed",
                session_id=session_id,
                request_id=request_id,
                payload={"intent_id": intent.intent_id, "description": intent.description}
            ))
            
        return intents

