---
type: adr
title: "ADR-012: Phase 0 Brainstorm for Extension Creation"
status: accepted
date: "2026-04-03"
deciders:
  - "@euglevit"
---

# ADR-012: Phase 0 Brainstorm for Extension Creation

## Context

The existing extension creation workflow (ADR-010) uses a two-phase
API pattern: Phase 1 gathers context and infers metadata, Phase 2
executes with user responses. Manager skills (agent-manager,
skill-manager, plugin-manager, hook-manager, permissions) follow
this pattern for their create/add/setup operations.

However, the current Phase 1 questions focus on **logistics**:
toolchain, location, repo creation, scope. They do not explore
**how the extension should behave**. This produces extensions that
are structurally correct but lack design depth.

**Example**: When creating a PR plugin, Phase 1 asked:

- Which language toolchain?
- Where should the plugin be created?
- Should a GitHub repository be created?
- What features should the PR skill include?

Missing were behavior questions like:

- What information matters in the PR body?
- What should the title format be?
- Are there code checks to run before opening?

These design questions would have significantly improved output
quality.

## Decision

Add a **Phase 0: Brainstorm** step to extension creation workflows.
Phase 0 is a standalone `brainstorm` skill that manager skills
invoke before Phase 1 during create operations.

### Separation of Concerns

| Phase | Owns | Examples |
| --- | --- | --- |
| Phase 0 | **Design** -- how it should work | Behavior, quality gates, edge cases |
| Phase 1 | **Logistics** -- where it goes | Location, toolchain, naming |
| Phase 2 | **Execution** -- make it happen | File creation, validation |

### Brainstorm Skill

- **Location**: `skills/brainstorm/SKILL.md`
- **Type**: Pure conversational skill (no Python scripts)
- **Invocable**: Internal only (`user-invocable: false`)
- **Question bank**: `references/extension-prompts.md` with
  per-type questions (agent, skill, plugin, hook, permissions)

### Output Contract

Phase 0 produces a structured brief:

```json
{
  "brainstorm": {
    "refined_description": "concise, clarified description",
    "purpose": "what problem this solves",
    "constraints": ["decisions made during brainstorming"],
    "scope": ["in-scope items"],
    "out_of_scope": ["explicitly excluded items"],
    "prior_art": "existing patterns/code to build on"
  }
}
```

This output enriches subsequent phases:

- `refined_description` replaces the raw user description in
  Phase 1's `--context` JSON
- `constraints` and `scope` are passed as additional context
- `prior_art` informs the `claude-code-expert` agent in Phase 2

### Skip Conditions

Phase 0 is optional. It is skipped when:

- The user's description is already specific and actionable
- The user explicitly requests skipping ("just create it")
- The operation is not a create/add/setup operation
- A built-in template is selected (hook-manager)
- Audit mode is active (permissions)

## Rationale

### Why a Separate Phase?

**1. Design questions are categorically different from logistics**:

Phase 1 asks "where and how to set up." Phase 0 asks "what
should this do and why." Mixing them blurs the purpose of each
phase and makes it harder to skip one without the other.

**2. Reusable across all manager skills**:

A standalone brainstorm skill keeps the logic DRY. All five
manager skills invoke the same skill rather than each
implementing their own brainstorming flow.

**3. Optional without disrupting the existing pattern**:

Phase 0 is additive. The two-phase API (ADR-010) remains
unchanged. Power users who already know exactly what they want
skip straight to Phase 1.

### Why a Standalone Skill (Not Inline)?

- **Single source of truth** for brainstorming logic
- **Composable** -- future skills can invoke it
- **Testable** -- can be validated independently
- **Follows ADR-001** -- skills define WHAT, this skill defines
  the brainstorming process

### Why No Python Scripts?

Phase 0 is a dialogue between Claude and the user. It asks
questions, checks for prior art in the codebase, and produces
a structured brief. No file I/O, computation, or environment
detection is needed -- those remain in Phase 1.

## Consequences

### Positive

- Extensions are designed before they are built
- Users have a voice in how their extensions behave
- Question bank grows over time as new patterns emerge
- No disruption to existing two-phase API
- Power users can skip when not needed

### Negative

- Adds an extra step to the creation workflow
- May feel slow for users who want quick scaffolding
- Question quality depends on the brainstorm skill's prompts

### Mitigation

**Extra step**: Skip conditions ensure Phase 0 only runs when
it adds value. Specific, actionable descriptions bypass it
automatically.

**Slowness**: No fixed question limit. The skill asks as many
questions as needed but stops when it has enough for an
actionable brief.

**Question quality**: The `references/extension-prompts.md`
question bank is maintained as a living document and can be
improved based on user feedback.

## Affected Skills

| Skill | Phase 0 Location |
| --- | --- |
| `agent-manager` | Before Phase 1 in create |
| `skill-manager` | Before Phase 1 in create |
| `plugin-manager` | Before Phase 1 in create and scaffold |
| `hook-manager` | Before Phase 1 in add |
| `permissions` | Before Phase 1 in setup |

## Related Decisions

- [ADR-001: Skills-First Architecture](001-skills-first-architecture.md)
  -- Phase 0 follows the skills-first pattern
- [ADR-010: Two-Phase API Pattern](010-two-phase-api-pattern.md)
  -- Phase 0 extends (not replaces) the two-phase pattern

---

**Decision Record**: @euglevit, 2026-04-03
**Status**: Accepted
