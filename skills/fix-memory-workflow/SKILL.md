---
name: fix-memory-workflow
description: Use when debugging code errors, build failures, test failures, dependency/path/environment problems, MCP/API/tooling failures, or when the user says to use fix-memory, 错题库, 报错库, 先查历史错误, 修好后写回, or asks to record a fix. This skill makes the agent search the local fix-memory case library before debugging and save a clean repair case after the issue is verified fixed.
---

# Fix Memory Workflow

## Purpose

Use the local fix-memory library as a code error notebook: search before spending tokens on a repeated bug, then save the verified fix so future agents can reuse it.

Memory root:

```text
<absolute-path-to-fix-memory-mcp>
```

## Workflow

1. When a code error appears, pause before guessing.
2. Search fix-memory using the original error plus framework, command, file path, package/module name, and OS/environment hints.
3. If a similar case is found, explain whether it truly applies and which part will be reused.
4. Debug and fix the issue normally.
5. Verify with the relevant command or user-observable check.
6. Save a clean fix case when the issue is real, repeatable, costly, environment-related, or likely useful later.

## Preferred Tools

If MCP tools are available, use them first:

```text
search_fixes
search_fixes_vector
get_fix_case
save_fix_case
list_recent_fixes
rebuild_vector_index
```

Use `search_fixes` by default because it performs hybrid keyword + local vector retrieval. Use `search_fixes_vector` when the error wording differs from the saved case and semantic similarity matters more than exact tokens.

If MCP is unavailable, use the CLI:

```powershell
cd <absolute-path-to-fix-memory-mcp>
python scripts\fix_memory.py search "报错关键词 框架 命令 文件路径"
```

The CLI defaults to hybrid search. Use explicit modes when needed:

```powershell
python scripts\fix_memory.py search "报错关键词 框架 命令 文件路径" --mode hybrid
python scripts\fix_memory.py search "报错关键词 框架 命令 文件路径" --mode vector
python scripts\fix_memory.py search "报错关键词 框架 命令 文件路径" --mode keyword
```

To create a new case without MCP:

```powershell
cd <absolute-path-to-fix-memory-mcp>
python scripts\fix_memory.py new --title "错误标题" --project "项目名" --language "语言" --framework "框架" --command "触发命令" --error "原始报错" --tags "标签1,标签2"
```

After creating the Markdown file, fill in root cause, related files, patch summary, key diff, verification, reusable advice, failed attempts, and sensitive-info check.

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
