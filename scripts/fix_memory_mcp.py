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
    verified: bool = False,
    repeat_observed: bool = False,
    duration_minutes: int = 0,
    user_requested: bool = False,
    sensitivity: Literal["public", "private", "secret"] = "private",
) -> str:
    """Assess, deduplicate, and save a local Markdown fix case when it is durable enough."""
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
        verified=verified,
        repeat_observed=repeat_observed,
        duration_minutes=duration_minutes,
        user_requested=user_requested,
        sensitivity=sensitivity,
        force=False,
    )
    result = fix_memory.save_fix_case_entry(args)
    if result["action"] == "skipped":
        return json.dumps(result, ensure_ascii=False, indent=2)
    return f"Saved fix case: {result['path']} ({result['assessment']['memory_status']})"


@mcp.tool()
def search_fixes(query: str, limit: int = 5, include_candidates: bool = False) -> str:
    """Search local fix cases with hybrid keyword + vector retrieval."""
    results = fix_memory.search_fix_items(
        query, limit, mode="hybrid", include_candidates=include_candidates
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def search_memory(
    query: str,
    memory_type: str = "",
    limit: int = 5,
    mode: Literal["hybrid", "keyword", "vector"] = "hybrid",
    include_candidates: bool = False,
) -> str:
    """Search long-term memory with optional memory type filtering."""
    results = fix_memory.search_memory_items(
        query,
        limit=limit,
        memory_type=memory_type,
        mode=mode,
        include_candidates=include_candidates,
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def should_search_memory(
    query: str,
    context: str = "",
    project: str = "",
    command: str = "",
    file_path: str = "",
    memory_type: str = "",
    force: bool = False,
) -> str:
    """Decide whether this task should search long-term memory before work continues."""
    result = fix_memory.should_search_memory(
        query,
        context=context,
        project=project,
        command=command,
        file_path=file_path,
        memory_type=memory_type,
        force=force,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def smart_search_memory(
    query: str,
    search_scope: Literal["memory", "fixes"] = "memory",
    memory_type: str = "",
    limit: int = 5,
    mode: Literal["hybrid", "keyword", "vector"] = "hybrid",
    context: str = "",
    project: str = "",
    command: str = "",
    file_path: str = "",
    force: bool = False,
    include_candidates: bool = False,
) -> str:
    """Use the retrieval gate and semantic cache before searching memory or fix cases."""
    result = fix_memory.smart_search(
        query,
        search_scope=search_scope,
        limit=limit,
        memory_type=memory_type,
        mode=mode,
        context=context,
        project=project,
        command=command,
        file_path=file_path,
        force=force,
        include_candidates=include_candidates,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def task_state(
    action: Literal["start", "show", "note", "verify", "clear"] = "show",
    goal: str = "",
    project: str = "",
    task_id: str = "",
    note: str = "",
    item: str = "",
) -> str:
    """Manage current task working memory without writing long-term memory."""
    if action == "start":
        result = fix_memory.start_task_state(goal or "ad-hoc task", project=project, task_id=task_id)
    elif action == "note":
        result = fix_memory.append_task_event(event_type="note", value=note, project=project, goal=goal)
    elif action == "verify":
        result = fix_memory.append_task_event(event_type="verified", value=item, project=project, goal=goal)
    elif action == "clear":
        result = fix_memory.clear_task_state()
    else:
        result = fix_memory.load_task_state()
    return json.dumps(result, ensure_ascii=False, indent=2)


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
def search_fixes_vector(query: str, limit: int = 5, include_candidates: bool = False) -> str:
    """Search local fix cases using only TF-IDF vector cosine similarity."""
    results = fix_memory.search_fix_items(
        query, limit, mode="vector", include_candidates=include_candidates
    )
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
