# Fix Memory MCP

> Stop debugging the same error twice.

Fix Memory MCP is a local-first developer memory system for bugs.

AI coding agents are fast, but they often behave like they have no memory. They may fix a Python path issue today, then spend tokens rediscovering the same `python.exe`, `venv`, `PATH`, `npm`, build, deployment, or MCP setup issue three days later.

Fix Memory MCP gives Claude Code, Codex, Cursor-like agents, or any MCP client a curated memory of verified fixes. Before guessing, the agent can search your past bug fixes. After a real fix is verified, the agent can save the clean repair as a Markdown case.

In plain English: it is a **debugging notebook for agents**.

```text
error appears
  -> search previous fixes
  -> reuse the closest repair pattern
  -> fix and verify
  -> save the new case
  -> future agents get smarter
```

## Why This Exists

AI agents are fast, but they often waste tokens rediscovering the same environment, dependency, build, path, MCP, or deployment bug.

Fix Memory MCP gives them a small long-term memory:

- Local Markdown cases you can read and edit
- Hybrid keyword + TF-IDF vector search
- Failed-attempt notes so agents do not repeat dead ends
- A stdio MCP server with tools for search, read, save, recent, and index rebuild
- No cloud database, no external embedding API, no required network access

## What Makes It Different

This is not a general "remember everything I said" memory.

Many AI memory features store every detail. Fix Memory MCP is stricter: it stores curated long-term memory that helps future agents avoid repeated work.

It does not embed every chat transcript. It saves useful, durable memory such as:

- the exact error
- the project and environment context
- the root cause
- the patch summary
- the verification command and result
- the failed attempts that should not be repeated
- user preferences and tool/API habits
- environment facts such as paths, ports, Python/Node, Claude/Codex/CCSwitch setup
- interview or learning weak spots
- repeated workflows and dated episodes that may recur

That curation step matters. If every conversation is saved, the memory becomes noisy. If only durable memory is saved, the memory becomes a useful agent asset.

## Why Markdown Instead of SQLite

Fix cases are stored as Markdown because the data is developer knowledge, not ordinary business data.

Markdown is a good fit because it is:

- easy for humans to read and edit
- easy for AI agents to read
- friendly to Git, diff, merge, review, and sync
- portable across machines and tools
- transparent when a saved case contains private paths or sensitive details

SQLite may become useful later for very large collections, full-text search, or team usage. For a personal developer memory system, Markdown keeps the memory inspectable and versionable.

## Why TF-IDF Instead of Embeddings

Many bug fixes are keyword-heavy. Errors often contain strong tokens such as:

- `ModuleNotFoundError`
- `python.exe`
- `venv`
- `PATH`
- `pip`
- `npm`
- `cargo`
- `MCP`
- `ECONNREFUSED`

TF-IDF is cheap, local, fast, private, and good enough for this kind of error retrieval. No embedding API key is required, and private bug history does not leave the machine.

Embedding search can still be added later when the case library grows or when semantic matching becomes more important.

## What It Is Good At

- Repeated build failures
- Python / Node / Windows path problems
- MCP connection issues
- Dependency and virtual environment mistakes
- Framework-specific errors
- Deployment and service startup fixes
- Recording failed attempts as "do not try this again"

## Features

- **Local-first memory**: cases live under `data/` as Markdown files.
- **MCP server**: expose fix memory to AI coding tools through stdio.
- **Hybrid retrieval**: keyword search plus local TF-IDF cosine similarity.
- **Zero external AI dependency**: no OpenAI/Anthropic API key needed.
- **Readable case format**: root cause, patch, verification, reusable advice.
- **Privacy by default**: real fix cases are ignored by Git unless you choose to share them.

## Project Layout

```text
fix-memory-mcp/
  data/
    fixes/              # your private fixed cases
    failed-attempts/    # private "do not repeat" notes
    commands/           # private useful command notes
    preferences/         # user habits, tools, model/API preferences
    environments/        # OS, paths, ports, Python/Node, Claude/Codex/CCSwitch
    workflows/           # repeated procedures
    interviews/          # interview misses and learning weak spots
    projects/            # project decisions and tradeoffs
    prompts/             # reusable prompts
    episodes/            # dated events that may recur
  scripts/
    fix_memory.py       # CLI
    fix_memory_mcp.py   # MCP stdio server
    vector_search.py    # local TF-IDF vector index
    self_check.py       # CLI + tool self-check
    mcp_smoke.py        # stdio MCP smoke test
  skills/
    fix-memory-workflow/
      SKILL.md          # optional Codex/agent skill instructions
  templates/
    fix-case.md         # case template
```

## Quick Start

```bash
git clone https://github.com/l111403717-cloud/fix-memory-mcp.git
cd fix-memory-mcp
python -m pip install mcp
python scripts/self_check.py
```

Create your first case:

```bash
python scripts/fix_memory.py new \
  --title "Python ModuleNotFoundError from wrong working directory" \
  --project "demo-api" \
  --language "Python" \
  --framework "FastAPI" \
  --command "python app/main.py" \
  --error "ModuleNotFoundError: No module named app" \
  --tags "python,path,fastapi,windows"
```

Search it later:

```bash
python scripts/fix_memory.py search "ModuleNotFoundError FastAPI working directory"
```

Search modes:

```bash
python scripts/fix_memory.py search "MCP failed stdio" --mode hybrid
python scripts/fix_memory.py search "MCP failed stdio" --mode keyword
python scripts/fix_memory.py search "MCP failed stdio" --mode vector
```

Rebuild the local vector index:

```bash
python scripts/fix_memory.py rebuild-index
```

Assess whether something deserves long-term memory:

```bash
python scripts/fix_memory.py assess \
  --memory-type environment \
  --title "API relay setup" \
  --content "User uses CCSwitch and a local API relay for model routing."
```

Save or update long-term memory through the write gate:

```bash
python scripts/fix_memory.py remember \
  --memory-type environment \
  --title "API relay setup" \
  --content "User uses CCSwitch and a local API relay for model routing." \
  --tags "ccswitch,api,environment"
```

Search long-term memory with an optional type filter:

```bash
python scripts/fix_memory.py search-memory "API relay CCSwitch" --memory-type environment
```

## MCP Server

Run the server:

```bash
python scripts/fix_memory_mcp.py
```

Tools exposed:

- `save_fix_case`
- `search_fixes`
- `search_fixes_vector`
- `search_memory`
- `assess_memory`
- `save_memory`
- `get_fix_case`
- `list_recent_fixes`
- `rebuild_vector_index`

Generic MCP config:

```json
{
  "mcpServers": {
    "fix-memory": {
      "command": "python",
      "args": [
        "/absolute/path/to/fix-memory-mcp/scripts/fix_memory_mcp.py"
      ],
      "env": {
        "FIX_MEMORY_ROOT": "/absolute/path/to/fix-memory-mcp/data"
      }
    }
  }
}
```

Windows + Claude Code helper:

```powershell
cd path\to\fix-memory-mcp
.\scripts\install_claude_mcp.ps1
```

## Agent Prompt

Use [FIX_MEMORY_AGENT_PROMPT.md](FIX_MEMORY_AGENT_PROMPT.md) to teach an agent this loop:

```text
bug -> search memory -> repair -> verify -> save the clean fix
```

## Case Quality Rules

## Write Gate

Do not save every small event. Before saving, ask:

- Will this be useful in the future?
- Did it repeat more than twice?
- Does it reflect a user habit?
- Is it environment/API/path/account/tool configuration?
- Was the fix verified?
- Will it help the next agent avoid wasted work?

Strong save signals:

- repeated at least twice
- took more than 10 minutes
- involves environment/API/path/account/tool configuration
- user explicitly said "remember"
- missed interview/learning point
- important project decision

Uncertain first occurrences can be saved as `candidate` or `episode`. Repeated matches update the existing memory and increment `occurrence_count` instead of creating duplicates.

Saved memories include metadata:

```yaml
memory_type: bug / preference / environment / workflow / interview / project / prompt / episode
memory_status: candidate / active / archived
occurrence_count: 1
first_seen: 2026-07-06
last_seen: 2026-07-06
confidence: low / medium / high
```

A useful case should include:

- Exact error
- Project/environment context
- Root cause
- Related files
- What changed
- Verification command/result
- Reusable advice
- Failed attempts
- Sensitive-info check

Do not save full chats, full terminal logs, secrets, API keys, cookies, passwords, private account data, or private source files.

## Self Check

```bash
python scripts/self_check.py
python scripts/mcp_smoke.py
```

## Roadmap

- Optional SQLite + FTS5 index for very large case libraries
- Optional embedding backends
- Better case sanitizer
- Git diff capture after verification
- Agent-friendly install command for more clients
- Web UI for browsing fix cases

## License

MIT
