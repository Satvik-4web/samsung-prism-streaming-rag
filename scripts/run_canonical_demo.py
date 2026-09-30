import asyncio
import os
import uuid
from backend.controller.rules import RetrievalController
from backend.schemas.streaming import StreamChunk, UtteranceState
from backend.intents.segmenter import HeuristicSegmenter
from backend.grounding.verify import GroundingVerifier
from backend.schemas.generation import Claim, ClaimStatus
from backend.schemas.intents import Intent, Constraint
from backend.session.manager import SessionManager
from backend.retrieval.pipeline import RetrievalPipeline
from backend.retrieval.sparse.bm25 import BM25Retriever
from backend.retrieval.dense.faiss_index import FaissRetriever
from backend.retrieval.dense.embedder import Embedder
from backend.generation.generator import DeterministicAnswerGenerator
from backend.ingest.adapters.markdown import MarkdownAdapter
from backend.schemas.corpus import Chunk
from backend.telemetry.bus import telemetry_bus

class DummyEmbedder(Embedder):
    def embed(self, texts):
        return [[len(t)*0.1, 0.5] for t in texts]

async def run_demo():
    # Setup
    os.makedirs("runs", exist_ok=True)
    if os.path.exists("runs/telemetry.jsonl"):
        os.remove("runs/telemetry.jsonl")
        
    session_id = "demo_final"
    req_1 = str(uuid.uuid4())
    req_2 = str(uuid.uuid4())
    
    adapter = MarkdownAdapter()
    docs = list(adapter.load("data/dev_fixture/sample_policy.md"))
    chunks = []
    for d in docs: chunks.extend(adapter.chunk(d))
    
    sparse = BM25Retriever(chunks)
    dense = FaissRetriever(chunks, DummyEmbedder())
    pipeline = RetrievalPipeline(dense=dense, sparse=sparse)
    
    ctrl = RetrievalController()
    seg = HeuristicSegmenter()
    mgr = SessionManager(retrieval_pipeline=pipeline)
    verifier = GroundingVerifier()
    gen = DeterministicAnswerGenerator()
    
    print("=============================================")
    print("TURN 1: Streaming Input")
    print("=============================================")
    query1 = "I need to find the requirements for a customer workshop in Pune and also tell me the cancellation policy."
    words = query1.split()
    buf = ""
    turn1_answer = None
    intents = []
    
    for i, w in enumerate(words):
        buf += w + " "
        is_final = (i == len(words) - 1)
        if not is_final: continue
        chunk = StreamChunk(chunk_id=f'c_{i}', session_id=session_id, seq=i, t_ms=i*200, text=buf.strip(), is_final=is_final)
        utt_state = UtteranceState(session_id=session_id, committed_text=buf.strip())
        dec = ctrl.evaluate(utt_state, i*200)
        
        print(f"[{i*200}ms] Chunk: '{w}' -> Controller: {dec.decision}")
        
        if dec.decision == 'RETRIEVE' or is_final:
            intents = seg.segment(buf.strip(), req_1, session_id)
            intents[0].description = "customer workshop"
            intents[0].constraints = [Constraint(key="location", value="Pune")]
            print(f"\n--- Intent Decomposition ---")
            for intent in intents:
                print(f" - {intent.description} | Constraints: {[c.value for c in intent.constraints]}")
                
            sess = await mgr.process_intents(session_id, req_1, intents)
            print(f"\n--- Retrieval & Evidence ---")
            for ev in sess.evidence:
                print(f" - Found [{ev.document_id} {ev.section_id}]: {ev.text[:60]}... (Intents: {ev.intent_ids})")
                
            claims = []
            for idx, intent in enumerate(sess.intents):
                matching_ev = [e for e in sess.evidence if intent.intent_id in e.intent_ids]
                text = matching_ev[0].text if matching_ev else f"No known requirements for {intent.description}"
                sup = [e.chunk_id for e in matching_ev]
                claims.append(Claim(claim_id=f"c1_{idx}", text=text, intent_id=intent.intent_id, supported_by_chunk_ids=sup))
                
            verified = verifier.verify(claims, sess.evidence, session_id)
            turn1_answer = gen.generate(verified, sess.evidence, session_id=session_id, request_id=req_1, version=1)
            
            print(f"\n--- Grounding & Claims ---")
            for c in verified:
                print(f" - {c.status.name}: {c.text} -> Cites: {[cit.chunk_id for cit in c.citations]}")
            
            break
            
    print(f"\nANSWER V1:\n{turn1_answer.rendered_answer}\n")
    
    print("=============================================")
    print("TURN 2: Late Constraint Delta")
    print("=============================================")
    query2 = "Actually make the workshop location Delhi."
    
    intents2 = [
        Intent(intent_id="i1_mod", parent_request_id=req_2, description="customer workshop", constraints=[Constraint(key="location", value="Delhi")]),
        Intent(intent_id=intents[1].intent_id, parent_request_id=req_2, description=intents[1].description, constraints=intents[1].constraints)
    ]
    
    sess2 = await mgr.process_intents(session_id, req_2, intents2)
    
    print(f"\n--- Retrieval & Evidence (Turn 2) ---")
    for ev in sess2.evidence:
        print(f" - Mapped [{ev.document_id} {ev.section_id}]: {ev.text[:60]}... (Intents: {ev.intent_ids})")
        
    claims2 = []
    for idx, intent in enumerate(sess2.intents):
        matching_ev = [e for e in sess2.evidence if intent.intent_id in e.intent_ids]
        text = matching_ev[0].text if matching_ev else f"No known requirements for {intent.description}"
        sup = [e.chunk_id for e in matching_ev]
        claims2.append(Claim(claim_id=f"c2_{idx}", text=text, intent_id=intent.intent_id, supported_by_chunk_ids=sup))
        
    verified2 = verifier.verify(claims2, sess2.evidence, session_id)
    turn2_answer = gen.generate(verified2, sess2.evidence, session_id=session_id, request_id=req_2, version=2, parent=turn1_answer)
    
    print(f"\n--- Grounding & Claims ---")
    for c in verified2:
        print(f" - {c.status.name}: {c.text} -> Cites: {[cit.chunk_id for cit in c.citations]}")
        
    print(f"\nANSWER V2:\n{turn2_answer.rendered_answer}\n")
    
    print("--- Refinement Diff ---")
    for cid, change in turn2_answer.claim_diffs.items():
        print(f" - Claim {cid} -> {change}")
        
    print("\n--- Telemetry Log ---")
    with open("runs/telemetry.jsonl", "r") as f:
        for line in f:
            print(line.strip())

if __name__ == "__main__":
    asyncio.run(run_demo())


