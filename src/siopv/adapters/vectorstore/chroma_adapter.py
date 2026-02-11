"""ChromaDB vector store adapter.

Implements VectorStorePort for storing and querying enrichment embeddings.
Uses hybrid persistence: SQLite for storage + LRU cache for performance.

Based on Context7 ChromaDB documentation patterns.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import TYPE_CHECKING

import chromadb
import structlog

from siopv.application.ports import VectorStorePort
from siopv.domain.value_objects import EnrichmentData

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


class LRUCache:
    """Simple LRU cache for EnrichmentData objects."""

    def __init__(self, max_size: int = 1000):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
        """
        self._cache: OrderedDict[str, EnrichmentData] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> EnrichmentData | None:
        """Get item from cache, moving to end (most recent)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: EnrichmentData) -> None:
        """Put item in cache, evicting oldest if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # Remove oldest
            self._cache[key] = value

    def remove(self, key: str) -> bool:
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


class ChromaDBAdapter(VectorStorePort):
    """ChromaDB adapter for enrichment data storage.

    Features:
    - Persistent storage using SQLite backend
    - LRU cache for frequently accessed items
    - Automatic embedding generation
    - Similarity search for related vulnerabilities
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: object | None = None,
    ):
        """Initialize ChromaDB adapter.

        Args:
            settings: Application settings with ChromaDB configuration
            client: Optional pre-configured ChromaDB client (for testing)
        """
        self._persist_dir = settings.chroma_persist_dir
        self._collection_name = settings.chroma_collection_name
        self._cache_size = settings.chroma_cache_size_mb

        # Initialize LRU cache (estimate ~4KB per enrichment = 1000 items per 4MB)
        estimated_items = max(100, (self._cache_size * 1024) // 4)
        self._cache = LRUCache(max_size=estimated_items)

        self._external_client = client
        self._owned_client: object | None = None
        self._collection: Collection | None = None

        logger.info(
            "chromadb_adapter_initialized",
            persist_dir=str(self._persist_dir),
            collection_name=self._collection_name,
            cache_items=estimated_items,
        )

    def _get_client(self) -> object:
        """Get or create ChromaDB client."""
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            # Ensure persist directory exists
            self._persist_dir.mkdir(parents=True, exist_ok=True)

            # Create persistent client (Context7 verified pattern)
            self._owned_client = chromadb.PersistentClient(path=str(self._persist_dir))

            logger.debug("chromadb_client_created", path=str(self._persist_dir))

        return self._owned_client

    def _get_collection(self) -> Collection:
        """Get or create ChromaDB collection."""
        if self._collection is None:
            client = self._get_client()

            # Get or create collection (Context7 verified pattern)
            # client typed as object; PersistentClient has this method at runtime
            self._collection = client.get_or_create_collection(  # type: ignore[attr-defined]
                name=self._collection_name,
                metadata={"description": "SIOPV vulnerability enrichment data"},
            )

            logger.debug(
                "chromadb_collection_ready",
                name=self._collection_name,
                count=self._collection.count(),
            )

        return self._collection

    def _enrichment_to_document(self, enrichment: EnrichmentData) -> dict[str, object]:
        """Convert EnrichmentData to ChromaDB document format.

        Args:
            enrichment: EnrichmentData to convert

        Returns:
            Dictionary with id, document, and metadata
        """
        # Generate text for embedding
        document_text = enrichment.to_embedding_text()

        # Serialize full enrichment data as metadata
        metadata = {
            "cve_id": enrichment.cve_id,
            "enriched_at": enrichment.enriched_at.isoformat(),
            "relevance_score": enrichment.relevance_score,
            "has_nvd": enrichment.nvd is not None,
            "has_epss": enrichment.epss is not None,
            "has_github": enrichment.github_advisory is not None,
            "osint_count": len(enrichment.osint_results),
            # Store full JSON for reconstruction
            "full_data": enrichment.model_dump_json(),
        }

        return {
            "id": enrichment.cve_id,
            "document": document_text,
            "metadata": metadata,
        }

    def _document_to_enrichment(self, metadata: dict[str, object]) -> EnrichmentData:
        """Reconstruct EnrichmentData from ChromaDB metadata.

        Args:
            metadata: ChromaDB document metadata

        Returns:
            EnrichmentData instance
        """
        # metadata values typed as object; full_data is str at runtime
        full_data = json.loads(metadata["full_data"])  # type: ignore[arg-type]
        return EnrichmentData.model_validate(full_data)

    async def store_enrichment(self, enrichment: EnrichmentData) -> str:
        """Store enrichment data with generated embedding.

        Args:
            enrichment: EnrichmentData to store

        Returns:
            Document ID for stored enrichment
        """
        collection = self._get_collection()
        doc = self._enrichment_to_document(enrichment)

        # Upsert to handle duplicates
        # doc values typed as object; chromadb expects str/dict at runtime
        collection.upsert(
            ids=[doc["id"]],  # type: ignore[list-item]
            documents=[doc["document"]],  # type: ignore[list-item]
            metadatas=[doc["metadata"]],  # type: ignore[list-item]
        )

        # Update cache
        self._cache.put(enrichment.cve_id, enrichment)

        logger.debug("chromadb_enrichment_stored", cve_id=enrichment.cve_id)
        return doc["id"]  # type: ignore[return-value]  # doc["id"] is str at runtime

    async def store_enrichments_batch(self, enrichments: list[EnrichmentData]) -> list[str]:
        """Store multiple enrichments efficiently.

        Args:
            enrichments: List of EnrichmentData to store

        Returns:
            List of document IDs
        """
        if not enrichments:
            return []

        collection = self._get_collection()

        ids = []
        documents = []
        metadatas = []

        for enrichment in enrichments:
            doc = self._enrichment_to_document(enrichment)
            ids.append(doc["id"])
            documents.append(doc["document"])
            metadatas.append(doc["metadata"])

            # Update cache
            self._cache.put(enrichment.cve_id, enrichment)

        # Batch upsert — lists contain object but chromadb expects str/dict
        collection.upsert(
            ids=ids,  # type: ignore[arg-type]
            documents=documents,  # type: ignore[arg-type]
            metadatas=metadatas,  # type: ignore[arg-type]
        )

        logger.info("chromadb_batch_stored", count=len(enrichments))
        return ids  # type: ignore[return-value]  # list[object] is list[str] at runtime

    async def query_similar(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        min_relevance: float = 0.0,
    ) -> list[tuple[EnrichmentData, float]]:
        """Query for similar enrichment documents.

        Args:
            query_text: Text to find similar documents for
            n_results: Maximum results to return
            min_relevance: Minimum similarity score (0-1)

        Returns:
            List of (EnrichmentData, similarity_score) tuples
        """
        collection = self._get_collection()

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "distances"],
        )

        enrichments_with_scores = []

        if results["metadatas"] and results["distances"]:
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            for metadata, distance in zip(metadatas, distances, strict=False):
                # Convert distance to similarity (ChromaDB uses L2 distance)
                # Lower distance = higher similarity
                similarity = 1.0 / (1.0 + distance)

                if similarity >= min_relevance:
                    # metadata typed as Mapping but is dict at runtime
                    enrichment = self._document_to_enrichment(metadata)  # type: ignore[arg-type]
                    enrichments_with_scores.append((enrichment, similarity))

        logger.debug(
            "chromadb_query_complete",
            query_len=len(query_text),
            results=len(enrichments_with_scores),
        )
        return enrichments_with_scores

    async def get_by_cve_id(self, cve_id: str) -> EnrichmentData | None:
        """Retrieve stored enrichment by CVE ID.

        Args:
            cve_id: CVE identifier

        Returns:
            EnrichmentData if found, None otherwise
        """
        # Check cache first
        cached = self._cache.get(cve_id)
        if cached:
            logger.debug("chromadb_cache_hit", cve_id=cve_id)
            return cached

        collection = self._get_collection()

        results = collection.get(
            ids=[cve_id],
            include=["metadatas"],
        )

        if results["metadatas"] and results["metadatas"][0]:
            metadata = results["metadatas"][0]
            # metadata typed as Mapping but is dict at runtime
            enrichment = self._document_to_enrichment(metadata)  # type: ignore[arg-type]

            # Update cache
            self._cache.put(cve_id, enrichment)

            return enrichment

        return None

    async def exists(self, cve_id: str) -> bool:
        """Check if enrichment exists for CVE.

        Args:
            cve_id: CVE identifier

        Returns:
            True if enrichment exists
        """
        # Check cache first
        if self._cache.get(cve_id):
            return True

        collection = self._get_collection()

        results = collection.get(
            ids=[cve_id],
            include=[],  # Don't need actual data
        )

        return bool(results["ids"])

    async def delete(self, cve_id: str) -> bool:
        """Delete enrichment by CVE ID.

        Args:
            cve_id: CVE identifier

        Returns:
            True if deleted, False if not found
        """
        if not await self.exists(cve_id):
            return False

        collection = self._get_collection()
        collection.delete(ids=[cve_id])

        # Remove from cache
        self._cache.remove(cve_id)

        logger.debug("chromadb_enrichment_deleted", cve_id=cve_id)
        return True

    async def count(self) -> int:
        """Get total count of stored enrichments.

        Returns:
            Number of stored documents
        """
        collection = self._get_collection()
        return collection.count()

    async def clear(self) -> None:
        """Clear all stored enrichments.

        Use with caution - primarily for testing.
        """
        client = self._get_client()

        # Delete and recreate collection
        # client typed as object; PersistentClient has this method at runtime
        client.delete_collection(self._collection_name)  # type: ignore[attr-defined]
        self._collection = None

        # Clear cache
        self._cache.clear()

        logger.warning("chromadb_collection_cleared", name=self._collection_name)

    def get_stats(self) -> dict[str, object]:
        """Get adapter statistics."""
        collection = self._get_collection()
        return {
            "collection_name": self._collection_name,
            "document_count": collection.count(),
            "cache_size": len(self._cache),
            "cache_max_size": self._cache._max_size,
            "persist_dir": str(self._persist_dir),
        }


__all__ = ["ChromaDBAdapter"]
