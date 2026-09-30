from backend.schemas.controller import ControllerFeatures
from backend.schemas.streaming import UtteranceState


def extract_features(state: UtteranceState, previous_text: str = "") -> ControllerFeatures:
    text = state.full_text.strip()
    words = text.split()
    prev_words = previous_text.split()
    
    dangling_tail = False
    if words:
        last_word = words[-1].lower()
        dangling_tail = last_word in {"in", "the", "and", "a", "an", "of", "to", "for", "with", "at"}
        
    # Heuristic for completeness: length and non-stop words
    completeness = min(1.0, len([w for w in words if w.lower() not in {"is", "are", "the", "a", "an", "i", "need"}]) / 4.0)
    
    # Stability: intersection of words
    stability = 0.0
    if len(words) > 0:
        common = set(words).intersection(set(prev_words))
        stability = len(common) / len(words)
        if len(words) == len(prev_words):
            stability = 1.0  # highly stable if no new words
            
    info_gain = len(set(words) - set(prev_words))
    
    return ControllerFeatures(
        stability=stability,
        completeness=completeness,
        dangling_tail=dangling_tail,
        utterance_end=state.ended,
        new_content_tokens=info_gain,
        retrieved_before=False,  # Stub for session tracking
        cooldown_ok=True         # Stub for timing
    )
