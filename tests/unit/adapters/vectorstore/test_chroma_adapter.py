"""Unit tests for ChromaDBAdapter.

Coverage targets:
- LRUCache: get/put/remove/clear/eviction/__len__
- ChromaDBAdapter.store_enrichment(): upserts to collection, updates cache
- ChromaDBAdapter.store_enrichments_batch(): batch upsert, empty list
- ChromaDBAdapter.query_similar(): with results, empty results, min_relevance filter
- ChromaDBAdapter.get_by_cve_id(): cache hit, collection hit, not found
- ChromaDBAdapter.exists(): cache hit, collection hit, not found
- ChromaDBAdapter.delete(): existing, not found
- ChromaDBAdapter.count(): delegates to collection
- ChromaDBAdapter.clear(): deletes + recreates collection
- ChromaDBAdapter.get_stats(): returns dict
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from siopv.adapters.vectorstore.chroma_adapter import ChromaDBAdapter, LRUCache
from siopv.domain.value_objects import EnrichmentData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings() -> MagicMock:
    from pathlib import Path

    settings = MagicMock()
    settings.chroma_persist_dir = Path("/tmp/test_chroma")
    settings.chroma_collection_name = "test_collection"
    settings.chroma_cache_size_mb = 4
    return settings


def _make_enrichment(cve_id: str = "CVE-2021-44228") -> EnrichmentData:
    return EnrichmentData(
        cve_id=cve_id,
        enriched_at=datetime(2024, 1, 1, tzinfo=UTC),
        relevance_score=0.85,
    )


@pytest.fixture
def mock_collection() -> MagicMock:
    collection = MagicMock()
    collection.count.return_value = 0
    return collection


@pytest.fixture
def mock_chroma_client(mock_collection: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get_or_create_collection.return_value = mock_collection
    return client


@pytest.fixture
def adapter(mock_chroma_client: MagicMock) -> ChromaDBAdapter:
    settings = _make_settings()
    return ChromaDBAdapter(settings, client=mock_chroma_client)


# ---------------------------------------------------------------------------
# LRUCache
# ---------------------------------------------------------------------------


class TestLRUCache:
    def test_get_returns_none_on_miss(self) -> None:
        cache = LRUCache(max_size=10)
        assert cache.get("missing") is None

    def test_put_and_get(self) -> None:
        cache = LRUCache(max_size=10)
        enrichment = _make_enrichment()
        cache.put("CVE-2021-44228", enrichment)
        assert cache.get("CVE-2021-44228") == enrichment

    def test_evicts_oldest_when_full(self) -> None:
        cache = LRUCache(max_size=2)
        a = _make_enrichment("CVE-A")
        b = _make_enrichment("CVE-B")
        c = _make_enrichment("CVE-C")
        cache.put("CVE-A", a)
        cache.put("CVE-B", b)
        cache.put("CVE-C", c)  # Should evict CVE-A
        assert cache.get("CVE-A") is None
        assert cache.get("CVE-B") == b
        assert cache.get("CVE-C") == c

    def test_get_moves_to_end(self) -> None:
        cache = LRUCache(max_size=2)
        a = _make_enrichment("CVE-A")
        b = _make_enrichment("CVE-B")
        c = _make_enrichment("CVE-C")
        cache.put("CVE-A", a)
        cache.put("CVE-B", b)
        cache.get("CVE-A")  # Access CVE-A → moves to end (most recent)
        cache.put("CVE-C", c)  # Should evict CVE-B (now oldest)
        assert cache.get("CVE-A") == a
        assert cache.get("CVE-B") is None

    def test_remove_existing_key(self) -> None:
        cache = LRUCache(max_size=10)
        enrichment = _make_enrichment()
        cache.put("CVE-2021-44228", enrichment)
        assert cache.remove("CVE-2021-44228") is True
        assert cache.get("CVE-2021-44228") is None

    def test_remove_missing_key_returns_false(self) -> None:
        cache = LRUCache(max_size=10)
        assert cache.remove("missing") is False

    def test_clear(self) -> None:
        cache = LRUCache(max_size=10)
        cache.put("CVE-A", _make_enrichment("CVE-A"))
        cache.put("CVE-B", _make_enrichment("CVE-B"))
        cache.clear()
        assert len(cache) == 0

    def test_len(self) -> None:
        cache = LRUCache(max_size=10)
        assert len(cache) == 0
        cache.put("CVE-A", _make_enrichment("CVE-A"))
        assert len(cache) == 1

    def test_put_updates_existing(self) -> None:
        cache = LRUCache(max_size=10)
        old = _make_enrichment("CVE-A")
        new = _make_enrichment("CVE-A")
        cache.put("CVE-A", old)
        cache.put("CVE-A", new)
        assert len(cache) == 1
        assert cache.get("CVE-A") == new


# ---------------------------------------------------------------------------
# ChromaDBAdapter — store_enrichment
# ---------------------------------------------------------------------------


class TestStoreEnrichment:
    @pytest.mark.asyncio
    async def test_upserts_to_collection(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        enrichment = _make_enrichment()

        doc_id = await adapter.store_enrichment(enrichment)

        assert doc_id == enrichment.cve_id
        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args.kwargs
        assert enrichment.cve_id in call_kwargs["ids"]

    @pytest.mark.asyncio
    async def test_updates_cache_on_store(self, adapter: ChromaDBAdapter) -> None:
        enrichment = _make_enrichment()

        await adapter.store_enrichment(enrichment)

        assert adapter._cache.get(enrichment.cve_id) == enrichment


# ---------------------------------------------------------------------------
# ChromaDBAdapter — store_enrichments_batch
# ---------------------------------------------------------------------------


class TestStoreEnrichmentsBatch:
    @pytest.mark.asyncio
    async def test_batch_upsert(self, adapter: ChromaDBAdapter, mock_collection: MagicMock) -> None:
        enrichments = [_make_enrichment(f"CVE-{i}") for i in range(3)]

        ids = await adapter.store_enrichments_batch(enrichments)

        assert len(ids) == 3
        mock_collection.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        ids = await adapter.store_enrichments_batch([])

        assert ids == []
        mock_collection.upsert.assert_not_called()


# ---------------------------------------------------------------------------
# ChromaDBAdapter — query_similar
# ---------------------------------------------------------------------------


class TestQuerySimilar:
    def _build_metadata_entry(self, cve_id: str = "CVE-2021-44228") -> dict[str, object]:
        enrichment = _make_enrichment(cve_id)
        return {"full_data": enrichment.model_dump_json()}

    @pytest.mark.asyncio
    async def test_returns_results_with_scores(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        metadata_entry = self._build_metadata_entry()
        mock_collection.query.return_value = {
            "metadatas": [[metadata_entry]],
            "distances": [[0.5]],
        }

        results = await adapter.query_similar("log4shell rce")

        assert len(results) == 1
        enrichment, score = results[0]
        assert isinstance(enrichment, EnrichmentData)
        assert score == pytest.approx(1.0 / (1.0 + 0.5))

    @pytest.mark.asyncio
    async def test_filters_by_min_relevance(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        metadata_entry = self._build_metadata_entry()
        mock_collection.query.return_value = {
            "metadatas": [[metadata_entry]],
            "distances": [[10.0]],  # Very far → low similarity
        }

        results = await adapter.query_similar("query", min_relevance=0.5)

        # similarity = 1/(1+10) ≈ 0.09, below threshold
        assert results == []

    @pytest.mark.asyncio
    async def test_empty_collection(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.query.return_value = {"metadatas": [], "distances": []}

        results = await adapter.query_similar("query")

        assert results == []


# ---------------------------------------------------------------------------
# ChromaDBAdapter — get_by_cve_id
# ---------------------------------------------------------------------------


class TestGetByCveId:
    @pytest.mark.asyncio
    async def test_returns_from_cache(self, adapter: ChromaDBAdapter) -> None:
        enrichment = _make_enrichment()
        adapter._cache.put(enrichment.cve_id, enrichment)

        result = await adapter.get_by_cve_id(enrichment.cve_id)

        assert result == enrichment

    @pytest.mark.asyncio
    async def test_fetches_from_collection_when_not_cached(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        enrichment = _make_enrichment()
        metadata_entry = {"full_data": enrichment.model_dump_json()}
        mock_collection.get.return_value = {"metadatas": [metadata_entry]}

        result = await adapter.get_by_cve_id(enrichment.cve_id)

        assert result is not None
        assert result.cve_id == enrichment.cve_id
        # Also cached now
        assert adapter._cache.get(enrichment.cve_id) is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"metadatas": [None]}

        result = await adapter.get_by_cve_id("CVE-9999-9999")

        assert result is None


# ---------------------------------------------------------------------------
# ChromaDBAdapter — exists
# ---------------------------------------------------------------------------


class TestExists:
    @pytest.mark.asyncio
    async def test_returns_true_from_cache(self, adapter: ChromaDBAdapter) -> None:
        enrichment = _make_enrichment()
        adapter._cache.put(enrichment.cve_id, enrichment)

        assert await adapter.exists(enrichment.cve_id) is True

    @pytest.mark.asyncio
    async def test_returns_true_from_collection(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"ids": ["CVE-2021-44228"]}

        assert await adapter.exists("CVE-2021-44228") is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"ids": []}

        assert await adapter.exists("CVE-9999-9999") is False


# ---------------------------------------------------------------------------
# ChromaDBAdapter — delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_deletes_existing_enrichment(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        # Seed cache so exists() returns True without extra collection.get call
        enrichment = _make_enrichment()
        adapter._cache.put(enrichment.cve_id, enrichment)

        result = await adapter.delete(enrichment.cve_id)

        assert result is True
        mock_collection.delete.assert_called_once_with(ids=[enrichment.cve_id])
        assert adapter._cache.get(enrichment.cve_id) is None

    @pytest.mark.asyncio
    async def test_returns_false_for_missing(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"ids": []}

        result = await adapter.delete("CVE-9999-9999")

        assert result is False
        mock_collection.delete.assert_not_called()


# ---------------------------------------------------------------------------
# ChromaDBAdapter — count / clear / get_stats
# ---------------------------------------------------------------------------


class TestCountClearStats:
    @pytest.mark.asyncio
    async def test_count_delegates_to_collection(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.count.return_value = 42

        count = await adapter.count()

        assert count == 42

    @pytest.mark.asyncio
    async def test_clear_deletes_collection_and_clears_cache(
        self, adapter: ChromaDBAdapter, mock_chroma_client: MagicMock
    ) -> None:
        adapter._cache.put("CVE-A", _make_enrichment("CVE-A"))

        await adapter.clear()

        mock_chroma_client.delete_collection.assert_called_once_with("test_collection")
        assert len(adapter._cache) == 0
        assert adapter._collection is None

    def test_get_stats_returns_dict(
        self, adapter: ChromaDBAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.count.return_value = 5

        stats = adapter.get_stats()

        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 5
        assert "cache_size" in stats
        assert "persist_dir" in stats
