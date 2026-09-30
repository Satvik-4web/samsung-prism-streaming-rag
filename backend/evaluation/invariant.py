from backend.schemas.generation import AnswerVersion
from backend.schemas.delta import DeltaPlan, DeltaType

class RefinementInvariantError(Exception):
    pass

def validate_refinement(prev_v: AnswerVersion, curr_v: AnswerVersion, delta: DeltaPlan) -> dict:
    prev_claims = {c.claim_id: c for c in prev_v.claims}
    curr_claims = {c.claim_id: c for c in curr_v.claims}
    
    preserved = 0
    changed = 0
    
    # Check that UNCHANGED intents perfectly preserve their claims
    for intent in delta.preserved_intents:
        # Find claims mapping to this intent in prev and curr
        prev_i_claims = [c for c in prev_v.claims if c.intent_id == intent.intent_id]
        curr_i_claims = [c for c in curr_v.claims if c.intent_id == intent.intent_id]
        
        if len(prev_i_claims) != len(curr_i_claims):
            raise RefinementInvariantError(f"Claim count mismatch for preserved intent {intent.intent_id}")
            
        for pc, cc in zip(prev_i_claims, curr_i_claims):
            if pc.text != cc.text:
                raise RefinementInvariantError(f"Claim text mutated for preserved intent! {pc.text} != {cc.text}")
            if pc.citations != cc.citations:
                raise RefinementInvariantError("Claim citations mutated for preserved intent!")
            preserved += 1
            
    for intent in delta.affected_intents:
        changed += sum(1 for c in curr_v.claims if c.intent_id == intent.intent_id)
        
    return {
        "preserved_claims": preserved,
        "changed_claims": changed,
        "added_claims": len(curr_claims) - len(prev_claims) if len(curr_claims) > len(prev_claims) else 0,
        "removed_claims": len(prev_claims) - len(curr_claims) if len(prev_claims) > len(curr_claims) else 0
    }
