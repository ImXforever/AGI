"""Unit tests for the retrieval layer (chunking, embedding, similarity search).

`app.core.rag` backs every grounded answer the knowledge agent gives. The
chunker, the deterministic embedding and the cosine ranking are all pure, so
the whole retrieval path can be tested without a model or a database.
"""

from __future__ import annotations

import pytest

from app.core import rag

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_index():
    """Each test starts and ends with an empty in-memory index."""
    rag.clear_index()
    yield
    rag.clear_index()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


class TestChunkText:
    def test_empty_text_produces_no_chunks(self):
        assert rag.chunk_text("") == []

    def test_whitespace_only_produces_no_chunks(self):
        assert rag.chunk_text("   \n\n  ") == []

    def test_short_text_stays_a_single_chunk(self):
        assert rag.chunk_text("a short paragraph") == ["a short paragraph"]

    def test_long_text_is_split(self):
        text = "\n\n".join(f"Paragraph number {i}. " + "word " * 40 for i in range(10))
        assert len(rag.chunk_text(text, chunk_size=200, overlap=0)) > 1

    def test_chunks_are_never_empty_strings(self):
        text = "\n\n".join("para " * 30 for _ in range(6))
        assert all(c.strip() for c in rag.chunk_text(text, chunk_size=100, overlap=10))

    def test_no_content_is_lost_when_overlap_is_zero(self):
        text = "\n\n".join(f"unique{i}" for i in range(5))
        joined = " ".join(rag.chunk_text(text, chunk_size=20, overlap=0))
        for i in range(5):
            assert f"unique{i}" in joined

    def test_a_single_oversized_paragraph_is_split_on_sentences(self):
        text = " ".join(f"This is sentence number {i}." for i in range(40))
        chunks = rag.chunk_text(text, chunk_size=120, overlap=0)
        assert len(chunks) > 1

    def test_arabic_sentence_terminator_is_respected(self):
        text = " ".join("ما هو السعر؟" for _ in range(40))
        assert len(rag.chunk_text(text, chunk_size=100, overlap=0)) > 1


# ---------------------------------------------------------------------------
# Embedding & similarity
# ---------------------------------------------------------------------------


class TestEmbedding:
    def test_embedding_has_a_fixed_dimension(self):
        assert len(rag._simple_embed("anything")) == 64

    def test_embedding_is_deterministic(self):
        assert rag._simple_embed("diesel pump") == rag._simple_embed("diesel pump")

    def test_embedding_is_unit_normalised(self):
        vec = rag._simple_embed("some text")
        assert abs(sum(v * v for v in vec) ** 0.5 - 1.0) < 1e-9

    def test_empty_text_yields_a_zero_vector(self):
        assert rag._simple_embed("") == [0.0] * 64

    def test_different_texts_embed_differently(self):
        assert rag._simple_embed("diesel") != rag._simple_embed("gasoline")


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self):
        vec = rag._simple_embed("hello")
        assert abs(rag._cosine_similarity(vec, vec) - 1.0) < 1e-9

    def test_zero_vector_scores_zero_rather_than_dividing_by_zero(self):
        assert rag._cosine_similarity([0.0] * 64, rag._simple_embed("x")) == 0.0

    def test_orthogonal_vectors_score_zero(self):
        assert rag._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_similarity_is_symmetric(self):
        a, b = rag._simple_embed("diesel"), rag._simple_embed("diesel fuel")
        assert rag._cosine_similarity(a, b) == pytest.approx(rag._cosine_similarity(b, a))


class TestDocId:
    def test_id_is_deterministic(self):
        assert rag._doc_id("text", "src") == rag._doc_id("text", "src")

    def test_source_is_part_of_the_identity(self):
        assert rag._doc_id("text", "a") != rag._doc_id("text", "b")

    def test_id_is_a_short_hex_digest(self):
        assert len(rag._doc_id("t")) == 16


# ---------------------------------------------------------------------------
# Index & search
# ---------------------------------------------------------------------------


class TestIndexing:
    async def test_a_fresh_index_is_empty_and_not_ready(self):
        stats = rag.index_stats()
        assert stats["total_documents"] == 0 and stats["ready"] is False

    async def test_indexing_reports_the_chunk_count(self):
        assert await rag.index_documents([{"text": "diesel fuel specification"}]) == 1

    async def test_documents_without_text_are_skipped(self):
        assert await rag.index_documents([{"source": "x"}, {"text": "   "}]) == 0

    async def test_indexing_marks_the_store_ready(self):
        await rag.index_documents([{"text": "content here"}])
        assert rag.index_stats()["ready"] is True

    async def test_embeddings_stay_aligned_with_documents(self):
        await rag.index_documents([{"text": f"doc {i}"} for i in range(4)])
        stats = rag.index_stats()
        assert stats["total_documents"] == stats["total_embeddings"]

    async def test_duplicates_are_skipped_by_default(self):
        doc = [{"text": "identical content", "source": "s"}]
        await rag.index_documents(doc)
        assert await rag.index_documents(doc) == 0

    async def test_deduplication_can_be_disabled(self):
        doc = [{"text": "identical content", "source": "s"}]
        await rag.index_documents(doc)
        assert await rag.index_documents(doc, deduplicate=False) == 1

    async def test_clearing_empties_the_store(self):
        await rag.index_documents([{"text": "content"}])
        rag.clear_index()
        stats = rag.index_stats()
        assert stats["total_documents"] == 0 and stats["ready"] is False


class TestSearch:
    async def test_searching_an_empty_index_returns_nothing(self):
        assert await rag.search_similar("anything") == []

    async def test_an_exact_match_is_retrieved(self):
        await rag.index_documents([{"text": "diesel fuel specification sheet", "source": "spec"}])
        results = await rag.search_similar("diesel fuel specification sheet")
        assert results and results[0]["source"] == "spec"

    async def test_results_carry_the_expected_fields(self):
        await rag.index_documents([{"text": "hydraulic oil viscosity", "metadata": {"k": "v"}}])
        results = await rag.search_similar("hydraulic oil viscosity")
        assert set(results[0]) == {"text", "score", "source", "metadata"}
        assert results[0]["metadata"] == {"k": "v"}

    async def test_results_are_ordered_by_descending_score(self):
        await rag.index_documents(
            [
                {"text": "diesel fuel specification"},
                {"text": "completely unrelated cooking recipe"},
                {"text": "diesel fuel specification sheet revision"},
            ]
        )
        scores = [
            r["score"] for r in await rag.search_similar("diesel fuel specification", threshold=0.0)
        ]
        assert scores == sorted(scores, reverse=True)

    async def test_top_k_limits_the_result_count(self):
        await rag.index_documents([{"text": f"diesel document number {i}"} for i in range(8)])
        assert len(await rag.search_similar("diesel document", top_k=3, threshold=0.0)) <= 3

    async def test_a_high_threshold_filters_everything_out(self):
        await rag.index_documents([{"text": "diesel fuel"}])
        assert await rag.search_similar("完全に無関係", threshold=0.99) == []

    async def test_source_filter_restricts_the_results(self):
        await rag.index_documents(
            [
                {"text": "diesel fuel spec", "source": "a"},
                {"text": "diesel fuel spec sheet", "source": "b"},
            ]
        )
        results = await rag.search_similar("diesel fuel spec", threshold=0.0, source_filter="a")
        assert all(r["source"] == "a" for r in results)

    async def test_scores_are_rounded_for_readability(self):
        await rag.index_documents([{"text": "diesel"}])
        for r in await rag.search_similar("diesel", threshold=0.0):
            assert r["score"] == round(r["score"], 4)
