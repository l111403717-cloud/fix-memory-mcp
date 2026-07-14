# Fix Memory Agent Prompt

Copy this into Claude Code, Codex, or another coding agent when you want it to use Fix Memory as a long-term memory system.

```text
You must follow my fix-memory long-term memory workflow.

My local fix-memory project is here:
<absolute-path-to-fix-memory-mcp>

Do not treat fix-memory as only a bug notebook. Treat it as a Memory Hub.

Before starting a task, do not automatically read the whole memory library.
For first-time repo reviews, GitHub downloads, normal code reading, or deployment checks without a concrete error, inspect the project directly and skip memory retrieval.
Use a retrieval gate only when there is a hard error, repeated issue, explicit user request, or known local environment/API/path problem.

1. Preference Memory: user habits, tool preferences, model/API preferences.
2. Environment Memory: local OS, paths, ports, Python/Node, Claude/Codex/CCSwitch setup.
3. Project Memory: project design decisions and architecture reasons.
4. Bug Memory: historical errors and verified fixes.
5. Workflow Memory: workflows repeated more than twice.
6. Interview Memory: interview questions the user missed or learning weak spots.
7. Episode Memory: specific events that may repeat later.

Use working memory for the current task:
   - task_state stores the current goal, whether memory has already been searched, matched memory ids, notes, and verification.
   - retrieval cache stores recent similar search results.
   - These are temporary runtime files, not long-term memories.

If MCP tools are available, prefer `should_search_memory` or `smart_search_memory` before raw search:
   - should_search_memory decides whether retrieval is worth it.
   - smart_search_memory uses the retrieval gate and semantic cache before searching.
   - task_state records current task state and prevents repeated retrieval in the same task.

When there is a code error, build failure, test failure, dependency/path/environment issue, MCP issue, API/tooling issue, or model-call issue:

1. Do not immediately guess.
2. Run the retrieval gate or smart search; search fix-memory only when the gate says search.
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
   - should_search_memory
   - smart_search_memory
   - task_state
   - get_fix_case
   - save_fix_case
   - list_recent_fixes
   - rebuild_vector_index

If MCP tools are unavailable, use the CLI:
   cd <absolute-path-to-fix-memory-mcp>
   python scripts/fix_memory.py gate "<raw error> <framework> <command> <file path>"
   python scripts/fix_memory.py smart-search "<raw error> <framework> <command> <file path>" --scope fixes --mode hybrid

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

Before saving, call `assess_memory` when available. If it says `skip`, do not save.
If it says `candidate`, save it as a candidate; if it says `save`, save it as active
memory. Candidates are not returned by default RAG retrieval and archive after 30
days without recurrence. `save_memory` and `save_fix_case` should update a similar
memory in the same project and scope, incrementing `occurrence_count` rather than
creating duplicates. Never send API keys, tokens, passwords, authorization headers,
or cookies to either write tool.

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
task -> direct project inspection by default -> retrieval gate only for hard/repeated/explicit memory cases -> skip/search/cache -> reuse prior knowledge if relevant -> fix/answer -> verify -> save only valuable long-term memory.
```
