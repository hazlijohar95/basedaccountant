"""FastAPI server for Based Accountant.

Serves the search API and the web UI from a single process.
Start with: basedaccountant serve
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from basedaccountant.search import SearchEngine, SearchResult

app = FastAPI(
    title="Based Accountant",
    description="AI-powered accounting standards research",
    version="0.1.0",
)

engine = SearchEngine()

STATIC_DIR = Path(__file__).parent / "static"


# ── Models ──────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    k: int = 10


class SearchResultResponse(BaseModel):
    id: str
    text: str
    score: float
    source: str
    framework: str
    section: str
    page: int
    citation: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]
    total_docs: int


class AskRequest(BaseModel):
    query: str
    k: int = 5


# ── API Routes ──────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "docs_indexed": engine.num_docs,
        "vector_search": engine.vector_available,
    }


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest):
    results = engine.search(req.query, k=req.k)
    return SearchResponse(
        query=req.query,
        results=[
            SearchResultResponse(
                id=r.id,
                text=r.text,
                score=r.score,
                source=r.source,
                framework=r.framework,
                section=r.section,
                page=r.page,
                citation=r.citation(),
            )
            for r in results
        ],
        total_docs=engine.num_docs,
    )


@app.post("/api/ask")
async def ask(req: AskRequest):
    """Search + AI synthesis with streaming response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        results = engine.search(req.query, k=req.k)
        return {
            "error": "ANTHROPIC_API_KEY not set. Showing search results only.",
            "results": [
                {
                    "text": r.text,
                    "citation": r.citation(),
                    "score": r.score,
                }
                for r in results
            ],
        }

    results = engine.search(req.query, k=req.k)
    context = _build_context(results)

    async def stream() -> AsyncGenerator[str, None]:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        with client.messages.stream(
            model="claude-sonnet-4-5-20250514",
            max_tokens=2048,
            system=(
                "You are Based Accountant, an expert on Malaysian accounting standards "
                "(MFRS, MPERS, ITA 1967). Answer the user's question using ONLY the "
                "provided source material. Cite specific standards, sections, and "
                "paragraph numbers. If the sources don't contain enough information "
                "to answer, say so. Be precise and concise."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Question: {req.query}\n\n{context}",
                }
            ],
        ) as stream_response:
            for text in stream_response.text_stream:
                yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


def _build_context(results: list[SearchResult]) -> str:
    """Build context string from search results for the AI prompt."""
    parts = ["Here are the relevant excerpts from Malaysian accounting standards:\n"]
    for i, r in enumerate(results, 1):
        parts.append(f"[Source {i}] {r.citation()}")
        parts.append(r.text)
        parts.append("")
    return "\n".join(parts)


# ── Web UI ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())
