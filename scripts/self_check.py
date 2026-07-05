from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import fix_memory
import fix_memory_mcp


ROOT = Path(__file__).resolve().parents[1]


def run_cli(memory_root: Path, *args: str) -> str:
    env = os.environ.copy()
    env["FIX_MEMORY_ROOT"] = str(memory_root)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "fix_memory.py"), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fix-memory-check-") as tmp:
        memory_root = Path(tmp)
        os.environ["FIX_MEMORY_ROOT"] = str(memory_root)

        args = argparse.Namespace(
            title='Python "path" ModuleNotFoundError',
            project="demo",
            language="Python",
            framework="",
            command="python main.py",
            error='ModuleNotFoundError: No module named "demo"',
            tags="python,path,venv",
            source_tool="self-check",
            status="fixed",
        )
        path = fix_memory.create_case(args)
        assert path.exists(), "case file was not created"

        found = fix_memory.find_cases("ModuleNotFoundError python path", limit=3)
        assert found, "search did not find created case"
        assert "ModuleNotFoundError" in found[0]["snippet"], "search snippet does not mention the error"

        body = fix_memory.read_case(path.name)
        assert 'ModuleNotFoundError: No module named "demo"' in body, "read_case lost quoted error text"

        recent = fix_memory.list_recent(limit=1)
        assert recent and recent[0]["title"].startswith("修复案例：Python"), "recent list is empty or wrong"

        failed = run_cli(
            memory_root,
            "new",
            "--status",
            "failed",
            "--title",
            "bad path attempt",
            "--error",
            "still failed",
        )
        assert "failed-attempts" in failed, "failed case did not go to failed-attempts"

        save_result = fix_memory_mcp.save_fix_case(
            title="Next.js build suspense",
            project="demo",
            language="TypeScript",
            framework="Next.js",
            command="npm run build",
            error="useSearchParams should be wrapped in a suspense boundary",
            tags="nextjs,build,suspense",
        )
        assert "Saved fix case" in save_result, "MCP save helper failed"

        search_result = fix_memory_mcp.search_fixes(query="useSearchParams suspense", limit=3)
        assert "Next.js build suspense" in search_result, "MCP search helper failed"

        vector_found = fix_memory.find_cases("suspense boundary app router", limit=3, mode="vector")
        assert vector_found, "vector search did not find any cases"
        assert "Next.js build suspense" in vector_found[0]["title"], "vector search did not rank expected case first"

        hybrid_found = fix_memory.find_cases("ModuleNotFoundError virtual environment", limit=3, mode="hybrid")
        assert hybrid_found, "hybrid search did not find any cases"

        index_path = memory_root / ".fix_memory_vectors.json"
        assert index_path.exists(), "vector index was not created"

        vector_cli = run_cli(memory_root, "search", "suspense boundary app router", "--mode", "vector")
        assert "Next.js build suspense" in vector_cli, "vector CLI search failed"

        rebuild_cli = run_cli(memory_root, "rebuild-index")
        assert "documents:" in rebuild_cli, "rebuild-index CLI failed"

        vector_mcp = fix_memory_mcp.search_fixes_vector(query="suspense app router", limit=3)
        assert "Next.js build suspense" in vector_mcp, "MCP vector search helper failed"

        rebuild_mcp = fix_memory_mcp.rebuild_vector_index()
        assert "Rebuilt vector index" in rebuild_mcp, "MCP vector rebuild helper failed"

    print("self-check passed")


if __name__ == "__main__":
    main()
