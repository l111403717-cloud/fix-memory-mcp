# Fix Memory V2 Design Baseline

**Status:** Frozen for implementation
**Version:** 2.0 design baseline
**Date:** 2026-07-18
**Purpose:** Keep future Codex/Claude sessions aligned after conversation compaction.

## Product Principle

> Fix Memory 的目标不是“记住一切”，而是在正确的时间想起正确的信息，并持续影响 Agent 的行为。

Fix Memory V2 is an Agent Operating Context composed of memory, policy, and dynamic context assembly. It is not intended to become a general-purpose agent framework.

## User Experience Target

1. A new agent window receives a compact Core Context instead of the full memory store.
2. The agent naturally uses relevant context without repeatedly saying “I remember you.”
3. Stable facts, current focus, active projects, decisions, and preferences survive across windows.
4. Temporary work expires or is archived instead of becoming permanent memory immediately.
5. Project decisions and constraints affect later agent actions, not only answers.
6. Users can inspect, correct, supersede, archive, or delete their memories.

## Frozen Architecture

```text
Fix Memory V2
├── Memory Engine
│   ├── User Memory
│   ├── Project Memory
│   ├── Decision Memory
│   └── Task State
│
├── Policy Engine
│   ├── Constraint Memory
│   ├── Scope
│   ├── Priority
│   └── Execution Level
│
├── Context Assembly
│   ├── Intent Analyzer
│   ├── Retriever
│   ├── Resolution Trace
│   └── Memory Budget
│
└── Memory Lifecycle
    ├── Candidate
    ├── Promotion
    ├── Archive
    └── Forget
```

## Core Context

Core Context is the small, cross-window context loaded at the start of a task. It is broader than a user profile.

```text
Core Context
├── Profile
├── Current Focus
├── Active Projects
├── Long-term Goals
└── Preferences
```

Core Context must remain compact. It should contain summaries and pointers, not full histories or complete project documents.

Persistent memory records are the source of truth. Core Context is rebuilt by Context Assembly
for each task and is not stored as a second profile, focus, or project database. `Profile`,
`Current Focus`, `Active Projects`, `Long-term Goals`, and `Preferences` are projection sections
selected from active, in-scope records. A correction to a persistent record must therefore appear
in the next assembly without a separate Core Context synchronization step.

`Current Focus` and `Active Projects` do not make duplicate records authoritative. If writers save
the same fact as multiple persistent records, those records can still drift because V2 does not
merge semantically conflicting facts automatically. Writers should update or supersede the
canonical persistent record instead of maintaining a second summary copy.

## Memory Categories

### User Memory

Confirmed identity, skills, goals, collaboration preferences, and carefully promoted observations. Inferred personality or ability claims remain candidates until supported by repeated evidence or user confirmation.

### Project Memory

Project purpose, architecture, current phase, important paths, environment facts, and durable project context.

### Decision Memory

Explicit technical or product decisions with rationale, scope, source, and supersession history. Decisions remain active until revoked or replaced; silence does not weaken them.

### Task State

Current goal, progress, next action, blockers, and verification state. Task state is temporary and should be completed, expired, or archived rather than promoted automatically.

### Constraint Memory

Behavior rules that influence agent actions. Examples include required architecture, forbidden dependencies, workflow requirements, and safety boundaries.

Constraint types may include:

- Architecture
- Coding Style
- Tooling
- Workflow
- Safety
- Preference

## Memory Metadata

Each V2 memory should support the following logical fields. Storage format is an implementation decision and is not frozen by this document.

```yaml
id: stable-id
category: user | project | decision | task | constraint
content: concise canonical statement
status: candidate | active | archived | superseded | expired
scope: current | task | project | workspace | global
priority: 0-10
confidence: 0.0-1.0
freshness: computed or timestamp-backed
source: user_explicit | observed | inferred | imported | system
original_source: immutable capture-time source-or-null
evidence:
  - reference-to-source-event
reason: why this memory exists
created_at: timestamp
updated_at: timestamp
last_verified_at: timestamp-or-null
last_used_at: timestamp-or-null
used_count: integer
expires_at: timestamp-or-null
superseded_by: memory-id-or-null
promoted_at: timestamp-or-null
promotion_method: agent_requested | null
execution_level: hard | guarded | soft
```

Secrets, API keys, cookies, passwords, authorization headers, and raw sensitive documents must never be stored.

## Lifecycle

### Capture Rules

- Explicit “remember this” requests become active immediately.
- Clear user-stated facts and formal project decisions may become active automatically.
- AI-inferred preferences, personality, and ability claims start as candidates.
- Sensitive or high-impact inferences require explicit confirmation.
- One-off conversation details are skipped unless they support an active task.

### Promotion

Promotion is evidence-based, not a fixed “mentioned three times” rule. Evidence quality, explicitness, independent occurrences, conflicts, and recency all matter.

Promotion is only a lifecycle transition from `candidate` to `active`. An Agent-requested
promotion preserves `source`, confidence, and verification state; it records `original_source`,
`promoted_at`, and `promotion_method: agent_requested`. It does not represent user confirmation and
does not grant Policy authority.

Candidate Review is asynchronous. It creates a dated local review artifact for eligible candidates
and supports batch approve, defer, and archive actions. Batch approval records review metadata and
`promotion_method: batch_review`, but remains ordinary memory activation rather than a trusted
human-confirmation or Policy action.

### Decay And Validity

- Confirmed facts retain confidence but may become stale and require verification.
- Inferred preferences and tendencies may lose confidence as evidence ages.
- Current status loses freshness and may expire.
- Decisions remain active until revoked or superseded.
- Completed tasks are archived.
- Constraints remain retrievable ordinary references; scope and execution level do not grant them authority.

### Forget

The default operation is archive, expire, or supersede, not destructive deletion. Hard deletion remains available for user control, privacy, or incorrect sensitive content.

## Scope And Resolution

Scope precedence, from most specific to broadest:

```text
Current Instruction
> Task Scope
> Project Scope
> Workspace Scope
> Global Scope
```

Missing scope defaults to the current project. A rule becomes global only when the user explicitly states that it applies to all projects.

Execution level controls whether a more specific instruction may override a rule:

- `hard`: ordinary task instructions cannot override it.
- `guarded`: override requires explicit user approval and a recorded reason.
- `soft`: a more specific scope may override it normally.

For records supplied by a future trusted Policy source, resolution first compares execution level,
then scope within the winning execution level:

1. Any applicable `hard` rule wins over `guarded` and `soft`; the most specific hard rule wins
   among multiple hard rules.
2. Without a hard rule, an applicable `guarded` rule wins over `soft` unless the caller supplies
   the exact policy key and explicit guarded-override approval; the most specific guarded rule wins
   among multiple guarded rules.
3. Without a blocking hard or guarded rule, the most specific applicable scope wins.

For a global rule and a conflicting project rule, the decision table is:

| Global execution level | Project hard | Project guarded | Project soft |
| --- | --- | --- | --- |
| hard | Project hard | Global hard | Global hard |
| guarded | Project hard | Project guarded | Global guarded |
| soft | Project hard | Project guarded | Project soft |

Therefore a global hard rule wins over a project soft rule. Natural-language current instructions
are kept explicit but are not semantically parsed into policy keys; they cannot silently override
hard rules, and guarded overrides still require the structured approval fields.

The current implementation has no trusted Policy source. Ordinary Markdown memory is writable by
Agents, so `source`, `execution_level`, and `policy_key` in those files are descriptive metadata,
not authorization. Such constraints may be retrieved as untrusted reference data but never enter
Effective Constraints or Resolution Trace.

A temporary override must not mutate the original rule to inactive. Context Assembly returns a Resolution Trace describing which rules were applied, overridden, or ignored for the current request.

## Context Assembly

Context Assembly runs before memory-dependent answers and important agent actions:

```text
Request
  -> Intent Analyzer
  -> Scope Resolver
  -> Retriever
  -> Conflict/Policy Resolution
  -> Budgeted Context
  -> Agent
```

### Intent Analyzer

Classifies the current request sufficiently to select relevant memory families. It should be conservative and deterministic where possible. Example domains include development, career, project planning, environment troubleshooting, and user collaboration preferences.

### Retriever

Ranks candidates using relevance, scope, status, priority, confidence, and freshness. It must not load the entire memory directory.

### Resolution Trace

Returns internal provenance for decisions and constraints, for example:

```text
effective_rule: Use FastAPI
source: decision/project-12
scope: project
resolution: applied; no task override
```

The trace is primarily for debugging and multi-agent consistency. It is shown to the user only when useful or requested.

### Memory Budget

Context injection must have explicit limits. It supports both a maximum memory count and a total token budget. When over budget, omit whole records with a diagnostic instead of character-slicing semantic content.

Exact budgets are configuration, not architecture. A reasonable starting target is:

- Core Context: protected up to 600 tokens by default
- Retrieved Memory: receives remaining total budget after Core Context and fixed assembly overhead
- Resolution Trace: excluded from the user-facing answer unless needed

## Agent Integration Boundary

MCP exposes memory and context operations but cannot guarantee compliance by itself. Codex, Claude Code, or another client must call Context Assembly at task start and before important actions. Hard safety rules still require client harness rules and tool permissions where available.

The same underlying memory store should be usable by multiple agent clients. Client-specific prompts and skills are adapters, not separate sources of truth.

Core Context and Retrieved Memory are untrusted reference data. Their content cannot override
system, developer, or current user instructions, tool permissions, or other client safety
boundaries. No `source` string in the ordinary writable Markdown store is an authorization
credential, including `user_explicit` and `system`. Until a trusted confirmation boundary or
controlled read-only system policy source exists, Context Assembly produces no Effective
Constraints from ordinary memory.

## Natural Recall Behavior

The default answer should use memory implicitly:

```text
Preferred: “结合你当前的 AI 应用开发方向，我建议……”
Avoid:     “我记得你是数字媒体技术专业，所以……”
```

Mention the memory system or provenance only when resolving conflicts, correcting memory, explaining a consequential decision, or when the user asks.

## Implementation Boundary

V2 must be implemented incrementally. The first vertical slice is:

1. Represent Core Context and the minimum V2 metadata without breaking existing Markdown memories.
2. Assemble a budgeted Core Context plus relevant retrieved memories.
3. Expose the assembly operation through CLI and MCP.
4. Add focused tests for filtering, scope, budget, and backward compatibility.

Later slices may add promotion automation, constraint resolution, lifecycle maintenance, and richer intent analysis.

## Explicit Non-Goals For The First Slice

- No general agent scheduler.
- No autonomous multi-agent orchestration.
- No full rule-language or complex state-machine framework.
- No automatic ingestion of every conversation.
- No silent collection of sensitive information.
- No migration that rewrites all existing memories at once.
- No GBrain dependency or duplicated memory store.

## Acceptance Criteria

- Existing Fix Memory files remain readable and searchable.
- A new task can request one compact Core Context.
- Retrieval returns only relevant, active, in-scope memories within budget.
- Explicit decisions and constraints include source and reason.
- Temporary overrides produce a trace without modifying the underlying rule.
- Users can inspect and correct stored context.
- Tests cover compatibility and the first vertical slice.

## Implementation Status (2026-07-18)

The frozen V2 architecture is implemented in the local-first Markdown backend:

- `scripts/fix_memory.py` supports V2 memory types, metadata, context assembly, lifecycle management, and CLI operations.
- `scripts/context_engine.py` implements intent routing, scope filtering, project affinity, Core Context, Candidate Review, evidence-aware ranking, and dynamic total-budget allocation; the resolver remains available for future trusted Policy input but ordinary Markdown is safely excluded.
- `scripts/fix_memory_mcp.py` exposes only `assemble_context`, `manage_memory`, and `maintain_memory_lifecycle` to MCP clients. Search, assessment, and index helpers remain CLI/internal capabilities.
- `scripts/v2_check.py` covers legacy Markdown compatibility, Candidate Review actions, source-preserving promotion, Agent-facing source rejection, forged Markdown source degradation, untrusted constraint retrieval, project/task isolation, dynamic budget reallocation, oversized-record diagnostics, zero budgets, correction, archive, expiration, and damaged-storage degradation.
- `scripts/mcp_smoke.py` proves V2 operations through a real stdio MCP handshake.
- `scripts/install_codex_mcp.ps1` health-checks and registers the local server without replacing unrelated MCP entries.

Machine integration completed on 2026-07-18:

- Codex MCP name: `fix-memory`
- User-level Codex guidance: `%USERPROFILE%\.codex\AGENTS.md`
- Shared data source: the existing `data/` Markdown tree
- Core Context seeded with confirmed identity, skills, long-term direction, current focus, active project, and natural-recall preference
- Inferred thinking-style observations remain `candidate` and are excluded from default context

Current implementation intentionally stays local and deterministic. Intent analysis uses explicit regex categories and TF-IDF/token relevance rather than an LLM. MCP supplies untrusted memory context only; current system/developer/user instructions and tool permissions remain the enforcement boundary. Ordinary MCP and CLI writes accept only `observed`, `inferred`, or `imported` sources.

Verification commands:

```powershell
D:\python312\python.exe scripts\self_check.py
D:\python312\python.exe scripts\v2_check.py
D:\python312\python.exe scripts\mcp_smoke.py
D:\python312\python.exe scripts\mcp_healthcheck.py --python D:\python312\python.exe
codex mcp list
```

## Drift Guard

Before implementing or redesigning Fix Memory V2, agents must read this document first.

Any proposal that adds a scheduler, general agent runtime, complex policy language, or unrelated platform feature is out of scope unless this baseline is explicitly revised by the user. New ideas should be evaluated against the product principle and first-slice acceptance criteria before being added.
