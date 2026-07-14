---
name: fix-memory-workflow
description: Use when debugging real code errors, build/test failures, repeated dependency/path/environment problems, repeated MCP/API/tooling failures, or when the user says to use fix-memory, 错题库, 报错库, 先查历史错误, 修好后写回, or asks to record a fix. This skill makes the agent decide whether memory retrieval is needed before debugging; it must not search memory by default for first-time repo reviews, downloads, or normal deployment checks.
---

# Fix Memory Workflow

## Purpose

Use the local fix-memory library as a long-term Memory Hub: decide whether retrieval is needed, reuse cached retrieval when possible, then save only verified or durable knowledge that future agents can reuse.

Memory root:

```text
<absolute-path-to-fix-memory-mcp>
```

## Workflow

1. Before starting, do not search memory automatically.
2. If the task is a first-time repo review, GitHub download, normal code reading, or deployment check without a concrete error, inspect the project directly and skip memory retrieval.
3. Use a retrieval gate only when there is a hard error, repeated issue, explicit user request, or known local environment/API/path problem.
4. Use smart search when the gate says search so the agent can reuse recent cached retrieval results.
5. Search fix-memory for relevant preference, environment, project, bug, workflow, interview, prompt, or episode memory only after the gate says search.
6. When a code error appears, pause before guessing and search using the original error plus framework, command, file path, package/module name, and OS/environment hints.
7. If a similar case is found, explain whether it truly applies and which part will be reused.
8. Debug, answer, or fix normally.
9. Verify with the relevant command or user-observable check.
10. Save or update memory only when it has durable future value.

## Memory Types

- `bug`: verified errors, root causes, fixes, and validation.
- `preference`: user habits, tool preferences, model/API preferences, naming/style preferences.
- `environment`: OS, paths, ports, local services, Python/Node, Claude/Codex/CCSwitch/API setup.
- `project`: project decisions, architecture reasons, tradeoffs, constraints.
- `workflow`: repeated procedures that happened more than twice.
- `interview`: missed interview questions, weak knowledge points, simulation results.
- `prompt`: reusable prompts and agent instructions.
- `episode`: dated events that may recur but are not yet stable rules.

## Preferred Tools

If MCP tools are available, use them first:

```text
search_memory
should_search_memory
smart_search_memory
task_state
assess_memory
save_memory
search_fixes
search_fixes_vector
get_fix_case
save_fix_case
list_recent_fixes
rebuild_vector_index
```

Use `search_memory` for preference, environment, project, workflow, interview, prompt, or episode memory.
Use `search_fixes` by default for bug/fix cases because it performs hybrid keyword + local TF-IDF vector retrieval.
Use `search_fixes_vector` when the error wording differs from the saved case and semantic similarity matters more than exact tokens.
Use `should_search_memory` before retrieval when the task is not clearly a hard error, repeated issue, explicit memory request, or known local environment/API/path problem.
Use `smart_search_memory` when available because it combines the retrieval gate with recent semantic retrieval cache.
Use `task_state` to track the current task goal, prior searches, matched memory, notes, and verification without writing long-term memory.
Use `assess_memory` before saving, then `save_memory` to create or update a memory through the write gate.

If MCP startup, tool invocation, or retrieval fails, do not block the coding task.
Inspect and debug the project directly, then use the CLI fallback after the task:

```powershell
D:\python312\python.exe scripts\fix_memory.py smart-search "<error framework command file path>" --scope fixes --mode hybrid
```

Important skip rule: do not call `search_memory`, `search_fixes`, or `smart_search_memory` just because the task mentions GitHub, deployment, repository, package.json, nginx, Docker, or API. For first-time inspection, read the local project first. Search memory only after a concrete failure/repeated pattern appears or the user explicitly asks.

If MCP is unavailable, use the CLI:

```powershell
cd <absolute-path-to-fix-memory-mcp>
python scripts\fix_memory.py gate "报错关键词 框架 命令 文件路径"
python scripts\fix_memory.py smart-search "报错关键词 框架 命令 文件路径" --scope fixes --mode hybrid
python scripts\fix_memory.py search "报错关键词 框架 命令 文件路径" --mode hybrid
python scripts\fix_memory.py search-memory "偏好 环境 项目 决策 关键词" --memory-type environment
```

To create a new case without MCP:

```powershell
cd <absolute-path-to-fix-memory-mcp>
python scripts\fix_memory.py new --title "错误标题" --project "项目名" --language "语言" --framework "框架" --command "触发命令" --error "原始报错" --tags "标签1,标签2"
```

To save long-term memory without MCP:

```powershell
cd <absolute-path-to-fix-memory-mcp>
python scripts\fix_memory.py remember --memory-type environment --title "记忆标题" --content "长期有用的内容" --tags "标签1,标签2"
```

## Write Gate

Before saving, ask:

- Will this be useful in the future?
- Does it reflect the user's long-term habits?
- Is it environment or API configuration?
- Has it happened more than twice?
- Is it a missed interview/learning point?
- Will it help the next agent avoid wasted work?

Save when at least one strong reason is true. Otherwise do not save. Prefer merging/updating existing memory over creating duplicates.

Implementation rule: call `assess_memory` before saving when MCP is available. If the decision is `skip`, do not save. If the decision is `candidate`, save as candidate/episode. If the decision is `save`, save as active memory. Default retrieval returns only active memory; opt into candidates only for recent unconfirmed work. Candidates archive after 30 days without recurrence. `save_memory` and `save_fix_case` update similar memory only within the same project and scope, incrementing `occurrence_count` instead of creating duplicates. Never write secrets, API keys, tokens, passwords, authorization headers, or cookies.

## Search Query Pattern

Build searches from multiple clues, not just the user question:

```text
<raw error> <framework> <command> <file path> <package/module> <OS/env>
```

Examples:

```text
ModuleNotFoundError Python venv Windows python main.py
Next.js useSearchParams suspense npm run build app router
Claude Code MCP Failed to connect stdio FastMCP Windows
```

## Save Rules

Save a case when:

- The fix was verified.
- The error may happen again.
- The issue involved paths, dependencies, build/test tooling, encoding, permissions, MCP, API calls, model calls, or environment setup.
- A failed attempt is important enough to prevent repeated wasted work.

Do not save raw full chats, full terminal logs, full project files, secrets, tokens, API keys, cookies, passwords, or private account data.

## Case Quality

A useful saved case should answer:

- What was the exact error?
- What project/environment did it happen in?
- What was the root cause?
- What changed?
- How was it verified?
- What should future agents check first?
- What failed attempts should not be repeated?
