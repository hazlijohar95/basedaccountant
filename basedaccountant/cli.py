"""CLI for Based Accountant.

Usage:
    basedaccountant serve          Start the web server
    basedaccountant search <query> Search standards from the terminal
    basedaccountant mcp            Start the MCP server
    basedaccountant info           Show index statistics
"""

from __future__ import annotations

import click

from basedaccountant import __version__


@click.group()
@click.version_option(__version__)
def main():
    """Based Accountant — AI-powered accounting standards research."""
    pass


@main.command()
@click.option("--port", default=3000, help="Port to serve on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str):
    """Start the web server."""
    import uvicorn

    from basedaccountant.search import SearchEngine

    click.echo(f"  Based Accountant v{__version__}")
    click.echo()

    engine = SearchEngine()
    click.echo(f"  Loading index... ", nl=False)
    docs = engine.num_docs
    click.echo(f"{docs:,} chunks indexed")
    vector = "on" if engine.vector_available else "off"
    click.echo(f"  Search:  BM25 + vector ({vector})")
    click.echo()
    click.echo(f"  → http://{host}:{port}")
    click.echo()

    uvicorn.run(
        "basedaccountant.server:app",
        host=host,
        port=port,
        log_level="warning",
    )


@main.command()
@click.argument("query")
@click.option("-k", "--top-k", default=5, help="Number of results")
def search(query: str, top_k: int):
    """Search accounting standards from the terminal."""
    from basedaccountant.search import SearchEngine

    engine = SearchEngine()
    results = engine.search(query, k=top_k)

    if not results:
        click.echo("No results found.")
        return

    for i, r in enumerate(results, 1):
        click.echo()
        click.secho(f"  [{i}] {r.citation()}", fg="green", bold=True)
        click.secho(f"      Score: {r.score:.2f}", fg="bright_black")
        click.echo()
        # Wrap text at ~80 chars
        text = r.text.strip()
        if len(text) > 300:
            text = text[:300] + "..."
        for line in text.split("\n"):
            click.echo(f"      {line}")
        click.echo()
        click.echo("  " + "─" * 60)


@main.command()
def mcp():
    """Start the MCP server (for Claude Code, Cursor, etc.)."""
    from basedaccountant.mcp_server import mcp as mcp_app

    mcp_app.run()


@main.command()
def info():
    """Show index statistics."""
    from basedaccountant.search import SearchEngine

    engine = SearchEngine()

    click.echo()
    click.secho("  Based Accountant", bold=True)
    click.secho(f"  v{__version__}", fg="bright_black")
    click.echo()
    click.echo(f"  Data directory:  {engine.data_dir}")
    click.echo(f"  Chunks indexed:  {engine.num_docs:,}")
    click.echo(f"  Standards:       {engine.num_standards:,}")
    click.echo(f"  Vector search:   {'available' if engine.vector_available else 'unavailable (pip install chromadb sentence-transformers)'}")
    click.echo()
