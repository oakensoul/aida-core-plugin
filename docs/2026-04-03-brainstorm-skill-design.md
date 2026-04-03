# Brainstorm Skill Design

**Date:** 2026-04-03
**Status:** Proposed

## Problem

The current extension creation flow (agent-manager, skill-manager,
plugin-manager) asks logistics questions (toolchain, location, repo
setup) but does not dig into how the extension should actually
behave. This produces extensions that are structurally correct but
lack design depth.

**Example:** When asked to create a PR plugin, the flow asked:

- Which language toolchain?
- Where should it be created?
- Should a GitHub repository be created?
- What features should the PR skill include?

Missing were behavior questions like:

- What information matters in the PR body?
- What should the title format be?
- Are there code checks to run before opening?

These questions would have significantly improved the output quality.

## Solution

Add a standalone `brainstorm` skill that manager skills invoke as
**Phase 0** of the `create` workflow, before the existing Phase 1
(Gather Context). The brainstorm skill owns **design** questions;
Phase 1 continues to own **logistics** questions.

## Skill Definition

### Location

```text
skills/brainstorm/
├── SKILL.md                    # Dialogue flow + output contract
└── references/
    └── extension-prompts.md    # Per-type question banks
```

### Frontmatter

```yaml
type: skill
name: brainstorm
title: Brainstorm
description: >-
  Interactive ideation phase that refines a user's idea into
  a structured brief before extension creation. Invoked by
  manager skills as Phase 0 of the create workflow.
version: 0.1.0
tags:
  - core
  - ideation
user-invocable: false
disable-model-invocation: false
allowed-tools: "*"
```

- **`user-invocable: false`** -- invoked internally by manager
  skills, not directly via `/aida brainstorm`.
- **No Python scripts** -- pure conversational skill. No two-phase
  API needed.

### Output Contract

When the brainstorm completes, it produces a structured brief:

```json
{
  "brainstorm": {
    "refined_description": "concise, clarified description",
    "purpose": "what problem this solves",
    "constraints": ["list of constraints or decisions made"],
    "scope": ["in-scope items"],
    "out_of_scope": ["explicitly excluded items"],
    "prior_art": "existing patterns/code to build on"
  }
}
```

## Dialogue Flow

### Step 1: Understand Intent

Ask what problem the user is solving. Not "what do you want to
build" but "what's the pain point / workflow gap?"

### Step 2: Explore Behavior

Questions about how the extension should work in practice.
Type-aware but always focused on behavior, not logistics.
Ask as many questions as needed -- no fixed limit.

**Question categories** (from `references/extension-prompts.md`):

| Category        | When to ask    | Focus                             |
| --------------- | -------------- | --------------------------------- |
| Behavior        | Always (1-2)   | How should this work end to end?  |
| Quality Gates   | When relevant  | Checks, validations, guardrails   |
| Edge Cases      | When relevant  | Error handling, ambiguous input   |
| Integration     | When relevant  | Interaction with existing tools   |

**Per-type behavior question examples:**

- **Agent:** "When this agent gets a task, what's its
  decision-making process?" / "What should it refuse to do or
  flag for human review?"
- **Skill:** "Walk me through what a successful run looks like
  end to end" / "What inputs does it need and what does it
  produce?"
- **Plugin:** "What's the core workflow this enables?" /
  "What does a user see when it works well vs. when it fails?"

One question at a time. Multiple choice when possible.

### Step 3: Check for Prior Art

Scan the codebase for existing patterns, similar extensions, or
code the new extension should build on. Brief findings reported
to user.

### Step 4: Confirm Brief

Present the structured brief (JSON output contract). User
confirms or adjusts before handing back to the manager skill.

**Question budget:** No fixed limit. Ask as many questions as
needed to get a good understanding of what the user wants.
Stop when you have enough to produce an actionable brief.

**Key principle:** The brainstorm skill never asks about location,
language, or repo creation. Logistics are Phase 1's job; design
is Phase 0's job.

## Integration with Manager Skills

### Flow Change

```text
Today:     User -> Phase 1 (Gather) -> Phase 2 (Generate) -> Phase 3 (Write)
Proposed:  User -> Phase 0 (Brainstorm) -> Phase 1 (Gather) -> Phase 2 (Generate) -> Phase 3 (Write)
```

### Phase 0 in Manager SKILL.md Files

Each manager skill (`agent-manager`, `skill-manager`,
`plugin-manager`) adds a Phase 0 section to its `create`
operation:

```markdown
#### Phase 0: Brainstorm

Before gathering context, invoke the `brainstorm` skill to
refine the user's idea into a structured brief.

**Skip conditions** -- skip Phase 0 when:
- The user's description is already specific and actionable
- The user explicitly says to skip brainstorming
- The operation is not `create`

**Invoke:** Pass the user's description and the extension type
(agent/skill/plugin) to the `brainstorm` skill.

**Result:** Use the brainstorm output to enrich Phase 1 context:
- `refined_description` replaces the raw user description
- `constraints` and `scope` passed as additional context
- `prior_art` informs the claude-code-expert agent in Phase 2
```

### Skip Conditions

Phase 0 is optional. Skip when:

- The user's description is already specific and actionable
- The user explicitly requests skipping (e.g., "just create it")
- The operation is not `create` (validate, version, list)

### Affected Files

| File                            | Change                        |
| ------------------------------- | ----------------------------- |
| `skills/brainstorm/SKILL.md`    | New file                      |
| `skills/brainstorm/references/` | New directory + prompts file  |
| `skills/agent-manager/SKILL.md` | Add Phase 0 to create section |
| `skills/skill-manager/SKILL.md` | Add Phase 0 to create section |
| `skills/plugin-manager/SKILL.md`| Add Phase 0 to create/scaffold |
| `skills/hook-manager/SKILL.md`  | Add Phase 0 to add section    |
| `skills/permissions/SKILL.md`   | Add Phase 0 to setup flow     |
| `skills/aida/SKILL.md`          | No change (routing unchanged) |

## Design Decisions

1. **Standalone skill, not inline** -- keeps brainstorming logic
   DRY and composable for future skills.
2. **`user-invocable: false`** -- internal-only for now. Can be
   promoted to invocable later if standalone brainstorming is
   wanted.
3. **No Python scripts** -- pure dialogue. No file I/O or
   computation needed.
4. **Optional Phase 0** -- avoids friction for power users who
   already know exactly what they want.
5. **Design questions only** -- logistics stay in Phase 1 where
   they already work well.
6. **Question bank in references/** -- keeps SKILL.md focused on
   flow; per-type prompts live in a reference file.
