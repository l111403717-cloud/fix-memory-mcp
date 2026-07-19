from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import fix_memory
import fix_memory_mcp
import mcp_healthcheck


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

        candidate_args = argparse.Namespace(
            title="Transient TypeError while exploring a helper",
            project="demo",
            language="Python",
            framework="",
            command="python helper.py",
            error="TypeError: unsupported operand type",
            tags="python,typeerror",
            source_tool="self-check",
            status="fixed",
            verified=False,
            repeat_observed=False,
            duration_minutes=0,
            user_requested=False,
            sensitivity="private",
            force=False,
        )
        candidate_result = fix_memory.save_fix_case_entry(candidate_args)
        assert candidate_result["action"] == "created", "first unverified fix should be saved as a candidate"
        assert candidate_result["assessment"]["memory_status"] == "candidate", "unverified fix should be a candidate"
        default_fixes = fix_memory.search_fix_items("Transient TypeError helper")
        assert not default_fixes, "default fix retrieval should exclude candidate cases"
        candidate_fixes = fix_memory.search_fix_items(
            "Transient TypeError helper", include_candidates=True
        )
        assert candidate_fixes, "candidate fix retrieval should be opt-in"
        candidate_path = Path(str(candidate_result["path"]))
        candidate_meta, candidate_body = fix_memory.parse_frontmatter(
            candidate_path.read_text(encoding="utf-8")
        )
        candidate_meta["last_seen"] = (dt.datetime.now() - dt.timedelta(days=31)).isoformat()
        fix_memory.write_memory_file(candidate_path, candidate_meta, candidate_body)
        assert fix_memory.archive_stale_candidates(memory_root) == 1, "stale candidates should archive"
        archived_candidate = fix_memory.search_fix_items(
            "Transient TypeError helper", include_candidates=True
        )
        assert all(
            item["path"] != str(candidate_path) for item in archived_candidate
        ), "archived candidates must not be retrieved"

        first_observation = fix_memory.record_error_observation(
            error="ModuleNotFoundError: No module named worker_app",
            project="worker-service",
            command="python worker_app/main.py",
            file_path="worker_app/main.py",
        )
        assert first_observation["action"] == "observed", "first simple error should only be observed"
        assert first_observation["occurrence_count"] == 1, "first observation count is wrong"

        second_observation = fix_memory.record_error_observation(
            error="ModuleNotFoundError: No module named worker_app at line 42",
            project="worker-service",
            command="python worker_app/main.py",
            file_path="worker_app/main.py",
        )
        assert second_observation["action"] == "candidate_created", "second occurrence should create a candidate"
        observed_case_path = Path(str(second_observation["path"]))
        observed_case_meta, _ = fix_memory.parse_frontmatter(
            observed_case_path.read_text(encoding="utf-8")
        )
        assert observed_case_meta["memory_status"] == "candidate", "second occurrence must stay a candidate"

        third_observation = fix_memory.record_error_observation(
            error="ModuleNotFoundError: No module named worker_app at line 99",
            project="worker-service",
            command="python worker_app/main.py",
            file_path="worker_app/main.py",
        )
        assert third_observation["action"] == "activated", "third occurrence should activate the case"
        active_observed_meta, _ = fix_memory.parse_frontmatter(
            observed_case_path.read_text(encoding="utf-8")
        )
        assert active_observed_meta["memory_status"] == "active", "third occurrence did not activate the case"
        assert active_observed_meta["occurrence_count"] == 3, "observed occurrences were not retained"

        secret_observation = fix_memory.record_error_observation(
            error="Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            project="worker-service",
        )
        assert secret_observation["action"] == "skipped", "secret-looking errors must not enter observations"

        save_result = fix_memory_mcp.save_fix_case(
            title="Next.js build suspense",
            project="demo",
            language="TypeScript",
            framework="Next.js",
            command="npm run build",
            error="useSearchParams should be wrapped in a suspense boundary",
            tags="nextjs,build,suspense",
            verified=True,
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

        cross_project_args = argparse.Namespace(**{**vars(memory_args), "project": "other-demo"})
        cross_project_save = fix_memory.save_memory_entry(cross_project_args)
        assert cross_project_save["action"] == "created", "same memory in another project must not merge"

        secret_args = argparse.Namespace(
            **{
                **vars(memory_args),
                "title": "Accidental API key",
                "content": "api_key=sk-1234567890abcdef",
                "force": True,
            }
        )
        secret_result = fix_memory.save_memory_entry(secret_args)
        assert secret_result["action"] == "skipped", "secret-looking content must never be written"

        gate_skip = fix_memory.should_search_memory("rename a local variable in a small helper")
        assert gate_skip["decision"] == "skip", "retrieval gate should skip low-signal tasks"

        first_time_deploy_check = fix_memory.should_search_memory(
            "download this GitHub repo and check whether it is deployed",
            context="first-time repository inspection",
            file_path="package.json",
        )
        assert first_time_deploy_check["decision"] == "skip", "first-time repo/deploy checks should not search memory"

        gate_search = fix_memory.should_search_memory(
            "ModuleNotFoundError when running python main.py",
            command="python main.py",
            file_path="main.py",
        )
        assert gate_search["decision"] == "search", "retrieval gate should search on code errors"

        task_state = fix_memory.start_task_state("debug API relay", project="demo")
        assert task_state["current_task"]["goal"] == "debug API relay", "task state did not start"

        first_smart = fix_memory.smart_search(
            "CCSwitch API relay",
            search_scope="memory",
            memory_type="environment",
            project="demo",
            context="API relay issue",
            force=True,
        )
        assert first_smart["action"] == "searched", "first smart search should hit storage"
        assert first_smart["results"], "first smart search should return saved memory"

        second_smart = fix_memory.smart_search(
            "CCSwitch API relay model routing",
            search_scope="memory",
            memory_type="environment",
            project="demo",
            context="API relay issue",
            force=True,
        )
        assert second_smart["action"] == "cache_hit", "second smart search should use retrieval cache"
        assert second_smart["from_cache"] is True, "smart search cache flag is wrong"

        cache_invalidating_args = argparse.Namespace(
            **{
                **vars(memory_args),
                "title": "CCSwitch API relay verification",
                "content": "User verified the local API relay for model routing.",
                "evidence": "verified after cached search",
            }
        )
        fix_memory.save_memory_entry(cache_invalidating_args)
        cached_after_write = fix_memory.find_cached_retrieval(
            "CCSwitch API relay model routing",
            search_scope="memory",
            memory_type="environment",
            project="demo",
        )
        assert cached_after_write is None, "writes must invalidate retrieval cache"

        state_after_search = fix_memory.load_task_state()
        current_task = state_after_search.get("current_task")
        assert current_task and current_task.get("memory_searched") is True, "task state did not record search"

        gate_cli = run_cli(memory_root, "gate", "ModuleNotFoundError python main.py")
        assert '"decision": "search"' in gate_cli, "gate CLI failed"

        smart_cli = run_cli(
            memory_root,
            "smart-search",
            "CCSwitch API relay",
            "--memory-type",
            "environment",
            "--context",
            "API relay issue",
            "--force",
        )
        assert "CCSwitch API relay" in smart_cli, "smart-search CLI failed"

        task_cli = run_cli(memory_root, "task-state", "verify", "--item", "self-check verified")
        assert "self-check verified" in task_cli, "task-state CLI verify failed"

        review_candidate = json.loads(
            run_cli(
                memory_root,
                "remember",
                "--memory-type",
                "preference",
                "--title",
                "CLI review candidate",
                "--content",
                "User may prefer batch candidate review.",
                "--source",
                "inferred",
            )
        )
        review_candidate_path = Path(str(review_candidate["path"]))
        review_candidate_id = fix_memory.parse_frontmatter(
            review_candidate_path.read_text(encoding="utf-8")
        )[0]["memory_id"]
        review_cli = json.loads(run_cli(memory_root, "memory", "review"))
        assert Path(str(review_cli["path"])).exists(), "candidate review CLI did not write an artifact"
        applied_review = json.loads(
            run_cli(memory_root, "memory", "review", "--approve", review_candidate_id)
        )
        assert applied_review["action"] == "review_applied", "candidate review CLI did not apply approval"
        reviewed_meta, _ = fix_memory.parse_frontmatter(review_candidate_path.read_text(encoding="utf-8"))
        assert reviewed_meta["memory_status"] == "active"
        assert reviewed_meta["source"] == "inferred"
        assert reviewed_meta["promotion_method"] == "batch_review"

        mcp_assess = fix_memory_mcp.assess_memory(
            memory_type="interview",
            title="Redis why not use",
            content="User could not explain why Redis is not used.",
        )
        assert "save" in mcp_assess, "MCP assess_memory failed"

        for authoritative_source in ("user_explicit", "system"):
            try:
                fix_memory_mcp.save_memory(
                    memory_type="constraint",
                    title=f"Rejected {authoritative_source}",
                    content="Agent-facing MCP must reject authoritative sources.",
                    source=authoritative_source,
                )
            except ValueError as exc:
                assert "reject authoritative source" in str(exc)
            else:
                raise AssertionError(f"MCP accepted authoritative source: {authoritative_source}")

        mcp_save = fix_memory_mcp.save_memory(
            memory_type="interview",
            title="Redis why not use",
            content="User could not explain why Redis is not used.",
            tags="redis,interview",
        )
        assert "created" in mcp_save, "MCP save_memory failed"

        health = mcp_healthcheck.check_server(
            python_path=sys.executable,
            server_path=ROOT / "scripts" / "fix_memory_mcp.py",
            data_path=memory_root,
            timeout_seconds=5,
        )
        assert health["healthy"] is True, "health check should initialize the MCP server"
        assert health["server_name"] == "fix-memory", "health check found the wrong MCP server"

    print("self-check passed")


if __name__ == "__main__":
    main()
