from backend.intents.planner import QueryPlanner
from backend.intents.segmenter import HeuristicSegmenter


def test_single_intent() -> None:
    segmenter = HeuristicSegmenter()
    intents = segmenter.segment("I need to plan a customer workshop in Pune.", "req1", "s1")
    assert len(intents) == 1
    assert intents[0].description == "I need to plan a customer workshop in Pune."
    # Extracted location constraint
    assert any(c.key == "location" and c.value == "Pune" for c in intents[0].constraints)

def test_compound_intent() -> None:
    segmenter = HeuristicSegmenter()
    text = "I need to plan a customer workshop in Pune. What venues can accommodate 80 people, and what are the cancellation policies?"
    intents = segmenter.segment(text, "req1", "s1")
    assert len(intents) >= 2
    
    # Shared constraint propagates to all intents
    for intent in intents:
        assert any(c.key == "location" and c.value == "Pune" for c in intent.constraints)
        
def test_query_planner() -> None:
    segmenter = HeuristicSegmenter()
    planner = QueryPlanner()
    text = "I need to plan a customer workshop in Pune."
    intents = segmenter.segment(text, "req1", "s1")
    queries = planner.plan(intents, "s1")
    
    assert len(queries) == 1
    assert queries[0].query_text == text
    assert len(queries[0].constraints) > 0
