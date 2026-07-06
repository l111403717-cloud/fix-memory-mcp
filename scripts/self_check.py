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
        assert recent and recent[0]["title"].startswith("\u4fee\u590d\u6848\u4f8b\uff1a"), "case title template is not readable Chinese"
        assert recent and 'Python "path" ModuleNotFoundError' in recent[0]["title"], "recent list is empty or wrong"

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

        weak = fix_memory.assess_memory_value("episode", "temporary typo", "typed one wrong letter")
        assert weak["decision"] == "candidate", "weak episode should become candidate"

        strong = fix_memory.assess_memory_value(
            "environment",
            "CCSwitch API relay",
            "User uses local API relay at 127.0.0.1 for model routing",
        )
        assert strong["memory_status"] == "active", "environment memory should be active"

        memory_args = argparse.Namespace(
            memory_type="environment",
            title="CCSwitch API relay",
            content="User uses CCSwitch and a local API relay for model routing.",
            project="demo",
            tags="ccswitch,api,environment",
            evidence="self-check first occurrence",
            source_tool="self-check",
            scope="global",
            sensitivity="private",
            duration_minutes=0,
            verified=False,
            repeat_observed=False,
            user_requested=False,
            force=False,
        )
        first_save = fix_memory.save_memory_entry(memory_args)
        assert first_save["action"] == "created", "first memory save should create"
        first_saved_text = Path(first_save["path"]).read_text(encoding="utf-8")
        assert first_saved_text.splitlines()[0].startswith("\u8bb0\u5fc6\uff1a") or first_saved_text.startswith("---"), "memory body was not written"
        assert "\u8bb0\u5fc6\uff1aCCSwitch API relay" in first_saved_text, "memory body template is not readable Chinese"
        second_save = fix_memory.save_memory_entry(memory_args)
        assert second_save["action"] == "updated", "second memory save should update duplicate"

        saved_text = fix_memory.read_case(Path(second_save["path"]).name)
        assert "occurrence_count: 2" in saved_text, "duplicate update did not increment occurrence_count"

        memory_search = run_cli(memory_root, "search-memory", "CCSwitch API relay", "--memory-type", "environment")
        assert "CCSwitch API relay" in memory_search, "search-memory did not find saved environment memory"

        mcp_assess = fix_memory_mcp.assess_memory(
            memory_type="interview",
            title="Redis why not use",
            content="User could not explain why Redis is not used.",
        )
        assert "save" in mcp_assess, "MCP assess_memory failed"

        mcp_save = fix_memory_mcp.save_memory(
            memory_type="interview",
            title="Redis why not use",
            content="User could not explain why Redis is not used.",
            tags="redis,interview",
        )
        assert "created" in mcp_save, "MCP save_memory failed"

    print("self-check passed")


if __name__ == "__main__":
    main()
