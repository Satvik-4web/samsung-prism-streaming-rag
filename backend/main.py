import os
import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from backend.config import settings
from backend.logger import setup_logging
from backend.streaming.buffer import StreamBuffer
from backend.controller.rules import RetrievalController
from backend.intents.segmenter import HeuristicSegmenter
from backend.session.manager import SessionManager
from backend.retrieval.pipeline import RetrievalPipeline
from backend.retrieval.sparse.bm25 import BM25Retriever
from backend.retrieval.dense.faiss_index import FaissRetriever
from backend.retrieval.dense.embedder import Embedder
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
        fixture_path = os.path.join("data", "dev_fixture", "sample_policy.md")
        try:
            docs = list(adapter.load(fixture_path))
            self.chunks = []
            for d in docs:
                self.chunks.extend(adapter.chunk(d))
        except Exception:
            self.chunks = []
            
        # Init Retrievers
        class DummyEmbedder(Embedder):
            def embed(self, texts):
                return [[len(t)*0.1, 0.5] for t in texts] # Fast mock embedder for dev

        self.sparse = BM25Retriever(self.chunks)
        self.dense = FaissRetriever(self.chunks, DummyEmbedder())
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

@app.post("/session/{session_id}/reset")
def reset_session(session_id: str):
    if session_id in state.manager.sessions:
        del state.manager.sessions[session_id]
    if session_id in state.manager.answers:
        del state.manager.answers[session_id]
    if session_id in state.buffer.sessions:
        del state.buffer.sessions[session_id]
    return {"status": "reset"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    request_id = str(uuid.uuid4())
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Streaming flow
            if data.get("type") == "chunk":
                chunk = StreamChunk(
                    session_id=session_id,
                    seq=data.get("seq", 0),
                    t_ms=data.get("t_ms", 0),
                    text=data["text"],
                    is_final=data.get("is_final", False)
                )
                
                utt_state = state.buffer.append(chunk)
                
                # Check Controller
                decision = state.controller.evaluate(utt_state, chunk.t_ms)
                
                await websocket.send_json({
                    "event": "controller_decision",
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "text": utt_state.committed_text
                })
                
                if decision.decision == "RETRIEVE":
                    # Multi-Intent
                    intents = state.segmenter.segment(utt_state.committed_text, request_id, session_id)
                    await websocket.send_json({"event": "intents_extracted", "intents": [i.model_dump() for i in intents]})
                    
                    # Delta & Retrieval
                    sess = await state.manager.process_intents(session_id, request_id, intents)
                    
                    # Grounding & Generate Answer
                    # In a real app we'd map intent to generation explicitly. We just generate over all.
                    claims = [
                        # Mock simple claim extraction from intents for demonstration
                        # A real system would use LLM here
                    ]
                    for intent in sess.intents:
                        from backend.schemas.generation import Claim
                        # Mock claim extraction
                        claim = Claim(claim_id=str(uuid.uuid4()), text=f"Details about {intent.description}", intent_id=intent.intent_id, supported_by_chunk_ids=[ev.chunk_id for ev in sess.evidence if intent.intent_id in ev.intent_ids])
                        claims.append(claim)
                    
                    # Grounding
                    verified_claims = state.verifier.verify(claims, sess.evidence, session_id)
                    
                    # Generate Answer Version
                    parent_versions = state.manager.answers.get(session_id, [])
                    parent = parent_versions[-1] if parent_versions else None
                    answer_v = state.generator.generate(
                        claims=verified_claims, 
                        evidence=sess.evidence, 
                        session_id=session_id, 
                        request_id=request_id,
                        version=(parent.version + 1) if parent else 1,
                        parent=parent
                    )
                    
                    # Save version
                    if session_id not in state.manager.answers:
                        state.manager.answers[session_id] = []
                    state.manager.answers[session_id].append(answer_v)
                    
                    await websocket.send_json({
                        "event": "answer_generated",
                        "answer": answer_v.model_dump(),
                        "evidence": [e.model_dump() for e in sess.evidence]
                    })
                    
    except WebSocketDisconnect:
        pass
