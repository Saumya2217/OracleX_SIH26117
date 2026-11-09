from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.core.permissions import PermissionScope, user_can_access_document, user_has_permission
from app.database import get_db
from app.models.company import Department, User
from app.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    generate_uuid,
    utcnow,
)
from app.schemas.knowledge import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentVersionResponse,
    IngestionJobResponse,
    ReconciliationResponse,
    VectorSearchRequest,
    VectorSearchResultItem,
)
from app.services.audit_service import record_audit_event
from app.services.ingestion import IngestionFailure, IngestionService
from app.services.vector_store import vector_store_service


router = APIRouter(prefix="/knowledge", tags=["Company knowledge"])


def _can_manage_document(user: User, document: Document) -> bool:
    return bool(user.is_admin or document.uploaded_by_id == user.id)


def _require_document_access(user: User, document: Document) -> None:
    if not user_can_access_document(
        user,
        document.clearance_level,
        document.department_id,
        document.is_company_wide,
    ):
        raise HTTPException(status_code=403, detail="Clearance Violation: you do not have access to this document.")


def _validate_upload_scope(
    db: Session,
    user: User,
    clearance_level: int,
    department_id: str | None,
    is_company_wide: bool,
) -> str | None:
    if not user_has_permission(user, PermissionScope.DOC_UPLOAD):
        raise HTTPException(status_code=403, detail="Document upload permission required.")
    if clearance_level not in {1, 2, 3, 4}:
        raise HTTPException(status_code=422, detail="Clearance level must be between 1 and 4.")
    if (user.clearance_level or 1) < clearance_level and not user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot upload a document above your own clearance level.")
    if is_company_wide:
        return None
    if not department_id:
        raise HTTPException(status_code=422, detail="A department is required for a department-scoped document.")
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.company_id == user.company_id,
    ).first()
    if not department:
        raise HTTPException(status_code=422, detail="Department is not part of this company.")
    return department_id


async def _stage_upload(
    file: UploadFile,
    *,
    company_id: str,
    document_id: str,
    version_id: str,
) -> tuple[str, str, int, str, str]:
    original_filename = Path(file.filename or "upload").name
    extension = Path(original_filename).suffix.lstrip(".").lower()
    if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed extensions: {allowed}.")

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    quarantine_dir = (
        upload_root / company_id / document_id / "versions" / version_id / "quarantine"
    ).resolve()
    if not quarantine_dir.is_relative_to(upload_root):
        raise HTTPException(status_code=400, detail="Invalid storage location.")
    quarantine_dir.mkdir(parents=True, exist_ok=False)
    stored_path = quarantine_dir / f"source.{extension}"

    file_size = 0
    digest = hashlib.sha256()
    try:
        with stored_path.open("xb") as handle:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
                digest.update(chunk)
                handle.write(chunk)
    except HTTPException:
        shutil.rmtree(quarantine_dir.parent, ignore_errors=True)
        raise
    except OSError as exc:
        shutil.rmtree(quarantine_dir.parent, ignore_errors=True)
        raise HTTPException(status_code=503, detail="The upload storage is unavailable.") from exc
    finally:
        await file.close()

    if file_size == 0:
        shutil.rmtree(quarantine_dir.parent, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Empty files are not supported.")
    media_type = file.content_type or f"application/{extension}"
    return original_filename, extension, file_size, digest.hexdigest(), str(stored_path)


def _upload_response(document: Document, version: DocumentVersion, job: IngestionJob) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(document),
        version=DocumentVersionResponse.model_validate(version),
        job=IngestionJobResponse.model_validate(job),
    )


def _run_inline_test_job(db: Session, job: IngestionJob) -> None:
    if not settings.INGESTION_INLINE_FOR_TESTS:
        return
    worker_id = "inline-test-worker"
    IngestionService.dispatch_outbox(db, worker_id)
    claimed = IngestionService.claim_next_job(db, worker_id)
    if claimed:
        IngestionService.process_job(db, claimed, worker_id)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document).filter(Document.company_id == current_user.company_id)
    if not include_archived:
        query = query.filter(Document.status != "ARCHIVED")
    documents = query.order_by(Document.updated_at.desc()).all()
    return [
        DocumentResponse.model_validate(document)
        for document in documents
        if user_can_access_document(
            current_user,
            document.clearance_level,
            document.department_id,
            document.is_company_wide,
        )
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    _require_document_access(current_user, document)
    return DocumentResponse.model_validate(document)


@router.get("/documents/{document_id}/detail", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    _require_document_access(current_user, document)
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
        .all()
    )
    version_ids = [version.id for version in versions]
    jobs = (
        db.query(IngestionJob)
        .filter(IngestionJob.version_id.in_(version_ids))
        .order_by(IngestionJob.created_at.desc())
        .all()
        if version_ids
        else []
    )
    return DocumentDetailResponse(
        document=DocumentResponse.model_validate(document),
        versions=[DocumentVersionResponse.model_validate(version) for version in versions],
        jobs=[IngestionJobResponse.model_validate(job) for job in jobs],
    )


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionResponse])
def list_document_versions(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = get_document_detail(document_id, db, current_user)
    return detail.versions


@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def get_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
        Document.status == "INDEXED",
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Ready document not found.")
    _require_document_access(current_user, document)
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.version_id == document.current_version_id,
        )
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    return [DocumentChunkResponse.model_validate(chunk) for chunk in chunks]


@router.get(
    "/documents/{document_id}/versions/{version_id}/chunks",
    response_model=list[DocumentChunkResponse],
)
def get_version_chunks(
    document_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    _require_document_access(current_user, document)
    if not _can_manage_document(current_user, document) and (
        version_id != document.current_version_id or document.status != "INDEXED"
    ):
        raise HTTPException(status_code=403, detail="Only document managers can inspect historical versions.")
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id,
        DocumentVersion.document_id == document.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.version_id == version.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    return [DocumentChunkResponse.model_validate(chunk) for chunk in chunks]


@router.get("/documents/{document_id}/versions/{version_id}/source")
def download_version_source(
    document_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    _require_document_access(current_user, document)
    if not _can_manage_document(current_user, document) and (
        version_id != document.current_version_id or document.status != "INDEXED"
    ):
        raise HTTPException(status_code=403, detail="Only document managers can download historical versions.")
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id,
        DocumentVersion.document_id == document.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    source = Path(version.storage_key).resolve()
    if not source.is_relative_to(upload_root):
        raise HTTPException(status_code=500, detail="The version storage path is invalid.")
    if not source.is_file():
        raise HTTPException(status_code=410, detail="The retained source file is unavailable.")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != version.content_sha256:
        raise HTTPException(status_code=409, detail="The retained source failed its integrity check.")
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="DOC_VERSION_SOURCE_READ",
        resource_type="DOCUMENT_VERSION",
        resource_id=version.id,
        user=current_user,
        details={"document_id": document.id, "version": version.version_number},
    )
    return FileResponse(
        source,
        media_type=version.media_type,
        filename=version.original_filename,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(...)],
    clearance_level: Annotated[int, Form()] = 1,
    department_id: Annotated[str | None, Form()] = None,
    is_company_wide: Annotated[bool, Form()] = False,
    tags: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department_id = _validate_upload_scope(
        db,
        current_user,
        clearance_level,
        department_id,
        is_company_wide,
    )
    if not title.strip():
        raise HTTPException(status_code=422, detail="Document title is required.")
    document_id = generate_uuid()
    version_id = generate_uuid()
    original, extension, file_size, digest, storage_key = await _stage_upload(
        file,
        company_id=current_user.company_id,
        document_id=document_id,
        version_id=version_id,
    )
    duplicate = (
        db.query(DocumentVersion)
        .join(Document, DocumentVersion.document_id == Document.id)
        .filter(
            Document.company_id == current_user.company_id,
            DocumentVersion.content_sha256 == digest,
            DocumentVersion.status.notin_(["ARCHIVED"]),
        )
        .first()
    )
    if duplicate:
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=409, detail=f"This content is already stored in document '{duplicate.document_id}'.")

    document = Document(
        id=document_id,
        company_id=current_user.company_id,
        department_id=department_id,
        uploaded_by_id=current_user.id,
        title=title.strip(),
        filename=original,
        file_type=extension,
        file_path=storage_key,
        file_size=file_size,
        content_sha256=digest,
        clearance_level=clearance_level,
        is_company_wide=is_company_wide,
        tags=[item.strip() for item in tags.split(",") if item.strip()],
        chunk_count=0,
        status="QUEUED",
        version_count=1,
    )
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        created_by_id=current_user.id,
        version_number=1,
        original_filename=original,
        media_type=file.content_type or f"application/{extension}",
        file_size=file_size,
        content_sha256=digest,
        storage_key=storage_key,
        parser_version="document-processor-v2",
        embedding_model=vector_store_service.EMBEDDING_MODEL,
        embedding_dimensions=vector_store_service.EMBEDDING_DIMENSIONS,
        status="QUEUED",
        extraction_metadata={},
    )
    db.add_all([document, version])
    db.flush()
    job = IngestionService.create_job_records(db, document=document, version=version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=409, detail="The document or version already exists.") from exc
    except Exception as exc:
        db.rollback()
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=503, detail="The document could not be queued for processing.") from exc

    _run_inline_test_job(db, job)
    db.refresh(document)
    db.refresh(version)
    db.refresh(job)
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="DOC_VERSION_QUEUED",
        resource_type="DOCUMENT_VERSION",
        resource_id=version.id,
        user=current_user,
        details={"document_id": document.id, "version": 1, "filename": original},
    )
    return _upload_response(document, version, job)


@router.post(
    "/documents/{document_id}/versions",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_replacement_version(
    document_id: str,
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not _can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="You do not have permission to replace this document.")
    if document.status == "ARCHIVED":
        raise HTTPException(status_code=409, detail="Restore the document before uploading a replacement.")

    version_id = generate_uuid()
    original, extension, file_size, digest, storage_key = await _stage_upload(
        file,
        company_id=current_user.company_id,
        document_id=document.id,
        version_id=version_id,
    )
    duplicate = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id,
        DocumentVersion.content_sha256 == digest,
    ).first()
    if duplicate:
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=409, detail=f"This content already exists as version {duplicate.version_number}.")
    version_number = (document.version_count or 0) + 1
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        created_by_id=current_user.id,
        version_number=version_number,
        original_filename=original,
        media_type=file.content_type or f"application/{extension}",
        file_size=file_size,
        content_sha256=digest,
        storage_key=storage_key,
        parser_version="document-processor-v2",
        embedding_model=vector_store_service.EMBEDDING_MODEL,
        embedding_dimensions=vector_store_service.EMBEDDING_DIMENSIONS,
        status="QUEUED",
        extraction_metadata={},
    )
    document.version_count = version_number
    db.add(version)
    db.flush()
    job = IngestionService.create_job_records(db, document=document, version=version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=409, detail="A concurrent replacement created this version first.") from exc
    except Exception as exc:
        db.rollback()
        shutil.rmtree(Path(storage_key).parent.parent, ignore_errors=True)
        raise HTTPException(status_code=503, detail="The replacement could not be queued for processing.") from exc
    _run_inline_test_job(db, job)
    db.refresh(document)
    db.refresh(version)
    db.refresh(job)
    return _upload_response(document, version, job)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(IngestionJob).filter(
        IngestionJob.id == job_id,
        IngestionJob.company_id == current_user.company_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    document = db.get(Document, job.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    _require_document_access(current_user, document)
    return IngestionJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=IngestionJobResponse)
def retry_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(IngestionJob).filter(
        IngestionJob.id == job_id,
        IngestionJob.company_id == current_user.company_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    document = db.get(Document, job.document_id)
    if not document or not _can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="You do not have permission to retry this job.")
    try:
        IngestionService.retry_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(job)
    return IngestionJobResponse.model_validate(job)


@router.post("/documents/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not _can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="You do not have permission to archive this document.")
    if document.status == "ARCHIVED":
        return DocumentResponse.model_validate(document)
    try:
        IngestionService.archive_document(db, document)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="The document could not be removed from search.") from exc
    return DocumentResponse.model_validate(document)


@router.post("/documents/{document_id}/restore", response_model=DocumentResponse)
def restore_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not _can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="You do not have permission to restore this document.")
    try:
        IngestionService.restore_document(db, document)
    except IngestionFailure as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.safe_message) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="The document search index could not be restored.") from exc
    return DocumentResponse.model_validate(document)


@router.delete("/documents/{document_id}")
def permanently_delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == current_user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permanent deletion requires administrator authority.")
    try:
        vector_store_service.delete_document_chunks(document.id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Permanent deletion is blocked because the search index is unavailable.") from exc

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    document_root = (upload_root / document.company_id / document.id).resolve()
    if not document_root.is_relative_to(upload_root):
        raise HTTPException(status_code=500, detail="The document storage path is invalid.")
    try:
        # Migrated pre-version files may not live below the generated document
        # directory, so remove every recorded source after containment checks.
        for version in document.versions:
            source = Path(version.storage_key).resolve()
            if not source.is_relative_to(upload_root):
                raise HTTPException(status_code=500, detail="A document version storage path is invalid.")
            if source.is_file():
                source.unlink()
        if document_root.exists():
            shutil.rmtree(document_root)
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Permanent deletion is blocked because original files could not be removed.") from exc

    title = document.title
    db.delete(document)
    db.commit()
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="DOC_PURGE",
        resource_type="DOCUMENT",
        resource_id=document_id,
        user=current_user,
        details={"title": title},
    )
    return {"status": "success", "deleted_id": document_id, "title": title}


@router.post("/admin/reconcile", response_model=ReconciliationResponse)
def reconcile_ingestion(
    repair: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator authority required.")
    result = IngestionService.reconcile(db, repair=repair)
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="INGESTION_RECONCILE",
        resource_type="SYSTEM",
        user=current_user,
        details={"repair": repair, "issues": len(result["issues"])},
    )
    return ReconciliationResponse(**result)


@router.post("/search", response_model=list[VectorSearchResultItem])
def search_knowledge(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = vector_store_service.search_authorized_chunks(
        company_id=current_user.company_id,
        user_clearance=current_user.clearance_level or 1,
        user_department_id=current_user.department_id,
        query=request.query,
        n_results=request.limit,
    )
    checked_results = []
    for result in results:
        document = db.query(Document).filter(
            Document.id == result.get("document_id"),
            Document.company_id == current_user.company_id,
            Document.status == "INDEXED",
        ).first()
        if (
            document
            and result.get("version_id") == document.current_version_id
            and user_can_access_document(
                current_user,
                document.clearance_level,
                document.department_id,
                document.is_company_wide,
            )
        ):
            checked_results.append(result)

    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="KNOWLEDGE_SEARCH",
        resource_type="SEARCH",
        user=current_user,
        details={"query": request.query, "results_found": len(checked_results)},
    )
    return [VectorSearchResultItem(**item, filename=item.get("title", "Document")) for item in checked_results]
