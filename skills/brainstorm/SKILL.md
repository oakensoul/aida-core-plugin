---
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
---

# Brainstorm

Refines a vague extension idea into a structured brief through
a short, focused dialogue. Invoked by manager skills before
Phase 1 (Gather Context) during `create` operations.

This skill owns **design** questions (how it should work).
It never asks **logistics** questions (location, language,
toolchain) -- those belong to Phase 1.

## Activation

This skill activates when:

- Invoked by `agent-manager`, `skill-manager`, or
  `plugin-manager` during a `create` operation
- The user's description needs refinement before
  context gathering

## Input

The calling manager skill passes:

- `description`: the user's raw description
- `extension_type`: one of `agent`, `skill`, `plugin`

## Dialogue Flow

### Step 1: Understand Intent

Ask the user what problem they are solving or what workflow
gap they want to fill. Do not ask what they want to build --
ask why.

One question. Open-ended.

### Step 2: Explore Behavior

Ask questions about how the extension should work in
practice. Read `references/extension-prompts.md` for
type-specific question banks. Ask as many questions as
needed to get a good understanding -- there is no fixed
limit.

**Rules:**

- One question at a time
- Multiple choice when possible
- Focus on behavior, quality gates, edge cases, and
  integration -- never logistics
- Adapt questions based on prior answers
- Stop when you have enough to produce an actionable brief

### Step 3: Check for Prior Art

Scan the codebase for existing patterns, similar extensions,
or code that the new extension should build on. Briefly report
findings to the user.

### Step 4: Confirm Brief

Present the structured brief as a JSON block. Ask the user
to confirm or adjust before handing back to the manager skill.

**Question budget:** No fixed limit. Ask as many questions as
needed to get a good understanding of what the user wants.
Stop when you have enough to produce an actionable brief.

## Output Contract

Return a JSON object with this structure:

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

The calling manager skill uses this output to enrich its
Phase 1 context:

- `refined_description` replaces the raw user description
  in the Phase 1 `--context` JSON
- `constraints` and `scope` are passed as additional fields
  in the Phase 1 `--context` JSON
- `prior_art` is included in the Phase 2 agent prompt

## Resources

### references/

- **extension-prompts.md** -- Per-type question banks
  organized by category (behavior, quality gates, edge cases,
  integration)
