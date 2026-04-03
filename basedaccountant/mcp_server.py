"""MCP server for Based Accountant.

Exposes Malaysian accounting standards search to any MCP-compatible
AI tool — Claude Code, Claude Desktop, Cursor, Windsurf, etc.

Start with:
    basedaccountant mcp

Configure in claude_desktop_config.json or .claude.json:
    {
      "mcpServers": {
        "basedaccountant": {
          "command": "python3",
          "args": ["-m", "basedaccountant.mcp_server"]
        }
      }
    }
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from basedaccountant.search import SearchEngine

mcp = FastMCP(
    "Based Accountant",
    instructions="AI-powered search over Malaysian accounting standards (MFRS, MPERS, ITA 1967). "
    "73,380 indexed chunks from 308 MASB standards with hybrid BM25 + vector search.",
)

engine = SearchEngine()


@mcp.tool()
def search_standards(query: str, top_k: int = 10) -> str:
    """Search Malaysian accounting standards (MFRS, MPERS, ITA 1967).

    Uses hybrid BM25 + vector search across 73,380 indexed chunks from 308
    MASB standards. Returns relevant excerpts with citations.

    Args:
        query: Natural language query about accounting standards.
               Examples: "revenue recognition for long-term contracts",
               "MFRS 16 lease modifications", "uncertain tax positions MPERS"
        top_k: Number of results to return (default 10)
    """
    results = engine.search(query, k=top_k)

    if not results:
        return "No results found for this query."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.citation()}")
        parts.append(f"Score: {r.score:.4f}")
        parts.append(r.text)
        parts.append("")

    return "\n".join(parts)


@mcp.tool()
def lookup_standard(standard: str, top_k: int = 10) -> str:
    """Look up a specific accounting standard by name or number.

    Args:
        standard: Standard identifier, e.g. "MFRS 15", "MPERS Section 23",
                  "MFRS 136", "ITA 1967 Schedule 3"
        top_k: Number of chunks to return (default 10)
    """
    results = engine.search(standard, k=top_k)

    if not results:
        return f"No results found for '{standard}'."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.citation()}")
        parts.append(r.text)
        parts.append("")

    return "\n".join(parts)


@mcp.tool()
def compare_standards(topic: str, frameworks: str = "MFRS,MPERS") -> str:
    """Compare how different frameworks treat the same accounting topic.

    Useful for understanding differences between MFRS (full framework)
    and MPERS (simplified framework for private entities).

    Args:
        topic: The accounting topic to compare, e.g. "revenue recognition",
               "financial instruments", "lease accounting"
        frameworks: Comma-separated frameworks to compare (default "MFRS,MPERS")
    """
    fw_list = [f.strip().upper() for f in frameworks.split(",")]
    all_results = engine.search(topic, k=30)

    parts = []
    for fw in fw_list:
        fw_results = [r for r in all_results if r.framework.upper() == fw][:5]
        parts.append(f"═══ {fw} ═══")
        if not fw_results:
            parts.append(f"No results found under {fw}.")
        else:
            for i, r in enumerate(fw_results, 1):
                parts.append(f"[{i}] {r.citation()}")
                parts.append(r.text)
                parts.append("")
        parts.append("")

    return "\n".join(parts)


@mcp.tool()
def index_info() -> str:
    """Show information about the indexed accounting standards."""
    return (
        f"Based Accountant Index\n"
        f"  Chunks indexed:  {engine.num_docs:,}\n"
        f"  Standards:       {engine.num_standards:,}\n"
        f"  Vector search:   {'available' if engine.vector_available else 'BM25 only'}\n"
        f"  Data directory:  {engine.data_dir}\n"
        f"\n"
        f"Covers: MFRS (full framework), MPERS (private entities), ITA 1967 (tax law), LHDN rulings"
    )


if __name__ == "__main__":
    mcp.run()
