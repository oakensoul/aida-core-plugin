# Expert Registry Design Spec

**Date:** 2026-04-16
**Status:** Approved
**Scope:** New `expert-registry` skill for aida-core-plugin

## Problem

Panel-based workflows (code review, plan grading, feature review) need to
dispatch parallel expert agents. Today, the set of experts is hardcoded
per-skill. Users cannot configure which experts are active for their project,
see what experts are available across installed plugins, or define named
panels for different review contexts.

## Solution

A new `expert-registry` skill that reads from the existing agent discovery
system and adds an activation layer, role-based filtering, and named panel
composition. Configuration is layered: global defaults in `~/.claude/aida.yml`,
project overrides in `aida-project-context.yml`.

## Design Decisions

- **Approach C (New Skill + Config Schema Extension):** Clean separation --
  agent-manager handles CRUD/discovery, expert-registry handles activation
  and panel composition.
- **Questionnaire-style UX (Approach A):** Consistent with the existing
  two-phase API pattern. No TUI dependencies.
- **Layered config (global + project):** Project `active` list fully
  replaces global when present.
- **Flat active list + optional named panels:** Maximum flexibility with
  sensible defaults.
- **Role tags on agents:** `core`, `domain`, `qa` enable skills to filter
  without knowing every expert by name.

---

## Data Model

### Agent Frontmatter Extension

Agents that can serve as panel experts declare `expert-role` in frontmatter:

```yaml
---
type: agent
name: security-expert
description: Application security review for NestJS
version: 1.0.0
tags:
  - security
  - review
expert-role: core
---
```

Valid roles:

- `core` -- Always included in panels unless explicitly excluded
  (security, best-practices, similar)
- `domain` -- Included when the work touches their domain
  (nestjs, bullmq, redis, pusher, similar)
- `qa` -- Testing/QA specialists, included in review and validation panels

Agents without `expert-role` are not eligible for panel dispatch.

### Global Config (`~/.claude/aida.yml`)

```yaml
experts:
  active:
    - security-expert
    - best-practices-reviewer
    - typescript-expert
    - web-qa-agent
```

Global config has no `panels` section. Panels are project-specific since
different projects need different compositions.

### Project Config (`aida-project-context.yml`)

```yaml
experts:
  active:
    - security-expert
    - best-practices-reviewer
    - nestjs-expert
    - typescript-expert
    - bullmq-expert
    - redis-expert
    - web-qa-agent
  panels:
    code-review:
      - security-expert
      - best-practices-reviewer
      - typescript-expert
      - web-qa-agent
    plan-grading:
      - security-expert
      - best-practices-reviewer
      - nestjs-expert
      - typescript-expert
      - web-qa-agent
```

### Resolution Order

1. **Discovery:** Agent-manager discovers all agents from project > user >
   plugin sources.
2. **Filter:** Expert-registry filters to agents with `expert-role` set.
3. **Activation:** Merge global `active` list with project `active` list.
   Project wins -- full replacement, not additive.
4. **Panel lookup:** If a skill requests a named panel and it exists in
   project config, use that list. Otherwise, fall back to all active experts.

---

## Skill Structure

### Location

```
skills/expert-registry/
├── SKILL.md
├── scripts/
│   ├── manage.py
│   └── operations/
│       ├── registry.py
│       └── panels.py
├── references/
│   └── schemas.md
└── templates/
    └── questionnaires/
        └── configure.yml
```

### Commands

Routed via `/aida expert ...`:

| Command | Description |
|---------|-------------|
| `/aida expert list` | Show all discovered experts with plugin source, role, activation status, and config source (global/project) |
| `/aida expert configure` | Interactive selection to toggle experts active/inactive, save to project or global config |
| `/aida expert panels` | Show named panels and their composition |
| `/aida expert panel create <name>` | Create a named panel by selecting from active experts |
| `/aida expert panel remove <name>` | Remove a named panel |

### Two-Phase API (ADR-010)

**Phase 1** (`--get-questions`): Discovers all experts across installed
plugins, reads current activation state from global + project config,
returns the expert list with current status and any questions needed.

**Phase 2** (`--execute`): Writes the updated activation state or panel
config to the appropriate YAML file.

---

## List Output Format

```
Expert Registry -- Project: my-nestjs-app

Plugin: splash-engineering (marketplace)
  Name                    Role     Status      Source
  ─────────────────────── ──────── ─────────── ────────
  best-practices-reviewer core     [active]    global
  security-expert         core     [active]    global
  web-qa-agent            qa       [active]    project
  nestjs-expert           domain   [active]    project
  typescript-expert       domain   [active]    project
  bullmq-expert           domain   [active]    project
  redis-expert            domain   [inactive]  --
  pusher-expert           domain   [inactive]  --
  devops-agent            domain   [inactive]  --

Plugin: aida-core (marketplace)
  Name                    Role     Status      Source
  ─────────────────────── ──────── ─────────── ────────
  claude-code-expert      domain   [inactive]  --

Active: 6 experts (3 global, 3 project override)
Panels: code-review (4 experts), plan-grading (5 experts)
```

**Source column logic:**

- `global` -- Active via `~/.claude/aida.yml` (shown only when no
  project-level `experts.active` list exists)
- `project` -- Active via `aida-project-context.yml` (when a project
  `experts.active` list exists, it fully replaces global -- all active
  experts show `project` as source)
- `--` -- Not activated at either level

---

## Configure Flow

When the user runs `/aida expert configure`:

1. Phase 1 discovers all experts and presents them numbered:

```
Select experts to activate for this project.
Current activation shown. Type numbers to toggle.

  1. [x] best-practices-reviewer  (core, splash-engineering)
  2. [x] security-expert          (core, splash-engineering)
  3. [x] web-qa-agent             (qa, splash-engineering)
  4. [x] nestjs-expert            (domain, splash-engineering)
  5. [x] typescript-expert        (domain, splash-engineering)
  6. [x] bullmq-expert            (domain, splash-engineering)
  7. [ ] redis-expert             (domain, splash-engineering)
  8. [ ] pusher-expert            (domain, splash-engineering)
  9. [ ] devops-agent             (domain, splash-engineering)
 10. [ ] claude-code-expert       (domain, aida-core)

Toggle (e.g. "7 8" or "all domain"): 
```

2. User responds with numbers or role-based shortcuts
   (`all core`, `all domain`, `none domain`).
3. Claude confirms the change and asks: **Save to project or global?**
4. Phase 2 writes to the chosen config file.

---

## Panel Resolution Logic

```python
def resolve_panel(panel_name: str | None = None) -> list[str]:
    """
    1. If panel_name given and exists in project config,
       return that panel's experts.
    2. If panel_name given but not defined,
       fall back to all active experts.
    3. If no panel_name, return all active experts.

    In all cases, filter out experts not in the active list.
    A named panel can only contain experts that are currently active.
    """


def resolve_by_role(role: str) -> list[str]:
    """
    Return all active experts matching the given role.
    Reads expert-role from agent frontmatter.
    """
```

Skills request panels like:

```python
# In a code-review skill
experts = resolve_panel("code-review")
# Returns: ["security-expert", "best-practices-reviewer",
#           "typescript-expert", "web-qa-agent"]

# In a generic panel dispatch
experts = resolve_panel()
# Returns: all active experts

# Role-based filtering
core = resolve_by_role("core")
# Returns: ["best-practices-reviewer", "security-expert"]
```

---

## Integration Points

### 1. AIDA Dispatcher (`skills/aida/SKILL.md`)

New routing entry for `expert` commands, alongside existing `agent`,
`skill`, `plugin` routes.

### 2. Project Config Schema (`agents/aida/knowledge/config-schema.md`)

Add `experts` section:

```yaml
experts:
  active: [list of expert agent names]
  panels:
    {panel-name}: [list of expert agent names]
```

Both `active` and `panels` are optional. If absent, global config is
used as-is.

### 3. Global Config Schema (`~/.claude/aida.yml`)

Same `experts.active` shape. No `panels` -- panels are project-specific.

### 4. Agent Frontmatter Schema (`skills/agent-manager/references/schemas.md`)

Add `expert-role` as optional field:

```yaml
expert-role: core|domain|qa
```

### 5. Plugin aida-config.json

No changes. Plugins already declare agents in the `agents` array.
Expert-registry discovers agents through existing agent-manager discovery
and filters by `expert-role` in frontmatter.

### 6. Configure Flow (`skills/aida/scripts/configure.py`)

After project configuration completes, if installed plugins provide
experts, the flow prompts: "Would you like to configure expert panels?
Run `/aida expert configure`."

## What This Design Does NOT Do

- Does not duplicate agent discovery -- reads from agent-manager
- Does not modify how agents are defined -- just adds optional
  `expert-role` field
- Does not change how plugins declare agents -- existing
  `aida-config.json` is sufficient
- Does not dictate how consuming skills dispatch agents -- provides
  the list, skills handle dispatch
- Does not add Python dependencies beyond what's already in the venv
