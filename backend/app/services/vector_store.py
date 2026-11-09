import math
import re
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from app.config import settings

import hashlib


class VectorStoreUnavailable(Exception):
    """Search could not be executed; this is not an empty result."""

class SimpleDeterministicEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Sovereign, offline-guaranteed lightweight embedding function.
    Produces deterministic 384-dimensional normalized vectors from text tokens
    without requiring external model downloads or internet access.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def name(self) -> str:
        return "sovereign_deterministic"

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            words = re.findall(r"\w+", text.lower())
            vec = [0.0] * self.dimension
            if not words:
                embeddings.append(vec)
                continue

            for idx, word in enumerate(words):
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
                dim_idx = h % self.dimension
                weight = 1.0 / math.log2(idx + 2)
                vec[dim_idx] += weight * (1.0 if (h % 2 == 0) else -1.0)

            # L2 Normalize
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 1e-9:
                vec = [x / norm for x in vec]
            embeddings.append(vec)
        return embeddings


class VectorStoreService:
    EMBEDDING_MODEL = "oraclex-deterministic-hash-v1"
    EMBEDDING_DIMENSIONS = 384

    def __init__(self):
        client_settings = ChromaSettings(anonymized_telemetry=False)
        if settings.CHROMA_HOST:
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                ssl=settings.CHROMA_SSL,
                settings=client_settings,
            )
        else:
            # Embedded storage is for isolated tests or a single development process.
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR, settings=client_settings,
            )
        self.embedding_fn = SimpleDeterministicEmbeddingFunction(self.EMBEDDING_DIMENSIONS)
        self.collection = self.client.get_or_create_collection(
            name="oraclex_company_knowledge",
            embedding_function=self.embedding_fn
        )

    def index_chunks(
        self,
        document_id: str,
        company_id: str,
        clearance_level: int,
        department_id: Optional[str],
        is_company_wide: bool,
        chunks: List[Any],
        doc_title: str,
        version_id: Optional[str] = None,
    ) -> int:
        """Indexes document chunks into ChromaDB with rich RBAC metadata."""
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            active_version_id = version_id or document_id
            chunk_id = f"{active_version_id}_chunk_{idx}"
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append({
                "document_id": document_id,
                "version_id": active_version_id,
                "company_id": str(company_id),
                "clearance_level": int(clearance_level),
                "department_id": str(department_id or "COMPANY_WIDE"),
                "is_company_wide": bool(is_company_wide),
                "page_number": int(getattr(chunk, "page_number", 1) or 1),
                "doc_title": str(doc_title),
                "chunk_index": int(idx)
            })

        # Upsert in batches of 50
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        return len(ids)

    def search_authorized_chunks(
        self,
        company_id: str,
        user_clearance: int,
        user_department_id: Optional[str],
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search over ChromaDB and enforces strict RBAC clearance
        and departmental boundaries on candidate chunks.
        """
        if not query.strip():
            return []

        # Query candidates from ChromaDB collection
        fetch_limit = min(n_results * 4, 30)
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=fetch_limit,
                where={"company_id": str(company_id)}
            )
        except Exception as exc:
            raise VectorStoreUnavailable("Document search is temporarily unavailable. Please retry.") from exc

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        authorized_items = []
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0] if ("distances" in results and results["distances"]) else [0.5] * len(docs)

        for doc_text, meta, dist in zip(docs, metas, distances):
            chunk_clearance = int(meta.get("clearance_level", 1))
            is_company_wide = bool(meta.get("is_company_wide", True))
            chunk_dept = meta.get("department_id")

            # 1. Clearance Check: User must have equal or higher clearance level
            if user_clearance < chunk_clearance:
                continue

            # 2. Department Boundary Check
            if not is_company_wide:
                # Level 4 Restricted clearance possesses enterprise-wide governance authority
                if user_clearance < 4 and chunk_dept != "COMPANY_WIDE" and chunk_dept != str(user_department_id):
                    continue

            similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            authorized_items.append({
                "document_id": meta.get("document_id"),
                "version_id": meta.get("version_id"),
                "title": meta.get("doc_title", "Document"),
                "content": doc_text,
                "page_number": meta.get("page_number", 1),
                "chunk_index": meta.get("chunk_index", 0),
                "clearance_level": chunk_clearance,
                "similarity_score": round(similarity, 3)
            })

            if len(authorized_items) >= n_results:
                break

        return authorized_items

    def delete_document_chunks(self, document_id: str):
        """Removes all indexed chunks for a given document."""
        self.collection.delete(where={"document_id": document_id})

    def delete_version_chunks(self, version_id: str):
        """Removes all indexed chunks for one immutable document version."""
        self.collection.delete(where={"version_id": version_id})

    def version_chunk_count(self, version_id: str) -> int:
        result = self.collection.get(where={"version_id": version_id}, include=[])
        return len(result.get("ids", []))

vector_store_service = VectorStoreService()
