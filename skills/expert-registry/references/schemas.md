---
type: reference
title: Expert Registry Schemas
description: >-
  Configuration schemas for expert activation and panel
  composition in global and project config files.
---

# Expert Registry Schemas

Reference for the data shapes used by the expert registry:
agent frontmatter, global config, and project config.

## Agent Frontmatter: `expert-role`

Agents opt into the expert registry by declaring `role: expert`
in their frontmatter. The optional `expert-role` field assigns
a sub-role used for panel filtering.

```yaml
---
type: agent
name: code-reviewer
description: Reviews code for correctness and style.
version: 0.1.0
role: expert
expert-role: core
tags:
  - review
---
```

### `expert-role` Values

| Value    | Description                               |
| -------- | ----------------------------------------- |
| `core`   | Always-on reviewers (architecture, style) |
| `domain` | Domain-specific experts (API, DB, etc.)   |
| `qa`     | Quality assurance and testing reviewers   |

The field is optional. Experts without `expert-role` are still
eligible for activation; they simply do not appear in
role-filtered panel lookups.

## Global Config (`~/.claude/aida.yml`)

Stores the user-level default expert activation list.

```yaml
experts:
  active:
    - code-reviewer
    - security-reviewer
```

**Constraints:**

- `experts.active` must be a YAML list of strings.
- Panels are not supported at global scope.
- The file may contain other top-level keys; only `experts`
  is read and written by the registry.

## Project Config (`.claude/aida-project-context.yml`)

Stores project-level expert activation and named panels.

```yaml
experts:
  active:
    - code-reviewer
    - qa-agent
  panels:
    review:
      - code-reviewer
      - security-reviewer
    quick:
      - code-reviewer
```

**Constraints:**

- `experts.active` must be a YAML list of strings.
- `experts.panels` must be a mapping of string keys to lists
  of strings.
- The file may contain other top-level keys; only `experts`
  is managed by the registry.

## Layering Semantics

| Condition                                        | Effect                     |
| ------------------------------------------------ | -------------------------- |
| Project config has `experts.active` (any value)  | Project config wins        |
| Project config has `experts.active: []` (empty)  | Project wins (no actives)  |
| Project config lacks `experts.active` key        | Falls through to global    |
| Neither config has `experts.active`              | No experts active          |

The presence of the key -- not its value -- determines
whether the project layer takes effect.

## Panels: Project-Only

Panels are stored in the project config only. The global
config does not support a `panels` key. When a panel name
is requested but not found, the registry falls back to all
currently active experts and emits a warning.

## Dangling Names

A name listed in `experts.active` or inside a panel that does
not correspond to any discovered agent with `role: expert` is
called a **dangling name**. The registry:

1. Reports it as a warning (non-fatal).
2. Excludes it from resolved expert lists.
3. Preserves it in the config file on write (no data loss).
