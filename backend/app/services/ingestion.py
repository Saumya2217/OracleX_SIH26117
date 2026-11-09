from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.company import User
from app.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    OutboxEvent,
    ServiceHeartbeat,
    generate_uuid,
    utcnow,
)
from app.services.audit_service import record_audit_event
from app.services.document_processor import DocumentChunkData, DocumentProcessor
from app.services.vector_store import vector_store_service


logger = logging.getLogger("oraclex.ingestion")


class IngestionFailure(Exception):
    def __init__(self, code: str, safe_message: str):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_local_file(path: Path, version: DocumentVersion) -> None:
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(upload_root):
        raise IngestionFailure("STORAGE_PATH_INVALID", "The stored file location is invalid.")
    if not resolved.is_file():
        raise IngestionFailure("SOURCE_MISSING", "The uploaded source file is missing.")
    if resolved.stat().st_size != version.file_size:
        raise IngestionFailure("SIZE_MISMATCH", "The stored file size does not match the upload record.")
    if _file_hash(resolved) != version.content_sha256:
        raise IngestionFailure("CHECKSUM_MISMATCH", "The stored file checksum does not match the upload record.")

    extension = Path(version.original_filename).suffix.lower()
    header = resolved.read_bytes()[:16]
    if extension == ".pdf" and not header.startswith(b"%PDF-"):
        raise IngestionFailure("TYPE_MISMATCH", "The file content is not a valid PDF signature.")
    if extension == ".xlsx" and not header.startswith(b"PK"):
        raise IngestionFailure("TYPE_MISMATCH", "The file content is not a valid XLSX container.")
    if extension in {".txt", ".md", ".csv"} and b"\x00" in header:
        raise IngestionFailure("TYPE_MISMATCH", "The text file contains an unsupported binary signature.")


class IngestionService:
    @staticmethod
    def create_job_records(
        db: Session,
        *,
        document: Document,
        version: DocumentVersion,
    ) -> IngestionJob:
        job = IngestionJob(
            id=generate_uuid(),
            company_id=document.company_id,
            document_id=document.id,
            version_id=version.id,
            job_type="INGEST_DOCUMENT",
            state="QUEUED",
            max_attempts=settings.INGESTION_MAX_ATTEMPTS,
            available_at=utcnow(),
        )
        event = OutboxEvent(
            id=generate_uuid(),
            company_id=document.company_id,
            aggregate_type="DOCUMENT_VERSION",
            aggregate_id=version.id,
            event_type="DOCUMENT_VERSION_QUEUED",
            payload={"job_id": job.id, "document_id": document.id, "version_id": version.id},
            state="PENDING",
            available_at=utcnow(),
        )
        db.add_all([job, event])
        return job

    @staticmethod
    def heartbeat(db: Session, worker_id: str, details: dict[str, Any] | None = None) -> None:
        heartbeat = db.get(ServiceHeartbeat, "ingestion-worker")
        if heartbeat is None:
            heartbeat = ServiceHeartbeat(
                service_name="ingestion-worker",
                instance_id=worker_id,
                heartbeat_at=utcnow(),
                details=details or {},
            )
            db.add(heartbeat)
        else:
            heartbeat.instance_id = worker_id
            heartbeat.heartbeat_at = utcnow()
            heartbeat.details = details or {}
        db.commit()

    @staticmethod
    def dispatch_outbox(db: Session, worker_id: str, limit: int = 20) -> int:
        now = utcnow()
        query = (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.state.in_(["PENDING", "RETRYABLE"]),
                OutboxEvent.available_at <= now,
                or_(OutboxEvent.lease_expires_at.is_(None), OutboxEvent.lease_expires_at <= now),
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        events = query.all()
        for event in events:
            event.lease_owner = worker_id
            event.lease_expires_at = now + timedelta(seconds=settings.INGESTION_LEASE_SECONDS)
            event.attempt_count += 1
            event.state = "PUBLISHED"
            event.published_at = now
            event.lease_owner = None
            event.lease_expires_at = None
        db.commit()
        return len(events)

    @staticmethod
    def release_expired_leases(db: Session) -> int:
        now = utcnow()
        expired = (
            db.query(IngestionJob)
            .filter(IngestionJob.state == "PROCESSING", IngestionJob.lease_expires_at <= now)
            .all()
        )
        for job in expired:
            job.state = "FAILED" if job.attempt_count >= job.max_attempts else "RETRYABLE"
            job.error_code = "WORKER_LEASE_EXPIRED"
            job.safe_error_message = "The worker stopped before completing this job."
            job.available_at = now
            job.lease_owner = None
            job.lease_expires_at = None
            version = db.get(DocumentVersion, job.version_id)
            if version:
                version.status = "FAILED"
                version.safe_error_message = job.safe_error_message
        if expired:
            db.commit()
        return len(expired)

    @staticmethod
    def claim_next_job(db: Session, worker_id: str) -> str | None:
        IngestionService.release_expired_leases(db)
        now = utcnow()
        query = (
            db.query(IngestionJob)
            .filter(
                IngestionJob.state.in_(["QUEUED", "RETRYABLE"]),
                IngestionJob.available_at <= now,
                IngestionJob.attempt_count < IngestionJob.max_attempts,
            )
            .order_by(IngestionJob.created_at)
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        job = query.first()
        if not job:
            return None
        job.state = "PROCESSING"
        job.attempt_count += 1
        job.lease_owner = worker_id
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=settings.INGESTION_LEASE_SECONDS)
        job.started_at = job.started_at or now
        job.error_code = None
        job.safe_error_message = None
        version = db.get(DocumentVersion, job.version_id)
        document = db.get(Document, job.document_id)
        if version:
            version.status = "SCANNING"
            version.safe_error_message = None
        if document and not document.current_version_id:
            document.status = "SCANNING"
        db.commit()
        return job.id

    @staticmethod
    def _set_stage(db: Session, job: IngestionJob, version: DocumentVersion, document: Document, stage: str) -> None:
        now = utcnow()
        version.status = stage
        if not document.current_version_id or document.current_version_id == version.id:
            document.status = stage
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=settings.INGESTION_LEASE_SECONDS)
        db.commit()

    @staticmethod
    def process_job(db: Session, job_id: str, worker_id: str) -> bool:
        job = db.get(IngestionJob, job_id)
        if not job or job.state != "PROCESSING" or job.lease_owner != worker_id:
            return False
        version = db.get(DocumentVersion, job.version_id)
        document = db.get(Document, job.document_id)
        if not version or not document:
            IngestionService._fail_job(db, job_id, "RECORD_MISSING", "The document ingestion record is incomplete.")
            return False

        try:
            source = Path(version.storage_key)
            validate_local_file(source, version)

            if source.parent.name == "quarantine":
                original_dir = source.parent.parent / "original"
                original_dir.mkdir(parents=True, exist_ok=True)
                approved_source = original_dir / source.name
                source.replace(approved_source)
                try:
                    source.parent.rmdir()
                except OSError:
                    pass
                source = approved_source
                version.storage_key = str(source)
                db.commit()

            IngestionService._set_stage(db, job, version, document, "PARSING")
            extension = Path(version.original_filename).suffix.lstrip(".").lower()
            try:
                summary, raw_chunks = DocumentProcessor.process_file(str(source), extension)
            except (ValueError, OSError, UnicodeError) as exc:
                raise IngestionFailure("PARSER_REJECTED", str(exc)) from exc
            if not raw_chunks:
                raise IngestionFailure("NO_SEARCHABLE_CONTENT", "No searchable content could be extracted from this file.")

            IngestionService._set_stage(db, job, version, document, "INDEXING")
            vector_store_service.delete_version_chunks(version.id)
            db.query(DocumentChunk).filter(DocumentChunk.version_id == version.id).delete()
            for index, chunk in enumerate(raw_chunks):
                metadata = dict(chunk.metadata)
                metadata["version_id"] = version.id
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        version_id=version.id,
                        chunk_index=index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        metadata_json=metadata,
                        vector_id=f"{version.id}_chunk_{index}",
                    )
                )
            db.flush()
            vector_store_service.index_chunks(
                document_id=document.id,
                version_id=version.id,
                company_id=document.company_id,
                clearance_level=document.clearance_level,
                department_id=document.department_id,
                is_company_wide=document.is_company_wide,
                chunks=raw_chunks,
                doc_title=document.title,
            )
            indexed_count = vector_store_service.version_chunk_count(version.id)
            if indexed_count != len(raw_chunks):
                raise IngestionFailure(
                    "INDEX_VERIFICATION_FAILED",
                    "The search index did not contain the expected number of document sections.",
                )

            previous_version_id = document.current_version_id
            if previous_version_id and previous_version_id != version.id:
                previous = db.get(DocumentVersion, previous_version_id)
                if previous and previous.status == "READY":
                    previous.status = "SUPERSEDED"
                vector_store_service.delete_version_chunks(previous_version_id)

            now = utcnow()
            version.status = "READY"
            version.summary = summary
            version.chunk_count = len(raw_chunks)
            version.ready_at = now
            version.safe_error_message = None
            version.extraction_metadata = IngestionService._coverage_metadata(extension, raw_chunks)
            version.embedding_model = vector_store_service.EMBEDDING_MODEL
            version.embedding_dimensions = vector_store_service.EMBEDDING_DIMENSIONS
            document.current_version_id = version.id
            document.version_count = max(document.version_count or 0, version.version_number)
            document.filename = version.original_filename
            document.file_type = extension
            document.file_path = version.storage_key
            document.file_size = version.file_size
            document.content_sha256 = version.content_sha256
            document.summary = summary
            document.chunk_count = len(raw_chunks)
            document.status = "INDEXED"
            document.archived_at = None
            job.state = "SUCCEEDED"
            job.completed_at = now
            job.heartbeat_at = now
            job.lease_owner = None
            job.lease_expires_at = None
            db.commit()

            creator = db.get(User, version.created_by_id) if version.created_by_id else None
            try:
                record_audit_event(
                    db=db,
                    company_id=document.company_id,
                    action="DOC_VERSION_READY",
                    resource_type="DOCUMENT_VERSION",
                    resource_id=version.id,
                    user=creator,
                    details={
                        "document_id": document.id,
                        "version": version.version_number,
                        "chunks": version.chunk_count,
                    },
                )
            except Exception:
                logger.exception("Ingestion completed but audit recording failed for version %s", version.id)
            return True
        except IngestionFailure as exc:
            db.rollback()
            IngestionService._fail_job(db, job_id, exc.code, exc.safe_message)
        except Exception:
            logger.exception("Unexpected ingestion failure for job %s", job_id)
            db.rollback()
            IngestionService._fail_job(
                db,
                job_id,
                "PROCESSING_ERROR",
                "Document processing failed. Review the file and retry the job.",
            )
        return False

    @staticmethod
    def _coverage_metadata(extension: str, chunks: list[DocumentChunkData]) -> dict[str, Any]:
        pages = sorted({chunk.page_number for chunk in chunks if chunk.page_number})
        sheets = sorted({str(chunk.metadata.get("sheet")) for chunk in chunks if chunk.metadata.get("sheet")})
        row_ranges = [chunk.metadata.get("rows") for chunk in chunks if chunk.metadata.get("rows")]
        return {
            "format": extension,
            "complete": True,
            "chunk_count": len(chunks),
            "pages": pages,
            "sheets": sheets,
            "row_ranges": row_ranges,
        }

    @staticmethod
    def _fail_job(db: Session, job_id: str, code: str, safe_message: str) -> None:
        job = db.get(IngestionJob, job_id)
        if not job:
            return
        version = db.get(DocumentVersion, job.version_id)
        document = db.get(Document, job.document_id)
        try:
            vector_store_service.delete_version_chunks(job.version_id)
        except Exception:
            logger.exception("Could not clean vector entries for failed version %s", job.version_id)
        now = utcnow()
        retryable = job.attempt_count < job.max_attempts
        job.state = "RETRYABLE" if retryable else "FAILED"
        job.error_code = code
        job.safe_error_message = safe_message
        job.available_at = now + timedelta(
            seconds=settings.INGESTION_RETRY_BASE_SECONDS * (2 ** max(job.attempt_count - 1, 0))
        )
        job.lease_owner = None
        job.lease_expires_at = None
        job.heartbeat_at = now
        if not retryable:
            job.completed_at = now
        if version:
            version.status = "FAILED"
            version.safe_error_message = safe_message
        if document and not document.current_version_id:
            document.status = "FAILED"
        db.commit()

    @staticmethod
    def retry_job(db: Session, job: IngestionJob) -> None:
        if job.state not in {"FAILED", "RETRYABLE"}:
            raise ValueError("Only failed or retryable jobs can be queued again.")
        job.state = "QUEUED"
        job.attempt_count = 0
        job.available_at = utcnow()
        job.error_code = None
        job.safe_error_message = None
        job.completed_at = None
        version = db.get(DocumentVersion, job.version_id)
        document = db.get(Document, job.document_id)
        if version:
            version.status = "QUEUED"
            version.safe_error_message = None
        if document and not document.current_version_id:
            document.status = "QUEUED"
        db.commit()

    @staticmethod
    def archive_document(db: Session, document: Document) -> None:
        now = utcnow()
        if document.current_version_id:
            vector_store_service.delete_version_chunks(document.current_version_id)
            version = db.get(DocumentVersion, document.current_version_id)
            if version:
                version.status = "ARCHIVED"
                version.archived_at = now
        document.status = "ARCHIVED"
        document.archived_at = now
        db.commit()

    @staticmethod
    def restore_document(db: Session, document: Document) -> None:
        if not document.current_version_id:
            raise IngestionFailure("VERSION_MISSING", "The document has no version to restore.")
        version = db.get(DocumentVersion, document.current_version_id)
        if not version:
            raise IngestionFailure("VERSION_MISSING", "The document version record is missing.")
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.version_id == version.id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if not chunks:
            raise IngestionFailure("CHUNKS_MISSING", "The archived document has no extracted sections to restore.")
        data = [
            DocumentChunkData(chunk.content, chunk.page_number or 1, dict(chunk.metadata_json or {}))
            for chunk in chunks
        ]
        vector_store_service.delete_version_chunks(version.id)
        vector_store_service.index_chunks(
            document_id=document.id,
            version_id=version.id,
            company_id=document.company_id,
            clearance_level=document.clearance_level,
            department_id=document.department_id,
            is_company_wide=document.is_company_wide,
            chunks=data,
            doc_title=document.title,
        )
        if vector_store_service.version_chunk_count(version.id) != len(chunks):
            raise IngestionFailure("INDEX_VERIFICATION_FAILED", "The restored index could not be verified.")
        version.status = "READY"
        version.archived_at = None
        document.status = "INDEXED"
        document.archived_at = None
        db.commit()

    @staticmethod
    def reconcile(db: Session, repair: bool = False) -> dict[str, Any]:
        expired = IngestionService.release_expired_leases(db)
        issues: list[dict[str, Any]] = []
        versions = db.query(DocumentVersion).all()
        for version in versions:
            document = db.get(Document, version.document_id)
            if not document:
                continue
            active = document.current_version_id == version.id and document.status == "INDEXED"
            expected_chunks = db.query(DocumentChunk).filter(DocumentChunk.version_id == version.id).count()
            try:
                indexed_chunks = vector_store_service.version_chunk_count(version.id)
            except Exception:
                indexed_chunks = -1

            if active:
                source = Path(version.storage_key)
                if not source.is_file():
                    issues.append(IngestionService._issue(document, version, "SOURCE_MISSING", "Original file is missing.", False))
                    if repair:
                        vector_store_service.delete_version_chunks(version.id)
                        version.status = "FAILED"
                        version.safe_error_message = "Original file is missing."
                        document.status = "FAILED"
                        issues[-1]["repaired"] = True
                    continue
                if _file_hash(source) != version.content_sha256:
                    issues.append(IngestionService._issue(document, version, "CHECKSUM_MISMATCH", "Original checksum differs.", False))
                    if repair:
                        vector_store_service.delete_version_chunks(version.id)
                        version.status = "FAILED"
                        version.safe_error_message = "Original checksum differs."
                        document.status = "FAILED"
                        issues[-1]["repaired"] = True
                    continue
                if indexed_chunks != expected_chunks:
                    issues.append(
                        IngestionService._issue(
                            document,
                            version,
                            "INDEX_COUNT_MISMATCH",
                            f"Expected {expected_chunks} indexed sections; found {indexed_chunks}.",
                            False,
                        )
                    )
                    if repair and expected_chunks:
                        chunks = (
                            db.query(DocumentChunk)
                            .filter(DocumentChunk.version_id == version.id)
                            .order_by(DocumentChunk.chunk_index)
                            .all()
                        )
                        data = [
                            DocumentChunkData(item.content, item.page_number or 1, dict(item.metadata_json or {}))
                            for item in chunks
                        ]
                        vector_store_service.delete_version_chunks(version.id)
                        vector_store_service.index_chunks(
                            document_id=document.id,
                            version_id=version.id,
                            company_id=document.company_id,
                            clearance_level=document.clearance_level,
                            department_id=document.department_id,
                            is_company_wide=document.is_company_wide,
                            chunks=data,
                            doc_title=document.title,
                        )
                        issues[-1]["repaired"] = vector_store_service.version_chunk_count(version.id) == expected_chunks
            elif indexed_chunks > 0:
                issues.append(
                    IngestionService._issue(
                        document,
                        version,
                        "STALE_INDEX",
                        "A non-current version is still present in the search index.",
                        False,
                    )
                )
                if repair:
                    vector_store_service.delete_version_chunks(version.id)
                    issues[-1]["repaired"] = True
        if repair:
            db.commit()
        return {"checked_versions": len(versions), "issues": issues, "expired_leases_requeued": expired}

    @staticmethod
    def _issue(document: Document, version: DocumentVersion, code: str, message: str, repaired: bool) -> dict[str, Any]:
        return {
            "document_id": document.id,
            "version_id": version.id,
            "code": code,
            "message": message,
            "repaired": repaired,
        }
