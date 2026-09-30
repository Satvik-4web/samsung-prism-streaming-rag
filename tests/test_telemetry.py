from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import TelemetryBus


def test_telemetry_emission(tmp_path) -> None:
    sink = tmp_path / "telemetry.jsonl"
    bus = TelemetryBus(sink_path=str(sink))
    event = TelemetryEvent(event_type="test", session_id="1", t_stream_ms=100)
    bus.emit(event)
    
    with open(sink, "r") as f:
        data = f.read()
        assert "test" in data
        assert "100" in data
