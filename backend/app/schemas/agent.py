from typing import Literal, Optional
from pydantic import BaseModel, Field

class AgentHealthResponse(BaseModel):
    status: Literal["online", "model_missing", "simulated", "unavailable"]
    engine: str
    provider: str
    model: Optional[str]
    active_model: Optional[str]
    available_models: list[str]
    mode: str
    is_live_inference: bool
    sovereign_mode: Optional[str] = None
    message: Optional[str] = None

class AgentCitation(BaseModel):
    document_id: str
    version_id: str
    chunk_id: str
    chunk_index: int
    title: str
    filename: str
    page_number: Optional[int] = None
    section_index: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    source_type: Literal["page", "section", "table"]
    location_label: str
    excerpt: str
    source_path: str

class AgentQueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    image_base64: Optional[str] = None

class AgentQueryResponse(BaseModel):
    answer: str
    conversation_id: str
    evidence_status: Literal["SUPPORTED", "INSUFFICIENT_EVIDENCE", "ACCESS_DENIED", "UNSUPPORTED_INPUT"]
    generation_mode: Literal["LOCAL_MODEL", "EXTRACTIVE", "DEMO_SIMULATION", "NONE"]
    model_id: Optional[str] = None
    retrieval_mode: Literal["hybrid", "none"] = "none"
    citations: list[AgentCitation] = Field(default_factory=list)
    requires_review: bool = False
    request_id: Optional[str] = None
    execution_status: str = "COMPLETED"

class FeedbackSubmitRequest(BaseModel):
    query_text: str
    agent_response: str
    rating: int  # 1 or -1
    correction: Optional[str] = None
    category: str = "ACCURACY"

class FeedbackSubmitResponse(BaseModel):
    status: Literal["recorded"]
    feedback_id: str
