import os
import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time
import uuid

from backend.config import settings
from backend.logger import setup_logging
from backend.streaming.buffer import StreamBuffer
from backend.controller.rules import RetrievalController
from backend.intents.segmenter import HeuristicSegmenter
from backend.session.manager import SessionManager
from backend.retrieval.pipeline import RetrievalPipeline
from backend.retrieval.sparse.bm25 import BM25Retriever
from backend.retrieval.dense.faiss_index import FaissRetriever
from backend.retrieval.dense.embedder import get_embedder
from backend.generation.generator import DeterministicAnswerGenerator
from backend.grounding.verify import GroundingVerifier
from backend.schemas.streaming import StreamChunk
from backend.telemetry.bus import telemetry_bus
from backend.ingest.adapters.markdown import MarkdownAdapter
from backend.schemas.corpus import Chunk

setup_logging()

app = FastAPI(title="PRISM Streaming RAG", debug=settings.debug)

# Enable CORS for local dev frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dependencies
class AppState:
    def __init__(self):
        self.buffer = StreamBuffer()
        self.controller = RetrievalController()
        self.segmenter = HeuristicSegmenter()
        self.verifier = GroundingVerifier()
        self.generator = DeterministicAnswerGenerator()
        
        # Load Corpus
        adapter = MarkdownAdapter()
        fixture_path = os.path.join("data", "dev_fixture", "samsung_products.md")
        try:
            docs = list(adapter.load(fixture_path))
            self.chunks = []
            for d in docs:
                self.chunks.extend(adapter.chunk(d))
        except Exception:
            self.chunks = []
            
        # Init Retrievers
        self.sparse = BM25Retriever(self.chunks)
        self.dense = FaissRetriever(self.chunks, get_embedder())
        self.pipeline = RetrievalPipeline(dense=self.dense, sparse=self.sparse)
        
        self.manager = SessionManager(retrieval_pipeline=self.pipeline)

state = AppState()

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}

@app.get("/session/{session_id}")
def get_session(session_id: str):
    sess = state.manager.get_or_create_session(session_id)
    answers = state.manager.answers.get(session_id, [])
    return {
        "session": sess.model_dump(),
        "answers": [a.model_dump() for a in answers]
    }

@app.get("/session/{session_id}/reset")
def reset_session(session_id: str):
    if session_id in state.manager.sessions:
        del state.manager.sessions[session_id]
    if session_id in state.manager.answers:
        del state.manager.answers[session_id]
    if session_id in state.buffer.sessions:
        del state.buffer.sessions[session_id]
    
    # CRITICAL: Clear seen_chunks for this session to allow re-running deterministic scenarios
    to_remove = [cid for cid in state.buffer.seen_chunks if cid.startswith(f"{session_id}_")]
    for cid in to_remove:
        state.buffer.seen_chunks.remove(cid)
        
    return {"status": "reset"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    print(f'Incoming WS connection: {session_id}')
    await websocket.accept()
    request_id = str(uuid.uuid4())
    active_task = None
    
    async def process_retrieval(utt_state, req_id):
        t0 = time.perf_counter()
        try:
            intents = state.segmenter.segment(utt_state.committed_text, req_id, session_id)
            await websocket.send_json({'event': 'intents_extracted', 'intents': [i.model_dump() for i in intents]})
            sess = await state.manager.process_intents(session_id, req_id, intents)
            claims = []
            for intent in sess.intents:
                from backend.schemas.generation import Claim
                matching_ev = [ev for ev in sess.evidence if intent.intent_id in ev.intent_ids]
                if matching_ev:
                    for ev in matching_ev:
                        claims.append(Claim(claim_id=str(uuid.uuid4()), text=ev.text, intent_id=intent.intent_id, supported_by_chunk_ids=[ev.chunk_id]))
                else:
                    claims.append(Claim(claim_id=str(uuid.uuid4()), text=f'No details found for {intent.description}', intent_id=intent.intent_id, supported_by_chunk_ids=[]))
            verified_claims = state.verifier.verify(claims, sess.evidence, session_id)
            parent_versions = state.manager.answers.get(session_id, [])
            parent = parent_versions[-1] if parent_versions else None
            answer_v = state.generator.generate(
                claims=verified_claims, evidence=sess.evidence, session_id=session_id, request_id=req_id,
                version=(parent.version + 1) if parent else 1, parent=parent)
            if session_id not in state.manager.answers: state.manager.answers[session_id] = []
            state.manager.answers[session_id].append(answer_v)
            await websocket.send_json({'event': 'answer_generated', 'answer': answer_v.model_dump(), 'evidence': [e.model_dump() for e in sess.evidence]})
            from backend.schemas.telemetry import TelemetryEvent
            telemetry_bus.emit(TelemetryEvent(event_type='retrieval_completed', session_id=session_id, payload={'request_id': req_id, 'total_latency_ms': (time.perf_counter() - t0) * 1000}))
        except asyncio.CancelledError:
            from backend.schemas.telemetry import TelemetryEvent
            telemetry_bus.emit(TelemetryEvent(event_type='retrieval_cancelled', session_id=session_id, payload={'request_id': req_id}))
            raise
        except Exception as e:
            print(f'Pipeline error: {e}')

    try:
        while True:
            data = await websocket.receive_json()
            print(f'WS RX: {data}')
            if data.get('type') == 'chunk':
                chunk = StreamChunk(
                    session_id=session_id, seq=data.get('seq', 0), t_ms=data.get('t_ms', 0),
                    text=data['text'], is_final=data.get('is_final', False), 
                    chunk_id=data.get('chunk_id', f'{session_id}_{data.get("seq", 0)}')
                )
                utt_state = state.buffer.add_chunk(chunk)
                decision = state.controller.evaluate(utt_state, chunk.t_ms)
                await websocket.send_json({'event': 'controller_decision', 'decision': decision.decision, 'reason': decision.reason, 'text': utt_state.full_text})
                if decision.decision == 'RETRIEVE':
                    if active_task and not active_task.done():
                        active_task.cancel()
                    req_id = str(uuid.uuid4())
                    active_task = asyncio.create_task(process_retrieval(utt_state, req_id))
    except WebSocketDisconnect:
        pass




