from __future__ import annotations

import argparse
import json
from typing import Literal

from mcp.server.fastmcp import FastMCP

try:
    from . import fix_memory
except ImportError:
    import fix_memory


mcp = FastMCP(
    "fix-memory",
    instructions=(
        "Local-first coding fix memory. Search previous error fixes before debugging, "
        "and save clean fix cases after verification."
    ),
)


@mcp.tool()
def save_fix_case(
    title: str,
    project: str = "",
    language: str = "",
    framework: str = "",
    command: str = "",
    error: str = "",
    tags: str = "",
    source_tool: str = "mcp",
    status: Literal["fixed", "failed", "partial"] = "fixed",
) -> str:
    """Save a local Markdown fix case for a real coding error or failed attempt."""
    args = argparse.Namespace(
        title=title,
        project=project,
        language=language,
        framework=framework,
        command=command,
        error=error,
        tags=tags,
        source_tool=source_tool,
        status=status,
    )
    path = fix_memory.create_case(args)
    return f"Saved fix case: {path}"


@mcp.tool()
def search_fixes(query: str, limit: int = 5) -> str:
    """Search local fix cases with hybrid keyword + vector retrieval."""
    results = fix_memory.find_cases(query, limit, mode="hybrid")
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def search_fixes_vector(query: str, limit: int = 5) -> str:
    """Search local fix cases using only TF-IDF vector cosine similarity."""
    results = fix_memory.find_cases(query, limit, mode="vector")
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def rebuild_vector_index() -> str:
    """Rebuild the local TF-IDF vector index for fix-memory cases."""
    root = fix_memory.memory_root()
    index = fix_memory.vector_search.build_index(root)
    return f"Rebuilt vector index: {root / fix_memory.vector_search.INDEX_FILE}\ndocuments: {len(index.get('documents', []))}"


@mcp.tool()
def get_fix_case(path: str) -> str:
    """Read a full fix case by relative path, absolute path, or filename."""
    return fix_memory.read_case(path)


@mcp.tool()
def list_recent_fixes(limit: int = 10) -> str:
    """List recently updated fix cases and failed attempts."""
    recent = fix_memory.list_recent(limit)
    return json.dumps(recent, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
