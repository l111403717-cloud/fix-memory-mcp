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
def search_memory(query: str, memory_type: str = "", limit: int = 5, mode: Literal["hybrid", "keyword", "vector"] = "hybrid") -> str:
    """Search long-term memory with optional memory type filtering."""
    results = fix_memory.search_memory_items(query, limit=limit, memory_type=memory_type, mode=mode)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def assess_memory(
    memory_type: str,
    title: str,
    content: str,
    verified: bool = False,
    repeat_observed: bool = False,
    duration_minutes: int = 0,
    user_requested: bool = False,
) -> str:
    """Assess whether something should be saved as long-term memory."""
    result = fix_memory.assess_memory_value(
        memory_type,
        title,
        content,
        verified=verified,
        repeat_observed=repeat_observed,
        duration_minutes=duration_minutes,
        user_requested=user_requested,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def save_memory(
    memory_type: str,
    title: str,
    content: str,
    project: str = "",
    tags: str = "",
    evidence: str = "",
    source_tool: str = "mcp",
    scope: str = "global",
    sensitivity: Literal["public", "private", "secret"] = "private",
    duration_minutes: int = 0,
    verified: bool = False,
    repeat_observed: bool = False,
    user_requested: bool = False,
    force: bool = False,
) -> str:
    """Save or update long-term memory through the write gate."""
    args = argparse.Namespace(
        memory_type=memory_type,
        title=title,
        content=content,
        project=project,
        tags=tags,
        evidence=evidence,
        source_tool=source_tool,
        scope=scope,
        sensitivity=sensitivity,
        duration_minutes=duration_minutes,
        verified=verified,
        repeat_observed=repeat_observed,
        user_requested=user_requested,
        force=force,
    )
    result = fix_memory.save_memory_entry(args)
    return json.dumps(result, ensure_ascii=False, indent=2)


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
