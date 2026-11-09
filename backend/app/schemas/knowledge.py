from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_id: str | None = None
    chunk_index: int
    content: str
    page_number: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    created_by_id: str | None = None
    version_number: int
    original_filename: str
    media_type: str
    file_size: int
    content_sha256: str
    parser_version: str
    embedding_model: str
    embedding_dimensions: int
    status: str
    summary: str | None = None
    chunk_count: int
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
    safe_error_message: str | None = None
    created_at: datetime
    ready_at: datetime | None = None
    archived_at: datetime | None = None


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_id: str
    job_type: str
    state: str
    attempt_count: int
    max_attempts: int
    error_code: str | None = None
    safe_error_message: str | None = None
    available_at: datetime
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    department_id: str | None = None
    uploaded_by_id: str | None = None
    title: str
    filename: str
    file_type: str
    file_size: int
    clearance_level: int
    is_company_wide: bool
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None
    chunk_count: int
    status: str
    current_version_id: str | None = None
    version_count: int = 0
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    version: DocumentVersionResponse
    job: IngestionJobResponse


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    versions: list[DocumentVersionResponse]
    jobs: list[IngestionJobResponse]


class ReconciliationIssue(BaseModel):
    document_id: str
    version_id: str
    code: str
    message: str
    repaired: bool = False


class ReconciliationResponse(BaseModel):
    checked_versions: int
    issues: list[ReconciliationIssue]
    expired_leases_requeued: int


class VectorSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class VectorSearchResultItem(BaseModel):
    document_id: str
    version_id: str | None = None
    title: str
    filename: str
    chunk_index: int
    content: str
    page_number: int | None = None
    clearance_level: int
    similarity_score: float
