from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


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
        env = os.environ.copy()
        env["FIX_MEMORY_ROOT"] = tmp
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
            assert any(tool["name"] == "search_fixes" for tool in tools)
            assert any(tool["name"] == "search_fixes_vector" for tool in tools)
            assert any(tool["name"] == "rebuild_vector_index" for tool in tools)

            write_message(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "save_fix_case",
                        "arguments": {
                            "title": "Python path smoke",
                            "error": "ModuleNotFoundError",
                            "tags": "python,path",
                        },
                    },
                },
            )
            assert "Saved fix case" in read_message(process)["result"]["content"][0]["text"]

            write_message(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "search_fixes",
                        "arguments": {"query": "ModuleNotFoundError path"},
                    },
                },
            )
            assert "Python path smoke" in read_message(process)["result"]["content"][0]["text"]

            write_message(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "search_fixes_vector",
                        "arguments": {"query": "python module path"},
                    },
                },
            )
            assert "Python path smoke" in read_message(process)["result"]["content"][0]["text"]
        finally:
            process.terminate()
            process.wait(timeout=5)

    print("mcp smoke passed")


if __name__ == "__main__":
    main()
