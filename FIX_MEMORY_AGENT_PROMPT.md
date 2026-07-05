# Fix Memory Agent Prompt

Copy this into Claude Code, Codex, or another coding agent when you want it to use Fix Memory MCP during debugging.

```text
You must follow my fix-memory workflow.

My local fix-memory project is here:
<absolute-path-to-fix-memory-mcp>

When you help me code, run commands, debug, or fix bugs, use this loop:

1. If there is an error, build failure, test failure, dependency issue, path issue, type error, runtime error, MCP issue, API/tooling issue, or environment problem:
   do not immediately guess.
   Search fix-memory first.

2. If MCP tools are available, prefer:
   - search_fixes
   - search_fixes_vector
   - get_fix_case
   - save_fix_case
   - list_recent_fixes
   - rebuild_vector_index

3. If MCP tools are unavailable, use the CLI:
   cd <absolute-path-to-fix-memory-mcp>
   python scripts/fix_memory.py search "<raw error> <framework> <command> <file path>"

4. Search with multiple clues:
   - original error
   - framework
   - command
   - related file path
   - package/module name
   - operating system or environment hint

5. If a similar case is found:
   explain which historical case was found, whether it really applies, and which part you will reuse.
   Then fix the issue.

6. If nothing is found:
   debug normally.
   Remember that this may become a new case.

7. After a verified fix, save a new case when:
   - the error is real
   - the issue may happen again
   - the fix took meaningful effort
   - it involved paths, dependencies, build/test tooling, encoding, permissions, MCP, API calls, model calls, or environment setup
   - a failed attempt is worth remembering

8. When saving, prefer save_fix_case through MCP. If unavailable, use:
   cd <absolute-path-to-fix-memory-mcp>
   python scripts/fix_memory.py new --title "short title" --project "project" --language "language" --framework "framework" --command "command" --error "raw error" --tags "tag1,tag2"

9. A good case should include:
   - error
   - environment
   - symptoms
   - root cause
   - related files
   - patch summary
   - key diff
   - verification
   - reusable advice
   - failed attempts
   - sensitive-info check

10. Do not store full chats, full terminal logs, full source files, secrets, API keys, cookies, passwords, private account data, or private paths that should not be shared.

Default behavior:
bug -> search fix-memory -> reuse prior knowledge -> fix -> verify -> save clean case.
```
