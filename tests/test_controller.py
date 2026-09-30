from backend.controller.rules import RetrievalController
from backend.schemas.streaming import UtteranceState


def test_incomplete_wait() -> None:
    ctrl = RetrievalController()
    state = UtteranceState(session_id="1", committed_text="a", volatile_tail="workshop in")
    dec = ctrl.evaluate(state, 100)
    assert dec.decision == "WAIT"

def test_stable_retrieve() -> None:
    ctrl = RetrievalController()
    # Step 1: initial text
    state1 = UtteranceState(session_id="2", committed_text="I need to plan a customer workshop in")
    ctrl.evaluate(state1, 0)
    
    # Step 2: add a word, highly stable, info gain = 1
    state2 = UtteranceState(session_id="2", committed_text="I need to plan a customer workshop in Pune")
    dec = ctrl.evaluate(state2, 1000)
    assert dec.decision == "RETRIEVE"
    assert dec.trigger == "provisional"

def test_transformation_no_retrieve() -> None:
    ctrl = RetrievalController()
    state = UtteranceState(session_id="3", committed_text="summarize that in two bullets")
    dec = ctrl.evaluate(state, 100)
    assert dec.decision == "NO_RETRIEVE"

def test_utterance_end() -> None:
    ctrl = RetrievalController()
    state = UtteranceState(session_id="4", committed_text="query", ended=True)
    dec = ctrl.evaluate(state, 100)
    assert dec.decision == "RETRIEVE"
    assert dec.trigger == "final"
