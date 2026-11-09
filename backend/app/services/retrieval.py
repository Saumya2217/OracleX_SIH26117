from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.permissions import user_can_access_document
from app.models.company import User
from app.models.knowledge import Document, DocumentChunk
from app.services.vector_store import vector_store_service


RetrievalMode = Literal["lexical", "vector", "hybrid"]

STOP_WORDS = {
    "a", "about", "an", "and", "any", "are", "by", "can", "company", "corporate",
    "document", "does", "employee", "employees", "for", "from", "guideline", "guidelines",
    "have", "how", "i", "in", "information", "internal", "is", "me", "of", "office",
    "official", "on", "our", "please", "policy", "provide", "provided", "rule", "rules", "show", "staff", "tell",
    "that", "the", "their", "this", "to", "us", "was", "we", "were", "what", "when",
    "where", "which", "who", "with", "you",
}

ALIASES = {
    "leave": {"vacation", "timeoff", "absence"},
    "vacation": {"leave", "timeoff"},
    "sick": {"medical"},
    "launch": {"release"},
    "release": {"launch"},
    "sla": {"service", "incident", "response"},
    "service": {"sla"},
    "budget": {"allocation", "expenditure", "spending"},
    "spending": {"budget", "expenditure"},
    "tolerance": {"variance", "limit"},
    "response": {"incident", "sla"},
}


def _normalize(token: str) -> str:
    token = token.lower()
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> set[str]:
    tokens = {_normalize(item) for item in re.findall(r"\d+(?:\.\d+)?|[a-zA-Z]+", text.lower())}
    return {token for token in tokens if token not in STOP_WORDS and len(token) > 1}


def expanded_query_tokens(query: str) -> set[str]:
    base = tokenize(query)
    expanded = set(base)
    for token in base:
        expanded.update(ALIASES.get(token, set()))
    return expanded


def source_location(chunk: DocumentChunk) -> dict[str, Any]:
    metadata = dict(chunk.metadata_json or {})
    sheet = metadata.get("sheet")
    rows = metadata.get("rows")
    if sheet and rows:
        return {"source_type": "table", "location_label": f"Sheet {sheet}, rows {rows}", "sheet_name": str(sheet), "row_range": str(rows)}
    if sheet:
        return {"source_type": "table", "location_label": f"Sheet {sheet}", "sheet_name": str(sheet)}
    if rows:
        return {"source_type": "table", "location_label": f"Rows {rows}", "row_range": str(rows)}
    file_type = str(metadata.get("file_type") or "").lower()
    if file_type == "pdf" or str(metadata.get("filename", "")).lower().endswith(".pdf"):
        page = chunk.page_number or metadata.get("page") or 1
        return {"source_type": "page", "location_label": f"Page {page}", "page_number": int(page)}
    return {"source_type": "section", "location_label": f"Section {chunk.chunk_index + 1}", "section_index": chunk.chunk_index + 1}


class RetrievalService:
    @staticmethod
    def _authorized_rows(db: Session, user: User) -> list[tuple[DocumentChunk, Document]]:
        rows = (
            db.query(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                Document.company_id == user.company_id,
                Document.status == "INDEXED",
                DocumentChunk.version_id == Document.current_version_id,
            )
            .limit(5000)
            .all()
        )
        return [
            (chunk, document)
            for chunk, document in rows
            if user_can_access_document(
                user,
                document.clearance_level,
                document.department_id,
                document.is_company_wide,
            )
        ]

    @staticmethod
    def retrieve(
        db: Session,
        user: User,
        query: str,
        *,
        limit: int = 5,
        mode: RetrievalMode = "hybrid",
    ) -> list[dict[str, Any]]:
        query_tokens = expanded_query_tokens(query)
        if not query_tokens:
            return []
        rows = RetrievalService._authorized_rows(db, user)
        by_key = {(chunk.version_id, chunk.chunk_index): (chunk, document) for chunk, document in rows}

        lexical_rank: dict[tuple[str | None, int], int] = {}
        lexical_scores: dict[tuple[str | None, int], float] = {}
        lexical_matches: dict[tuple[str | None, int], list[str]] = {}
        scored: list[tuple[float, tuple[str | None, int]]] = []
        query_phrase = " ".join(_normalize(item) for item in re.findall(r"[a-zA-Z0-9.]+", query.lower()) if _normalize(item) not in STOP_WORDS)
        for chunk, document in rows:
            key = (chunk.version_id, chunk.chunk_index)
            content_tokens = tokenize(chunk.content)
            title_tokens = tokenize(document.title)
            tag_tokens = tokenize(" ".join(document.tags or []))
            matches = sorted(query_tokens.intersection(content_tokens | title_tokens | tag_tokens))
            if not matches:
                continue
            numeric_matches = {item for item in matches if item[0].isdigit()}
            score = (
                len(query_tokens.intersection(content_tokens))
                + 3 * len(query_tokens.intersection(title_tokens))
                + 2 * len(query_tokens.intersection(tag_tokens))
                + 2 * len(numeric_matches)
            )
            if query_phrase and query_phrase in f"{document.title} {chunk.content}".lower():
                score += 5
            scored.append((float(score), key))
            lexical_scores[key] = float(score)
            lexical_matches[key] = matches
        scored.sort(key=lambda item: (-item[0], item[1][1]))
        # A one-word overlap can be valid when the term is distinctive, but it
        # should not trail a much stronger match into the evidence set. Keep
        # candidates within 60% of the best lexical score for this query.
        best_lexical_score = scored[0][0] if scored else 0.0
        relevance_floor = max(1.0, best_lexical_score * 0.6)
        relevant_scored = [item for item in scored if item[0] >= relevance_floor]
        lexical_rank = {key: rank for rank, (_, key) in enumerate(relevant_scored, 1)}

        vector_rank: dict[tuple[str | None, int], int] = {}
        vector_similarity: dict[tuple[str | None, int], float] = {}
        if mode in {"vector", "hybrid"}:
            candidates = vector_store_service.search_authorized_chunks(
                company_id=user.company_id,
                user_clearance=user.clearance_level or 1,
                user_department_id=user.department_id,
                query=query,
                n_results=min(max(limit * 4, 12), 30),
            )
            for rank, candidate in enumerate(candidates, 1):
                key = (candidate.get("version_id"), int(candidate.get("chunk_index", 0)))
                if key in by_key and key not in vector_rank:
                    vector_rank[key] = rank
                    vector_similarity[key] = float(candidate.get("similarity_score", 0.0))

        if mode == "lexical":
            ordered_keys = [key for _, key in relevant_scored]
        elif mode == "vector":
            ordered_keys = [key for key, _rank in sorted(vector_rank.items(), key=lambda item: item[1])]
        else:
            # Reciprocal-rank fusion uses vector ranking to order lexically
            # relevant evidence. Requiring lexical overlap prevents unrelated
            # nearest neighbours from becoming company evidence.
            fused: dict[tuple[str | None, int], float] = defaultdict(float)
            for key, rank in lexical_rank.items():
                fused[key] += 1 / (60 + rank)
            for key, rank in vector_rank.items():
                if key in lexical_rank:
                    fused[key] += 1 / (60 + rank)
            ordered_keys = sorted(fused, key=lambda key: (-fused[key], -lexical_scores.get(key, 0), key[1]))

        results: list[dict[str, Any]] = []
        for key in ordered_keys[:limit]:
            chunk, document = by_key[key]
            location = source_location(chunk)
            results.append({
                "document_id": document.id,
                "version_id": chunk.version_id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "title": document.title,
                "filename": document.filename,
                "content": chunk.content,
                "clearance_level": document.clearance_level,
                "lexical_score": lexical_scores.get(key, 0.0),
                "similarity_score": vector_similarity.get(key, 0.0),
                "matched_terms": lexical_matches.get(key, []),
                **location,
            })
        return results
