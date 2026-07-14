from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def write_message(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    process.stdin.flush()


def read_message_with_timeout(process: subprocess.Popen[str], timeout_seconds: float) -> dict[str, Any]:
    assert process.stdout is not None
    lines: queue.Queue[str] = queue.Queue(maxsize=1)

    def read_line() -> None:
        lines.put(process.stdout.readline())

    reader = threading.Thread(target=read_line, daemon=True)
    reader.start()
    try:
        line = lines.get(timeout=timeout_seconds)
    except queue.Empty as exc:
        raise TimeoutError(f"MCP did not respond within {timeout_seconds} seconds") from exc
    if not line:
        stderr = process.stderr.read() if process.stderr is not None else ""
        raise RuntimeError(f"MCP server closed stdout: {stderr.strip()}")
    return json.loads(line)


def check_server(
    *,
    python_path: str,
    server_path: Path,
    data_path: Path,
    timeout_seconds: float = 10,
) -> dict[str, object]:
    """Start the stdio server and prove it can initialize before an agent needs it."""
    if not Path(python_path).is_file():
        raise FileNotFoundError(f"Python executable not found: {python_path}")
    if not server_path.is_file():
        raise FileNotFoundError(f"MCP server script not found: {server_path}")

    env = os.environ.copy()
    env["FIX_MEMORY_ROOT"] = str(data_path)
    process = subprocess.Popen(
        [python_path, str(server_path)],
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
                    "clientInfo": {"name": "fix-memory-healthcheck", "version": "1.0"},
                },
            },
        )
        initialize = read_message_with_timeout(process, timeout_seconds)["result"]
        server_name = initialize["serverInfo"]["name"]

        write_message(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        write_message(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = read_message_with_timeout(process, timeout_seconds)["result"]["tools"]
        return {
            "healthy": True,
            "server_name": server_name,
            "tool_count": len(tools),
            "data_path": str(data_path),
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify that fix-memory MCP can start and respond.")
    parser.add_argument("--python", dest="python_path", default=sys.executable)
    parser.add_argument("--server", type=Path, default=ROOT / "scripts" / "fix_memory_mcp.py")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    try:
        result = check_server(
            python_path=args.python_path,
            server_path=args.server.resolve(),
            data_path=args.data.resolve(),
            timeout_seconds=args.timeout,
        )
    except (FileNotFoundError, RuntimeError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"healthy": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
