from backend.schemas.streaming import StreamChunk
from backend.streaming.buffer import StreamBuffer


def test_incremental_chunks() -> None:
    buf = StreamBuffer()
    c1 = StreamChunk(session_id="1", seq=1, t_ms=100, text="hello", chunk_id="1")
    state = buf.add_chunk(c1)
    assert state.full_text == "hello"
    
    c2 = StreamChunk(session_id="1", seq=2, t_ms=200, text="world", chunk_id="2")
    state = buf.add_chunk(c2)
    assert state.full_text == "hello world"

def test_duplicate_chunks() -> None:
    buf = StreamBuffer()
    c1 = StreamChunk(session_id="1", seq=1, t_ms=100, text="hello", chunk_id="1")
    buf.add_chunk(c1)
    state = buf.add_chunk(c1)
    assert state.full_text == "hello"

def test_late_chunks() -> None:
    buf = StreamBuffer()
    c1 = StreamChunk(session_id="1", seq=2, t_ms=200, text="world", chunk_id="2")
    buf.add_chunk(c1)
    
    c2 = StreamChunk(session_id="1", seq=1, t_ms=100, text="hello", chunk_id="1")
    state = buf.add_chunk(c2)
    # late chunk just gets appended to volatile tail in simple implementation
    assert state.full_text == "world hello"

def test_utterance_end() -> None:
    buf = StreamBuffer()
    c1 = StreamChunk(session_id="1", seq=1, t_ms=100, text="end", chunk_id="1", is_final=True)
    state = buf.add_chunk(c1)
    assert state.ended is True
