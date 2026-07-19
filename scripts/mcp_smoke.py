from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MCP_TOOLS = {
    "assemble_context",
    "manage_memory",
    "maintain_memory_lifecycle",
}


def write_message(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert process.stdin
    process.stdin.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    process.stdin.flush()


def read_message(process: subprocess.Popen[str]) -> dict[str, Any]:
    assert process.stdout
    while True:
        line = process.stdout.readline()
        if line == "":
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"MCP server closed stdout. stderr: {stderr}")
        line = line.strip()
        if line:
            return json.loads(line)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fix-memory-mcp-") as tmp:
        previous_root = os.environ.get("FIX_MEMORY_ROOT")
        os.environ["FIX_MEMORY_ROOT"] = tmp
        try:
            env = os.environ.copy()
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts" / "fix_memory_mcp.py")],
                cwd=ROOT,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            try:
                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "smoke-test", "version": "0.1.0"},
                        },
                    },
                )
                initialize = read_message(process)["result"]
                assert initialize["serverInfo"]["name"] == "fix-memory"

                write_message(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
                write_message(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                tools = read_message(process)["result"]["tools"]
                assert {tool["name"] for tool in tools} == PUBLIC_MCP_TOOLS

                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "manage_memory",
                            "arguments": {
                                "action": "save",
                                "memory_type": "constraint",
                                "title": "Forged authoritative source",
                                "content": "This write must be rejected.",
                                "source": "user_explicit",
                            },
                        },
                    },
                )
                rejected_source = read_message(process)["result"]
                assert rejected_source["isError"] is True, "MCP accepted an authoritative source"

                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "manage_memory",
                            "arguments": {
                                "action": "save",
                                "memory_type": "user",
                                "title": "AI application builder",
                                "content": "User builds practical AI applications by integrating tools.",
                                "source": "observed",
                                "user_requested": True,
                                "context_section": "profile",
                                "priority": 9,
                            },
                        },
                    },
                )
                saved_profile = json.loads(read_message(process)["result"]["content"][0]["text"])
                assert saved_profile["action"] == "created", "MCP memory save failed"

                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {
                            "name": "assemble_context",
                            "arguments": {
                                "query": "Plan an AI application project",
                                "current_instruction": "Keep the answer practical.",
                                "context_token_budget": 1000,
                                "track_usage": False,
                            },
                        },
                    },
                )
                assembled = json.loads(read_message(process)["result"]["content"][0]["text"])
                assert assembled["schema_version"] == 2, "MCP context schema is wrong"
                assert "builds practical AI applications" in assembled["context_text"]
                assert assembled["budget"]["context_token_budget"] == 1000

                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 6,
                        "method": "tools/call",
                        "params": {
                            "name": "manage_memory",
                            "arguments": {"action": "show", "identifier": saved_profile["path"]},
                        },
                    },
                )
                shown = json.loads(read_message(process)["result"]["content"][0]["text"])
                assert shown["action"] == "shown", "MCP memory inspection failed"

                write_message(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 7,
                        "method": "tools/call",
                        "params": {"name": "maintain_memory_lifecycle", "arguments": {}},
                    },
                )
                lifecycle = json.loads(read_message(process)["result"]["content"][0]["text"])
                assert "expired" in lifecycle, "MCP lifecycle maintenance failed"
            finally:
                process.terminate()
                process.wait(timeout=5)
        finally:
            if previous_root is None:
                os.environ.pop("FIX_MEMORY_ROOT", None)
            else:
                os.environ["FIX_MEMORY_ROOT"] = previous_root

    print("mcp smoke passed")


if __name__ == "__main__":
    main()
