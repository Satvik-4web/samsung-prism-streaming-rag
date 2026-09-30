
from pydantic import BaseModel, Field


class Constraint(BaseModel):
    key: str
    value: str

class Intent(BaseModel):
    intent_id: str
    parent_request_id: str
    description: str
    constraints: list[Constraint] = Field(default_factory=list)

class RetrievalQuery(BaseModel):
    intent_id: str
    parent_request_id: str
    query_text: str
    constraints: list[Constraint] = Field(default_factory=list)
    top_k: int = 5
    priority: int = 1
    retrieval_strategy: str = "hybrid"
