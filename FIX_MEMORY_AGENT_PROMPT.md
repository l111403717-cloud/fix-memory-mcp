# Fix Memory Agent Prompt

Copy this into Claude Code, Codex, or another coding agent when you want it to use Fix Memory as a long-term memory system.

```text
You must follow my fix-memory long-term memory workflow.

My local fix-memory project is here:
<absolute-path-to-fix-memory-mcp>

Do not treat fix-memory as only a bug notebook. Treat it as a Memory Hub.

Before starting a task, decide whether to search long-term memory:

1. Preference Memory: user habits, tool preferences, model/API preferences.
2. Environment Memory: local OS, paths, ports, Python/Node, Claude/Codex/CCSwitch setup.
3. Project Memory: project design decisions and architecture reasons.
4. Bug Memory: historical errors and verified fixes.
5. Workflow Memory: workflows repeated more than twice.
6. Interview Memory: interview questions the user missed or learning weak spots.
7. Episode Memory: specific events that may repeat later.

When there is a code error, build failure, test failure, dependency/path/environment issue, MCP issue, API/tooling issue, or model-call issue:

1. Do not immediately guess.
2. Search fix-memory first.
3. If a similar memory is found, explain whether it truly applies and which part you will reuse.
4. Fix the issue.
5. Verify the fix.
6. Save the useful long-term memory in the right category.

If MCP tools are available, prefer:
   - search_memory
   - assess_memory
   - save_memory
   - search_fixes
   - search_fixes_vector
   - get_fix_case
   - save_fix_case
   - list_recent_fixes
   - rebuild_vector_index

If MCP tools are unavailable, use the CLI:
   cd <absolute-path-to-fix-memory-mcp>
   python scripts/fix_memory.py search "<raw error> <framework> <command> <file path>" --mode hybrid

Search with multiple clues:
   - original error
   - framework
   - command
   - related file path
   - package/module name
   - operating system or environment hint

At the end of each task, decide whether this produced long-term value:

- Will it be useful in the future?
- Does it reflect the user's long-term habits?
- Is it environment or API configuration?
- Has it happened more than twice?
- Is it a question/knowledge point the user could not answer?
- Will it help the next agent avoid wasted work?

Only save if the answer is yes. Prefer updating/merging an existing memory over creating duplicates.

Before saving, call `assess_memory` when available. If it says `skip`, do not save unless the user explicitly asked to remember it. If it says `candidate`, save as candidate/episode. If it says `save`, save as active memory. `save_memory` should update a similar old memory and increment occurrence_count instead of creating duplicates.

When saving, prefer save_fix_case through MCP. If unavailable, use:
   cd <absolute-path-to-fix-memory-mcp>
   python scripts/fix_memory.py new --title "short title" --project "project" --language "language" --framework "framework" --command "command" --error "raw error" --tags "tag1,tag2"

A good saved memory should include:
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

Do not store full chats, full terminal logs, full source files, secrets, API keys, cookies, passwords, private account data, or private paths that should not be shared.

Default behavior:
task/error -> search memory -> reuse prior knowledge -> fix/answer -> verify -> save only valuable long-term memory.
```
