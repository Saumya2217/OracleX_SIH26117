from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import AgentCitation


class PersistedAgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: Literal["RUNNING", "COMPLETED", "FAILED"]
    evidence_status: Optional[str] = None
    generation_mode: Optional[str] = None
    model_id: Optional[str] = None
    prompt_version: str
    retrieval_mode: Optional[str] = None
    requires_review: bool = False
    business_request_id: Optional[str] = None
    safe_error_message: Optional[str] = None
    citations: list[AgentCitation] = Field(default_factory=list)


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["USER", "ASSISTANT"]
    content: str
    sequence: int
    created_at: datetime
    run: Optional[PersistedAgentRunResponse] = None


class ConversationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    classification_level: int
    status: Literal["ACTIVE", "ARCHIVED"]
    retention_until: Optional[datetime] = None
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: list[ConversationMessageResponse]


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    status: Optional[Literal["ACTIVE", "ARCHIVED"]] = None
