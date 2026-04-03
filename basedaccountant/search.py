"""Hybrid search over Malaysian accounting standards.

Architecture:
    Query → BM25 sparse search (keyword matching, Lucene scoring)
          → Vector search (semantic similarity, paraphrase-multilingual-MiniLM-L12-v2)
          → Reciprocal Rank Fusion (RRF) merges both ranked lists
          → Top-k results with source citations

The corpus is pre-indexed from 308 MASB standards (MFRS + MPERS + ITA 1967).
Each chunk carries metadata: framework, source, section, page number.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import bm25s

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the accounting standards corpus."""

    id: str
    text: str
    score: float
    source: str = ""
    framework: str = ""
    section: str = ""
    page: int = 0

    def citation(self) -> str:
        """Human-readable citation for this result."""
        parts = []
        if self.framework:
            parts.append(self.framework)
        if self.source:
            parts.append(self.source.replace("_", " "))
        if self.section:
            parts.append(f"§ {self.section}")
        if self.page:
            parts.append(f"p. {self.page}")
        return " · ".join(parts) if parts else self.id


DATA_DIR = Path(os.environ.get("BASED_DATA_DIR", Path.home() / ".basedaccountant"))


class SearchEngine:
    """Hybrid BM25 + vector search over MASB accounting standards."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._corpus: list[dict] | None = None
        self._corpus_by_id: dict[str, dict] | None = None
        self._bm25: bm25s.BM25 | None = None
        self._chroma = None
        self._vector_available: bool | None = None

    # ── Lazy loaders ────────────────────────────────────────

    def _load_corpus(self):
        path = self.data_dir / "index" / "bm25_corpus.json"
        with open(path) as f:
            self._corpus = json.load(f)
        self._corpus_by_id = {doc["id"]: doc for doc in self._corpus}

    @property
    def corpus(self) -> list[dict]:
        if self._corpus is None:
            self._load_corpus()
        return self._corpus

    @property
    def corpus_by_id(self) -> dict[str, dict]:
        if self._corpus_by_id is None:
            self._load_corpus()
        return self._corpus_by_id

    @property
    def bm25(self) -> bm25s.BM25:
        if self._bm25 is None:
            path = self.data_dir / "index" / "bm25"
            self._bm25 = bm25s.BM25.load(str(path), load_corpus=False)
        return self._bm25

    @property
    def chroma(self):
        if self._chroma is None:
            try:
                import chromadb

                client = chromadb.PersistentClient(path=str(self.data_dir / "index"))
                self._chroma = client.get_collection("standards")
                self._vector_available = True
            except Exception as e:
                log.warning("Vector search unavailable: %s", e)
                self._vector_available = False
        return self._chroma

    @property
    def vector_available(self) -> bool:
        if self._vector_available is None:
            self.chroma  # trigger lazy load
        return self._vector_available

    # ── Search methods ──────────────────────────────────────

    def search_bm25(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        """Sparse keyword search. Returns list of (doc_id, score)."""
        tokens = bm25s.tokenize(query, stemmer=None)
        indices, scores = self.bm25.retrieve(tokens, k=k)
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if score <= 0:
                continue
            doc_id = self.corpus[int(idx)]["id"]
            results.append((doc_id, float(score)))
        return results

    def search_vector(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        """Dense semantic search via ChromaDB. Returns list of (doc_id, score)."""
        if not self.vector_available:
            return []
        results = self.chroma.query(query_texts=[query], n_results=k)
        out = []
        for doc_id, distance in zip(results["ids"][0], results["distances"][0]):
            score = 1 / (1 + distance)
            out.append((doc_id, score))
        return out

    def search(self, query: str, k: int = 10) -> list[SearchResult]:
        """Hybrid search using Reciprocal Rank Fusion.

        Combines BM25 (keyword) and vector (semantic) results. If vector
        search is unavailable, falls back to BM25 only.
        """
        bm25_results = self.search_bm25(query, k=20)
        vector_results = self.search_vector(query, k=20)

        # Reciprocal Rank Fusion
        rrf_k = 60
        rrf_scores: dict[str, float] = {}

        for rank, (doc_id, _) in enumerate(bm25_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank + 1)

        for rank, (doc_id, _) in enumerate(vector_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank + 1)

        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:k]

        results = []
        for doc_id in sorted_ids:
            doc = self.corpus_by_id.get(doc_id)
            if not doc:
                continue
            meta = doc.get("meta", {})
            results.append(
                SearchResult(
                    id=doc_id,
                    text=doc["text"],
                    score=rrf_scores[doc_id],
                    source=meta.get("source", ""),
                    framework=meta.get("framework", ""),
                    section=meta.get("section", ""),
                    page=meta.get("page", 0),
                )
            )
        return results

    # ── Stats ───────────────────────────────────────────────

    @property
    def num_docs(self) -> int:
        return self.bm25.scores["num_docs"]

    @property
    def num_standards(self) -> int:
        """Count unique source documents in the corpus."""
        sources = {doc.get("meta", {}).get("source", "") for doc in self.corpus}
        return len(sources - {""})
