---
name: fix-memory-workflow
description: Use when debugging code errors, build failures, test failures, dependency/path/environment problems, MCP/API/tooling failures, or when the user says to use fix-memory, 错题库, 报错库, 先查历史错误, 修好后写回, or asks to record a fix. This skill makes the agent search the local fix-memory case library before debugging and save a clean repair case after the issue is verified fixed.
---

# Fix Memory Workflow

## Purpose

Use the local fix-memory library as a long-term Memory Hub: search before spending tokens on repeated work, then save only verified or durable knowledge that future agents can reuse.

Memory root:

```text
<absolute-path-to-fix-memory-mcp>
```

## Workflow

1. Before starting, decide whether long-term memory may contain relevant context.
2. Search fix-memory for relevant preference, environment, project, bug, workflow, interview, prompt, or episode memory.
3. When a code error appears, pause before guessing and search using the original error plus framework, command, file path, package/module name, and OS/environment hints.
4. If a similar case is found, explain whether it truly applies and which part will be reused.
5. Debug, answer, or fix normally.
6. Verify with the relevant command or user-observable check.
7. Save or update memory only when it has durable future value.

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
Use `assess_memory` before saving, then `save_memory` to create or update a memory through the write gate.

If MCP is unavailable, use the CLI:

```powershell
cd <absolute-path-to-fix-memory-mcp>
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

Implementation rule: call `assess_memory` before saving when MCP is available. If the decision is `skip`, do not save unless the user explicitly asked. If the decision is `candidate`, save as candidate/episode. If the decision is `save`, save as active memory. `save_memory` should update a similar old memory and increment `occurrence_count` instead of creating duplicates.

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
