import logging
from datetime import UTC, datetime

from backend.schemas.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)

class TelemetryBus:
    def __init__(self, sink_path: str = "runs/telemetry.jsonl") -> None:
        self.sink_path = sink_path
        
    def emit(self, event: TelemetryEvent) -> None:
        if not event.ts:
            event.ts = datetime.now(UTC).isoformat()
        try:
            with open(self.sink_path, "a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        except OSError as e:
            logger.error(f"Failed to emit telemetry event: {e}")

# Global instance for the app
telemetry_bus = TelemetryBus()
