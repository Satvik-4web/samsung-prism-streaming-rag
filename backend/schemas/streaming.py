
from pydantic import BaseModel


class StreamChunk(BaseModel):
    session_id: str
    seq: int
    t_ms: int
    text: str
    is_final: bool = False
    chunk_id: str

class UtteranceState(BaseModel):
    session_id: str
    committed_text: str = ""
    volatile_tail: str = ""
    last_seq: int = -1
    ended: bool = False
    
    @property
    def full_text(self) -> str:
        return (self.committed_text + " " + self.volatile_tail).strip()
