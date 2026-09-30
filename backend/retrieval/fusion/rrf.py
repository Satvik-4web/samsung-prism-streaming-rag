
from backend.schemas.evidence import Evidence


def reciprocal_rank_fusion(candidates_lists: list[list[Evidence]], k: int = 60) -> list[Evidence]:
    rrf_scores: dict[str, float] = {}
    evidence_map: dict[str, Evidence] = {}
    
    for candidate_list in candidates_lists:
        for rank, evidence in enumerate(candidate_list):
            doc_id = evidence.chunk_id
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                # Copy the first instance of evidence found
                evidence_map[doc_id] = evidence.model_copy()
                evidence_map[doc_id].retrieval_source = "rrf"
                evidence_map[doc_id].scores = {}
                
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)
            
            # Combine intent_ids safely
            for i_id in evidence.intent_ids:
                if i_id not in evidence_map[doc_id].intent_ids:
                    evidence_map[doc_id].intent_ids.append(i_id)
            
            # Store original scores for tracing
            for s_key, s_val in evidence.scores.items():
                evidence_map[doc_id].scores[s_key] = s_val
                
    # Assign the calculated RRF score
    for doc_id, score in rrf_scores.items():
        evidence_map[doc_id].scores["rrf"] = score
        
    sorted_results = sorted(evidence_map.values(), key=lambda x: x.scores["rrf"], reverse=True)
    return sorted_results
