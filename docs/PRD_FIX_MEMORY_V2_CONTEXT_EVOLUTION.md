# Fix Memory V2 Context Evolution PRD

**Status:** Slice A and Slice B implemented; Slice C deferred
**Date:** 2026-07-19
**Product principle:** Remember useful context safely, assemble it efficiently, and never let ordinary writable memory acquire authority.

## Problem Statement

Fix Memory V2 can already assemble compact, cross-window context from local Markdown memory. Its next limitations are practical rather than foundational:

1. Candidates are either manually promoted one at a time or eventually archived, which makes human review easy to postpone.
2. Core Context, retrieved memory, and policy budgets are static buckets. Unused capacity in one bucket cannot help another bucket.
3. The policy resolver exists but ordinary Markdown is intentionally excluded because its metadata is agent-writable. There is no legitimate trusted policy source yet.
4. Current Focus and Active Projects are separate records, not pointers. This avoids dangling-reference failures today, but does not prevent duplicated or stale summaries.

The user wants a low-interruption workflow that improves recall quality and token efficiency without weakening the security boundary or turning Fix Memory into a general Agent framework.

## Solution

Deliver the next context-quality release in three ordered slices.

### Slice A: Candidate Review Inbox

Provide a batch review workflow that produces a dated Markdown review artifact from eligible candidates. The user can approve, keep pending, archive, or defer several candidates in one deliberate review session. Candidate activation remains ordinary memory activation only; it never creates `user_explicit`, `system`, or Policy authority.

### Slice B: Dynamic Context Budget

Replace independent fixed budget consumption with a total assembly budget, protected minimum allocations, and a second allocation pass. Unused Policy capacity and unused Core capacity can be reassigned to high-relevance retrieved memory. The request itself remains owned by Codex, so Fix Memory only reallocates its own injected context budget.

### Slice C: Trusted Policy Readiness

Define the trust contract and perform a feasibility check for a future trusted policy source. Do not activate Policy Engine inputs in this release. A future source must be outside ordinary agent-writable memory, verifiable at read time, and able to prove issuer provenance. A project-local `config.yaml` with only a read-only flag is not sufficient.

Current Focus and Active Projects remain direct records in this release. The PRD defines deletion and reference-safety requirements for a future pointer model, but does not introduce pointers now.

## User Stories

1. As a user, I want a periodic candidate review artifact, so that I can evaluate unconfirmed memories without interrupting active coding.
2. As a user, I want each review item to show concise content, source, evidence, age, project, and reason, so that I can make a quick decision without opening each Markdown file.
3. As a user, I want to approve several candidates in one session, so that review does not become a repetitive command-by-command task.
4. As a user, I want to defer a candidate, so that uncertainty does not force immediate promotion or deletion.
5. As a user, I want to archive incorrect or obsolete candidates, so that the memory store does not become noisy.
6. As a user, I want a review action to preserve original provenance, so that active ordinary memory is never misrepresented as explicit user confirmation.
7. As an Agent, I want promoted ordinary memory to become eligible for normal retrieval, so that stable context can improve future answers.
8. As an Agent, I want candidate review decisions to remain non-authoritative, so that no review action can create Policy authority.
9. As a user, I want unused context budget to be reassigned to relevant memory, so that useful recall improves without increasing the configured total context size.
10. As an Agent, I want protected minimum Core Context capacity, so that identity, current focus, and active project context are not crowded out by retrieval.
11. As an Agent, I want selection results to explain token allocation and omissions, so that budget behavior can be debugged without dumping all memory.
12. As a user, I want oversized memory content to be skipped or safely summarized at a record boundary, so that an incomplete memory statement is not treated as a complete rule.
13. As a maintainer, I want ordinary Markdown constraints to remain retrievable but untrusted, so that compatibility is preserved without restoring the previous policy-escalation flaw.
14. As a maintainer, I want a documented trust contract before activating trusted policies, so that a future configuration source cannot be mistaken for secure merely because it is called read-only.
15. As a future pointer-model user, I want missing, archived, or deleted targets to degrade to a visible warning and omitted reference, so that context assembly never crashes on a stale reference.
16. As a maintainer, I want direct-record Core Context to keep working while pointer support is absent, so that this release does not require a Markdown migration.

## Implementation Decisions

1. Candidate review is asynchronous and batch-oriented. It must not show a modal prompt during ordinary coding work.
2. Review artifacts are generated from candidate records and runtime metadata; they are not a second source of truth for memory content.
3. Review actions use explicit memory identifiers and write lifecycle metadata such as review timestamp, review decision, and review method. They preserve `source`, `original_source`, confidence, and verification fields.
4. An Agent may generate a review artifact and propose actions, but the workflow must label those actions as agent-originated unless a future trusted human-confirmation boundary is introduced.
5. The budget allocator receives one total context budget plus configured protected minima for Core Context and optional future trusted Policy context.
6. Allocation occurs in passes: protected Core selection, protected trusted Policy selection when such a source exists, then relevance-ranked retrieval using all remaining capacity.
7. Token accounting keeps the current deterministic estimator as a fallback. A model-aware tokenizer may be added only behind an optional adapter because the active provider is not guaranteed to use an OpenAI tokenizer.
8. Oversized records are handled at record boundaries. The system should prefer omission with an omission reason or a stored concise summary over arbitrary character slicing of semantic content.
9. Ordinary writable Markdown continues to produce only untrusted Core Context or Retrieved Memory. It must not produce Effective Constraints, regardless of `source`, `execution_level`, or `policy_key` metadata.
10. Trusted Policy readiness is a design and feasibility output, not an activated feature. Any future source must specify its issuer, storage boundary, integrity verification, loading failure behavior, and revocation path.
11. A project-local YAML file is not accepted as a trusted source merely through filesystem read-only attributes. The trust decision must be enforced outside normal Agent write authority.
12. No pointer fields are introduced in this release. If a later release adds references, they must be optional, resolve defensively, report missing targets in assembly diagnostics, and never prevent unrelated context from assembling.
13. The existing Markdown store remains readable without migration.

## Testing Decisions

1. Test user-visible assembly behavior, lifecycle outcomes, and review output rather than private helper implementation details.
2. Candidate tests must prove that generated review output includes only eligible candidates, preserves original provenance after approval, and never creates Policy authority.
3. Batch review tests must prove mixed approve, defer, archive, and invalid-ID behavior without changing unrelated records.
4. Budget tests must prove that unused reserved capacity is reallocated, protected Core minima remain available, total output stays within the total budget, and omitted records have a traceable reason.
5. Token-estimator tests must cover Chinese, English, mixed text, and one oversized memory record.
6. Ordinary constraints with forged `user_explicit`, `system`, `hard`, and `policy_key` metadata must remain retrieved-only after every new change.
7. Trusted Policy readiness tests are limited to fail-closed loading behavior. Missing, malformed, unverifiable, or inaccessible future policy input must yield no Effective Constraints and must not block normal context assembly.
8. Future pointer tests, when pointers exist, must cover missing, archived, superseded, and deleted targets and verify that assembly returns remaining valid context plus diagnostics.
9. Reuse the existing V2 integration check, MCP smoke test, CLI self-check, and health check as regression seams.

## Out of Scope

1. Activating a trusted Policy Source in this release.
2. Treating a project-local `config.yaml` as trusted based only on a read-only attribute.
3. Building a GUI, web dashboard, notification system, or real-time pop-up confirmation flow.
4. Migrating existing Markdown memories.
5. Adding pointer-based Core Context deduplication.
6. Replacing Codex system, developer, current user instructions, or tool permissions with Fix Memory policy.
7. Building a general Agent scheduler, workflow engine, or multi-agent orchestration layer.

## Further Notes

Gemini's policy-source concern is valid, but the current empty Policy input is an intentional fail-closed security state after source-forgery remediation. The correct next action is to define a trustworthy boundary, not to quickly re-enable policy through an agent-writable configuration file.

Gemini's Candidate Review and dynamic budget concerns are the highest-value next improvements because they directly improve cross-window usefulness without requiring a new trust root.

The pointer concern is deferred deliberately: the current implementation stores direct records and does not dereference memory IDs during assembly. Introducing pointers before there is a demonstrated duplication problem would add lifecycle and integrity complexity without solving the immediate retrieval-quality problem.
