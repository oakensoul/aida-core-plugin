# Brainstorm Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a brainstorm skill that manager skills invoke as
Phase 0 of `create` workflows, asking behavior/design questions
before the existing logistics-focused Phase 1.

**Architecture:** A new pure-dialogue skill at
`skills/brainstorm/` with a SKILL.md and a reference file for
per-type question banks. Each manager skill's SKILL.md gets a
Phase 0 section that invokes the brainstorm skill before Phase 1
on `create` operations.

**Tech Stack:** Markdown only (no Python scripts).

**Spec:** `docs/2026-04-03-brainstorm-skill-design.md`

---

## File Map

| File | Action | Responsibility |
| ---- | ------ | -------------- |
| `skills/brainstorm/SKILL.md` | Create | Dialogue flow, output contract, skip conditions |
| `skills/brainstorm/references/extension-prompts.md` | Create | Per-type question banks (agent, skill, plugin) |
| `skills/agent-manager/SKILL.md` | Modify | Add Phase 0 before Phase 1 in create section |
| `skills/skill-manager/SKILL.md` | Modify | Add Phase 0 before Phase 1 in create section |
| `skills/plugin-manager/SKILL.md` | Modify | Add Phase 0 before Phase 1 in create section |

---

### Task 1: Create brainstorm SKILL.md

**Files:**

- Create: `skills/brainstorm/SKILL.md`

- [ ] **Step 1: Create the skill file**

Create `skills/brainstorm/SKILL.md` with this exact content:

````markdown
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

Ask 2-4 questions about how the extension should work in
practice. Read `references/extension-prompts.md` for
type-specific question banks.

**Rules:**

- One question at a time
- Multiple choice when possible
- Focus on behavior, quality gates, edge cases, and
  integration -- never logistics
- Adapt questions based on prior answers

### Step 3: Check for Prior Art

Scan the codebase for existing patterns, similar extensions,
or code that the new extension should build on. Briefly report
findings to the user.

### Step 4: Confirm Brief

Present the structured brief as a JSON block. Ask the user
to confirm or adjust before handing back to the manager skill.

**Question budget:** 2-4 questions total (Steps 1-2 combined).
This is lightweight ideation, not a full design session.

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
- `constraints` and `scope` are passed as additional context
  to Phase 1
- `prior_art` informs the `claude-code-expert` agent in
  Phase 2

## Resources

### references/

- **extension-prompts.md** -- Per-type question banks
  organized by category (behavior, quality gates, edge cases,
  integration)
````

- [ ] **Step 2: Validate frontmatter**

Run the existing validation to confirm the frontmatter is valid:

```bash
~/.aida/venv/bin/python skills/agent-manager/scripts/manage.py \
  --execute \
  --context='{"operation": "validate", "name": "brainstorm", "location": "plugin"}'
```

Expected: validation passes (or the skill-manager equivalent
works -- use whichever validate command is available).

If no automated validator is handy, manually confirm:

- `type: skill` present
- `name` matches `^[a-z][a-z0-9-]*$`, 2-50 chars
- `description` is 10-500 chars
- `version` matches `^\d+\.\d+\.\d+$`
- `tags` array with lowercase kebab-case entries

- [ ] **Step 3: Lint the file**

```bash
make lint
```

Expected: no new warnings or errors from `brainstorm/SKILL.md`.

- [ ] **Step 4: Commit**

```bash
git add skills/brainstorm/SKILL.md
git commit -m "feat: add brainstorm skill definition"
```

---

### Task 2: Create extension-prompts.md reference

**Files:**

- Create: `skills/brainstorm/references/extension-prompts.md`

- [ ] **Step 1: Create the reference file**

Create `skills/brainstorm/references/extension-prompts.md`
with this exact content:

````markdown
---
type: reference
title: Extension Prompts
description: >-
  Per-type question banks for the brainstorm skill, organized
  by category.
---

# Extension Prompts

Question banks for the brainstorm dialogue, organized by
extension type and category. Pick questions that fit the
user's idea -- do not ask all of them.

## Question Categories

### Behavior (always ask 1-2)

How should this work end to end? What does success look like?

### Quality Gates (ask when relevant)

What checks, validations, or guardrails matter?

### Edge Cases (ask when relevant)

What happens when things go wrong or input is ambiguous?

### Integration (ask when relevant)

How does this interact with existing tools or workflows?

## Agent Questions

### Behavior

- When this agent gets a task, what's its decision-making
  process? (e.g., always ask clarifying questions first /
  try the simplest approach / follow a strict checklist)
- What does a successful outcome look like for this agent?
- What information does the agent need before it can start
  working?

### Quality Gates

- What should it refuse to do or flag for human review?
- Are there outputs that need validation before the agent
  reports success?

### Edge Cases

- What should it do when it encounters ambiguous
  instructions?
- If it gets stuck, should it ask for help or try
  alternatives on its own?

### Integration

- What tools or external services does it need access to?
- Does it need to coordinate with other agents or skills?

## Skill Questions

### Behavior

- Walk me through what a successful run looks like end to
  end.
- What inputs does it need and what does it produce?
- Should it be interactive (ask questions during execution)
  or run to completion autonomously?

### Quality Gates

- What makes a run "good" vs. "acceptable" vs. "failed"?
- Are there preconditions that must be true before it starts?

### Edge Cases

- What should happen if required input is missing or
  malformed?
- If the skill partially completes, should it roll back or
  report partial results?

### Integration

- Does this skill build on or replace an existing workflow?
- What other skills or tools does the user currently use for
  this task?

## Plugin Questions

### Behavior

- What's the core workflow this plugin enables?
- What does a user see when it works well vs. when it fails?
- Who is the target audience -- individual developers, teams,
  or both?

### Quality Gates

- What standards or conventions should the plugin enforce?
- Should it validate its own output before presenting it to
  the user?

### Edge Cases

- What happens if the plugin is used in a project that
  doesn't match its assumptions (e.g., wrong language,
  missing config)?
- How should it handle version conflicts with other plugins?

### Integration

- What existing tools or workflows does this replace or
  complement?
- Does it need to work across multiple projects or is it
  project-specific?
````

- [ ] **Step 2: Lint**

```bash
make lint
```

Expected: no new warnings or errors.

- [ ] **Step 3: Commit**

```bash
git add skills/brainstorm/references/extension-prompts.md
git commit -m "feat: add brainstorm question banks"
```

---

### Task 3: Add Phase 0 to agent-manager

**Files:**

- Modify: `skills/agent-manager/SKILL.md:42-45`

- [ ] **Step 1: Insert Phase 0 before Phase 1**

In `skills/agent-manager/SKILL.md`, find the line:

```markdown
#### Phase 1: Gather Context (Python)
```

Insert the following **before** it (after the line
`pattern**:`):

```markdown
#### Phase 0: Brainstorm

Before gathering context, invoke the `brainstorm` skill to
refine the user's idea into a structured brief.

**Skip conditions** -- skip Phase 0 when:

- The user's description is already specific and actionable
- The user explicitly says to skip brainstorming
  (e.g., "just create it")

**Invoke:** Pass the user's description and
`extension_type: "agent"` to the `brainstorm` skill.

**Result:** Use the brainstorm output to enrich Phase 1
context:

- `refined_description` replaces the raw user description
  in the Phase 1 `--context` JSON
- `constraints` and `scope` are passed as additional fields
  in the Phase 1 `--context` JSON
- `prior_art` is included in the Phase 2 agent prompt

```

- [ ] **Step 2: Lint**

```bash
make lint
```

Expected: no new warnings or errors.

- [ ] **Step 3: Commit**

```bash
git add skills/agent-manager/SKILL.md
git commit -m "feat: add Phase 0 brainstorm to agent-manager"
```

---

### Task 4: Add Phase 0 to skill-manager

**Files:**

- Modify: `skills/skill-manager/SKILL.md:33-36`

- [ ] **Step 1: Insert Phase 0 before Phase 1**

In `skills/skill-manager/SKILL.md`, find the line:

```markdown
#### Phase 1: Gather Context (Python)
```

Insert the following **before** it (after the line that reads
`pattern.`):

```markdown
#### Phase 0: Brainstorm

Before gathering context, invoke the `brainstorm` skill to
refine the user's idea into a structured brief.

**Skip conditions** -- skip Phase 0 when:

- The user's description is already specific and actionable
- The user explicitly says to skip brainstorming
  (e.g., "just create it")

**Invoke:** Pass the user's description and
`extension_type: "skill"` to the `brainstorm` skill.

**Result:** Use the brainstorm output to enrich Phase 1
context:

- `refined_description` replaces the raw user description
  in the Phase 1 `--context` JSON
- `constraints` and `scope` are passed as additional fields
  in the Phase 1 `--context` JSON
- `prior_art` is included in the Phase 2 agent prompt

```

- [ ] **Step 2: Lint**

```bash
make lint
```

Expected: no new warnings or errors.

- [ ] **Step 3: Commit**

```bash
git add skills/skill-manager/SKILL.md
git commit -m "feat: add Phase 0 brainstorm to skill-manager"
```

---

### Task 5: Add Phase 0 to plugin-manager

**Files:**

- Modify: `skills/plugin-manager/SKILL.md:69-72`

- [ ] **Step 1: Insert Phase 0 before Phase 1**

In `skills/plugin-manager/SKILL.md`, find the section:

```markdown
### Extension Operations (create / validate / version / list)

#### Phase 1: Gather Context
```

Insert the following **before** `#### Phase 1: Gather Context`
and after the `### Extension Operations` heading:

```markdown
#### Phase 0: Brainstorm

Before gathering context for `create` operations, invoke the
`brainstorm` skill to refine the user's idea into a structured
brief. Skip this phase for `validate`, `version`, and `list`
operations.

**Skip conditions** -- skip Phase 0 when:

- The user's description is already specific and actionable
- The user explicitly says to skip brainstorming
  (e.g., "just create it")
- The operation is not `create`

**Invoke:** Pass the user's description and
`extension_type: "plugin"` to the `brainstorm` skill.

**Result:** Use the brainstorm output to enrich Phase 1
context:

- `refined_description` replaces the raw user description
  in the Phase 1 `--context` JSON
- `constraints` and `scope` are passed as additional fields
  in the Phase 1 `--context` JSON
- `prior_art` is included in Phase 2 when generating plugin
  extensions

```

Also add the same Phase 0 section before the scaffold
operation's Phase 1, since scaffolding a new plugin also
benefits from brainstorming. Find:

```markdown
### Scaffold Operation

#### Phase 1: Gather Context
```

Insert before `#### Phase 1: Gather Context`:

```markdown
#### Phase 0: Brainstorm

Before gathering context, invoke the `brainstorm` skill to
refine the user's plugin idea into a structured brief.

**Skip conditions** -- skip Phase 0 when:

- The user's description is already specific and actionable
- The user explicitly says to skip brainstorming
  (e.g., "just create it")

**Invoke:** Pass the user's description and
`extension_type: "plugin"` to the `brainstorm` skill.

**Result:** Use the brainstorm output to enrich Phase 1
context:

- `refined_description` replaces the raw user description
- `constraints` and `scope` inform scaffold questions
- `prior_art` helps determine which stubs to generate

```

- [ ] **Step 2: Lint**

```bash
make lint
```

Expected: no new warnings or errors.

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-manager/SKILL.md
git commit -m "feat: add Phase 0 brainstorm to plugin-manager"
```

---

### Task 6: Final validation

**Files:** All modified files

- [ ] **Step 1: Run full lint suite**

```bash
make lint
```

Expected: clean pass, no new warnings.

- [ ] **Step 2: Run tests**

```bash
make test
```

Expected: all existing tests pass. No new tests needed since
this is a pure-markdown change with no Python code.

- [ ] **Step 3: Verify directory structure**

```bash
ls -la skills/brainstorm/
ls -la skills/brainstorm/references/
```

Expected:

```text
skills/brainstorm/
  SKILL.md
  references/
    extension-prompts.md
```

- [ ] **Step 4: Verify Phase 0 appears in all managers**

```bash
rg "Phase 0: Brainstorm" skills/
```

Expected: matches in:

- `skills/agent-manager/SKILL.md`
- `skills/skill-manager/SKILL.md`
- `skills/plugin-manager/SKILL.md` (twice: extension + scaffold)
