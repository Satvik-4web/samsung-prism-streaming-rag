import argparse
import json
import sys
from pathlib import Path

from backend.controller.rules import RetrievalController
from backend.schemas.streaming import StreamChunk
from backend.streaming.buffer import StreamBuffer


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless Replay Script")
    parser.add_argument("scenario", type=str, help="Path to scenario JSONL")
    args = parser.parse_args()
    
    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        print(f"Error: {scenario_path} not found.")
        sys.exit(1)
        
    buffer = StreamBuffer()
    controller = RetrievalController()
    
    print(f"Replaying scenario: {scenario_path.name}")
    with open(scenario_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            chunk = StreamChunk(**data)
            
            # 1. Add to buffer
            state = buffer.add_chunk(chunk)
            print(f"[{chunk.t_ms:04d}ms] Buf: '{state.full_text}'")
            
            # 2. Controller evaluate
            decision = controller.evaluate(state, chunk.t_ms)
            print(f"  -> Decision: {decision.decision} (Reason: {decision.reason}, Conf: {decision.confidence:.2f})")
            
if __name__ == "__main__":
    main()
