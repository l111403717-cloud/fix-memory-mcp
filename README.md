# Fix Memory MCP

[中文文档](README.zh-CN.md) | [English](README.md)

> Fix Memory does not try to remember everything. It recalls the right information at the right time and lets that context shape agent behavior.

Fix Memory MCP is a local-first Agent Operating Context for AI coding agents.

AI coding agents are fast, but they often behave like they have no memory. They may fix a Python path issue today, then spend tokens rediscovering the same `python.exe`, `venv`, `PATH`, `npm`, build, deployment, or MCP setup issue three days later.

Fix Memory MCP gives Claude Code, Codex, Cursor-like agents, or any MCP client a curated memory of verified fixes. Before guessing, the agent can search your past bug fixes. After a real fix is verified, the agent can save the clean repair as a Markdown case.

It keeps the useful debugging notebook, but V2 also stores user, project, decision, task, and policy context as inspectable Markdown.

```text
new task
  -> analyze intent and scope
  -> assemble budgeted Core Context and untrusted reference memory
  -> retrieve only relevant memory
  -> execute
  -> promote, archive, expire, or supersede memory
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

This is not a "save every transcript" memory.

Fix Memory MCP stores curated operating context and loads only what a task needs. It separates Core Context, project decisions, constraints, temporary task state, and historical fixes.

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
- **Core Context**: carry profile, current focus, active projects, long-term goals, and preferences across windows.
- **Context Assembly**: combine intent, scope, priority, confidence, freshness, and retrieval relevance.
- **Policy resolution**: retained for future trusted Policy input; ordinary writable Markdown never enters it.
- **Dynamic memory budget**: protect Core Context capacity, then reallocate unused Core and inactive-Policy capacity to relevant retrieval within one total context budget.
- **User control**: inspect, correct, promote, archive, expire, supersede, or explicitly delete memory.
- **Hybrid retrieval**: keyword search plus local TF-IDF cosine similarity.
- **Retrieval gate**: decide whether a task actually needs memory search before spending time on retrieval; first-time repo reviews and normal deployment checks should inspect the project directly.
- **Working memory**: keep current task state, matched memories, notes, and verification without writing long-term memory.
- **Semantic retrieval cache**: reuse recent similar retrieval results during a task instead of scanning the memory library again.
- **Curated lifecycle**: first unverified cases become candidates, verified or repeated cases become active, and stale candidates archive after 30 days.
- **Candidate review inbox**: generate a dated local review artifact and batch approve, defer, or archive candidates without interrupting coding.
- **Error observations**: simple errors are counted outside RAG; the second matching occurrence creates a candidate and the third activates it.
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
    users/               # confirmed user facts, skills, and goals
    decisions/           # formal decisions with source and rationale
    tasks/               # cross-window task state
    constraints/         # scoped agent behavior constraints
    prompts/             # reusable prompts
    episodes/            # dated events that may recur
    .runtime/            # local task state and retrieval cache, not long-term memory
  scripts/
    fix_memory.py       # CLI
    fix_memory_mcp.py   # MCP stdio server
    context_engine.py   # Core Context, scope, policy, budget, lifecycle
    vector_search.py    # local TF-IDF vector index
    self_check.py       # CLI + tool self-check
    mcp_smoke.py        # stdio MCP smoke test
    v2_check.py         # V2 end-to-end check
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
python scripts/v2_check.py
python scripts/mcp_smoke.py
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

Use `--verified` only after the repair has passed its relevant check. An unverified
first occurrence is stored as a `candidate`, not returned by default retrieval.

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

Use the retrieval gate before searching. It should skip low-signal first-time tasks and search on hard/repeated issues:

```bash
python scripts/fix_memory.py gate "rename a small local variable"
python scripts/fix_memory.py gate "ModuleNotFoundError python main.py"
```

Use smart search when you want the gate and cache to decide the cheapest path:

```bash
python scripts/fix_memory.py smart-search "CCSwitch API relay" \
  --memory-type environment \
  --context "API relay issue"
```

Track current task working memory:

```bash
python scripts/fix_memory.py task-state start --goal "debug API relay" --project demo
python scripts/fix_memory.py task-state verify --item "nginx -t passed"
python scripts/fix_memory.py task-state show
```

Count a simple error before deciding whether it deserves a full case. The first
occurrence stays in the ignored runtime ledger, the second creates a candidate,
and the third promotes that candidate to active memory:

```bash
python scripts/fix_memory.py observe-error \
  --error "ModuleNotFoundError: No module named worker_app" \
  --project "worker-service" \
  --command "python worker_app/main.py" \
  --file-path "worker_app/main.py"
```

## MCP Server

Run the server:

```bash
python scripts/fix_memory_mcp.py
```

Tools exposed to MCP clients:

- `assemble_context`: assemble the minimal untrusted memory context for a task.
- `manage_memory`: save, inspect, correct, promote, archive, expire, supersede, or delete a memory.
- `maintain_memory_lifecycle`: archive stale candidates and expire elapsed memories.

Search, assessment, write, task-state, and vector-index helpers remain available to the CLI
and internal workflow, but are intentionally not exposed in the Codex MCP tool list.

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

Windows + Codex helper:

```powershell
.\scripts\install_codex_mcp.ps1 -PythonPath D:\python312\python.exe
```

Codex uses the same stdio model and starts the server on demand. Add this to the
global `%USERPROFILE%\.codex\config.toml`, then restart Codex:

```toml
[mcp_servers.fix-memory]
command = 'D:\python312\python.exe'
args = ['C:\Users\<you>\Documents\资料库\fix-memory-mvp\scripts\fix_memory_mcp.py']
startup_timeout_sec = 10

[mcp_servers.fix-memory.env]
FIX_MEMORY_ROOT = 'C:\Users\<you>\Documents\资料库\fix-memory-mvp\data'
```

Run a real stdio handshake before relying on the server:

```powershell
D:\python312\python.exe scripts\mcp_healthcheck.py --python D:\python312\python.exe
```

If the health check fails, continue the coding task without memory retrieval and
use the CLI as a fallback. A broken memory server must not block debugging.

## Agent Prompt

Use [FIX_MEMORY_AGENT_PROMPT.md](FIX_MEMORY_AGENT_PROMPT.md) to teach an agent this loop:

```text
task -> assemble minimal operating context -> inspect the project -> deeper fix retrieval only for hard/repeated errors -> execute -> verify -> curate memory
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

Every write path, including `save_fix_case`, uses the same gate. Unverified first
fixes become `candidate`; verified, repeated, high-cost, or durable configuration
memories become `active`. Default RAG retrieval returns only active memories. Pass
`include_candidates: true` only when investigating recent, unconfirmed work.

Candidates that do not recur for 30 days are archived during retrieval. Repeated
matches update the existing memory and increment `occurrence_count` instead of
creating duplicates. Duplicate matching is scoped to the same project and scope.

Secret-looking content such as API keys, access tokens, passwords, authorization
headers, and cookies is rejected before it reaches disk. `force` cannot override
this protection.

Saved memories include metadata:

```yaml
memory_type: bug / user / preference / environment / workflow / interview / project / decision / task / constraint / prompt / episode
memory_status: candidate / active / archived
occurrence_count: 1
first_seen: 2026-07-06
last_seen: 2026-07-06
confidence: low / medium / high
priority: 0-10
scope: current / task / project / workspace / global
source: user_explicit / observed / inferred / imported / system
execution_level: hard / guarded / soft
reason: why this memory exists
evidence_refs: []
```

Source values in writable Markdown are provenance labels, not authorization credentials.
Agent-facing MCP and CLI writes accept only `observed`, `inferred`, and `imported`. Ordinary
constraints remain untrusted reference memory and never enter Effective Constraints.

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
python scripts/v2_check.py
python scripts/mcp_smoke.py
python scripts/mcp_healthcheck.py
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
