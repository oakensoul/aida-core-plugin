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
- **Two-phase only (not three-phase):** Unlike agent-manager's create
  operation (which uses a third agent-generation step), expert-registry
  operations are pure configuration reads and writes. Two phases
  (gather/execute) are sufficient.

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

**Validation rules for `expert-role`:**

- Must be one of: `core`, `domain`, `qa` (case-sensitive, lowercase only)
- Invalid values (typos, wrong case like `Core`, unknown values like
  `reviewer`) cause the agent to be skipped during expert discovery with
  a warning: `"Skipping {name}: invalid expert-role '{value}',
  expected core|domain|qa"`
- This matches the existing pattern in agent discovery where agents with
  invalid frontmatter are skipped with warnings (see
  `test_missing_required_fields_skipped` in test suite)

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

### Config Semantics

**`active` key absent vs empty list:**

- **Key absent** (no `experts` section or no `active` key): Fall through
  to next layer. If absent at project level, use global. If absent at
  global level, no experts are active.
- **`active: []` (explicit empty list):** Intentional deactivation of all
  experts at this layer. At project level, this overrides global and
  results in zero active experts. This is a deliberate opt-out.

**Non-string values in `active` list:** Entries that are not strings
(null, numbers, objects) are silently skipped with a warning logged.
String entries that do not match any discovered expert are handled per
the error contracts below.

### Resolution Order

1. **Discovery:** Agent-manager discovers all agents from project > user >
   plugin sources.
2. **Filter:** Expert-registry filters to agents with valid `expert-role`.
3. **Activation:** Check project config first. If project has an `experts`
   section with an `active` key (even if empty), use it -- full replacement
   of global. Otherwise, use global `active` list. If neither exists, no
   experts are active.
4. **Dangling reference check:** Any name in `active` that does not match
   a discovered expert is logged as a warning and excluded from the
   resolved list. Same for names in `panels`.
5. **Panel lookup:** If a skill requests a named panel and it exists in
   project config, use that list (filtered to active experts only).
   Otherwise, fall back to all active experts with a signal to the caller
   indicating fallback occurred (see Panel Resolution Logic).

---

## Skill Structure

### Location

```text
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
| `/aida expert panels` | Show named panels and their composition, flag stale entries |
| `/aida expert panel create <name>` | Create a named panel by selecting from active experts |
| `/aida expert panel remove <name>` | Remove a named panel |

### Two-Phase API (ADR-010)

**Phase 1** (`--get-questions`): Discovers all experts across installed
plugins, reads current activation state from global + project config,
returns the expert list with current status and any questions needed.

**Phase 2** (`--execute`): Writes the updated activation state or panel
config to the appropriate YAML file using atomic writes (write to temp
file + rename). This prevents partial-write corruption of
`aida-project-context.yml` or `~/.claude/aida.yml`.

---

## List Output Format

```text
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
  project-level `experts.active` key exists)
- `project` -- Active via `aida-project-context.yml` (when a project
  `experts.active` key exists, it fully replaces global -- all active
  experts show `project` as source)
- `--` -- Not activated at either level

### Panels Output Format

When the user runs `/aida expert panels`:

```text
Named Panels -- Project: my-nestjs-app

code-review (4 experts):
  security-expert, best-practices-reviewer, typescript-expert, web-qa-agent

plan-grading (5 experts):
  security-expert, best-practices-reviewer, nestjs-expert,
  typescript-expert, web-qa-agent

No issues found.
```

When stale entries exist:

```text
plan-grading (4 of 5 experts active):
  security-expert, best-practices-reviewer, nestjs-expert,
  typescript-expert
  WARNING: 1 stale entry (not active or not discovered):
    - redis-expert
  Run `/aida expert configure` to update, or
  `/aida expert panel create plan-grading` to rebuild.
```

---

## Configure Flow

When the user runs `/aida expert configure`:

1. Phase 1 discovers all experts and presents them numbered:

```text
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

1. User responds with numbers or role-based shortcuts
   (`all core`, `all domain`, `none domain`).
2. Claude confirms the change and asks: **Save to project or global?**
   (If user chooses global, panels are not affected -- panels are
   project-only.)
3. Phase 2 writes to the chosen config file atomically.
4. On success: `"Expert configuration saved to {path}. {N} experts active."`
   On write failure: `"Failed to save configuration to {path}: {error}"`

**Edge case -- no experts discovered:** If no installed plugins provide
agents with `expert-role`, the configure command reports:
`"No experts found. Install a plugin that provides expert agents, then
run /aida expert configure."`

**Edge case -- panel create with no active experts:** The command reports:
`"No active experts. Run /aida expert configure first to activate
experts, then create a panel."`

---

## Panel Resolution Logic

```python
@dataclass
class PanelResult:
    """Result of panel resolution."""
    experts: list[str]
    panel_found: bool
    warnings: list[str]


def resolve_panel(panel_name: str | None = None) -> PanelResult:
    """
    1. If panel_name given and exists in project config,
       return that panel's experts filtered to active list.
       panel_found=True.
    2. If panel_name given but not defined,
       return all active experts. panel_found=False.
       Add warning: "Panel '{name}' not defined, using all
       active experts."
    3. If no panel_name, return all active experts.
       panel_found=True (no panel was requested).

    Dangling references (names in panel not in active list or
    not in discovery) are excluded and added to warnings.
    """


def resolve_by_role(role: str) -> PanelResult:
    """
    Return all active experts matching the given role.
    Reads expert-role from agent frontmatter.

    If role is not one of (core, domain, qa), returns empty
    list with warning: "Unknown expert role '{role}',
    expected core|domain|qa."
    """
```

Skills request panels like:

```python
# In a code-review skill
result = resolve_panel("code-review")
if not result.panel_found:
    log.warning("code-review panel not configured")
# result.experts: ["security-expert", "best-practices-reviewer",
#                  "typescript-expert", "web-qa-agent"]

# In a generic panel dispatch
result = resolve_panel()
# result.experts: all active experts

# Role-based filtering
result = resolve_by_role("core")
# result.experts: ["best-practices-reviewer", "security-expert"]

# Unknown role returns empty with warning
result = resolve_by_role("reviewer")
# result.experts: []
# result.warnings: ["Unknown expert role 'reviewer'..."]
```

---

## Error Contracts

### Config File Errors

| Scenario | Behavior |
|----------|----------|
| YAML parse error in global config | Skip global, warn: `"Malformed YAML in {path}, ignoring experts config"`. Fall through as if absent. |
| YAML parse error in project config | Skip project experts section, warn: `"Malformed YAML in {path}, ignoring experts config"`. Fall through to global. |
| `active` contains non-string values | Skip invalid entries with warning per entry. Process remaining valid strings. |
| `panels` value is not a list | Skip that panel with warning: `"Panel '{name}' must be a list, skipping"`. |
| Write failure during Phase 2 | Report error to user: `"Failed to save: {error}"`. Do not partially write. |

### Discovery Errors

| Scenario | Behavior |
|----------|----------|
| Expert name in `active` not found in discovery | Exclude from resolved list. Log warning: `"Expert '{name}' in config but not discovered (plugin uninstalled?)"`. Show in `expert list` output as a separate "Stale references" section. |
| Expert name in panel not found in discovery | Same as above. Additionally flagged in `expert panels` output. |
| No plugins installed / no agents discovered | All commands work but show empty results. `expert list` shows `"No experts found."` `resolve_panel()` returns empty list with no warnings. |
| No agents have `expert-role` set | Same as no experts discovered. |
| Invalid `expert-role` value on agent | Agent skipped during expert filtering with warning (see Data Model section). |

### Resolution Errors

| Scenario | Behavior |
|----------|----------|
| `resolve_panel("name")` where panel not defined | Return all active experts. `panel_found=False`. Warning in result. |
| `resolve_by_role("unknown")` | Return empty list. Warning in result. |
| Both global and project config absent | No experts active. `resolve_panel()` returns empty list, no warnings. |
| Project config exists but no `experts` key | Fall through to global config. |
| Project config has `experts` but no `active` key | Fall through to global config (key must be present to override). |
| Project config has `experts.active: []` | Zero experts active (intentional override). |

---

## Integration Points

### 1. AIDA Dispatcher (`skills/aida/SKILL.md`)

New routing entry for `expert` commands, alongside existing `agent`,
`skill`, `plugin` routes.

Add to the Help Text section under "Extension Management":

```markdown
### Expert Registry
- `/aida expert list` - List available experts and activation status
- `/aida expert configure` - Select active experts (project or global)
- `/aida expert panels` - Show named panel compositions
- `/aida expert panel create <name>` - Create a named expert panel
- `/aida expert panel remove <name>` - Remove a named panel
```

### 2. Project Config Schema (`agents/aida/knowledge/config-schema.md`)

Add `experts` section to schema documentation:

```yaml
experts:                          # optional
  active:                         # optional; list of expert agent names
    - security-expert
    - best-practices-reviewer
  panels:                         # optional; named panel compositions
    code-review:
      - security-expert
      - best-practices-reviewer
```

Bump schema version from `0.2.0` to `0.3.0` to reflect the new section.
Configs without the `experts` key are handled gracefully (fall through
to global or no experts active).

### 3. Global Config Schema (`~/.claude/aida.yml`)

Same `experts.active` shape. No `panels` -- panels are project-specific.

### 4. Agent Frontmatter Schema (`skills/agent-manager/references/schemas.md`)

Add `expert-role` as optional field:

```yaml
expert-role: core|domain|qa
```

### 5. Frontmatter JSON Schema (`.frontmatter-schema.json`)

Add `expert-role` to the `agent` type's properties block:

```json
"expert-role": {
  "type": "string",
  "enum": ["core", "domain", "qa"],
  "description": "Panel expert role for expert-registry dispatch"
}
```

This enables IDE autocomplete and validation via the `validate` command.

### 6. Scaffold Template (`skills/plugin-manager/templates/scaffold/shared/frontmatter-schema.json.jinja2`)

Update the scaffold template to include the `expert-role` property in the
`agent` type block, so newly scaffolded plugins get the field in their
schema from day one.

### 7. Plugin aida-config.json

No changes. Plugins already declare agents in the `agents` array.
Expert-registry discovers agents through existing agent-manager discovery
and filters by `expert-role` in frontmatter.

### 8. Configure Flow (`skills/aida/scripts/configure.py`)

After project configuration completes (`config_complete: true`), if
any discovered agents have `expert-role` set and the project config
has no `experts` section, display:

```text
Expert agents detected from installed plugins.
Run `/aida expert configure` to select which experts are active
for this project.
```

**Trigger condition:** `config_complete is True` AND at least one
discovered agent has `expert-role` AND project config has no
`experts.active` key.

## What This Design Does NOT Do

- Does not duplicate agent discovery -- reads from agent-manager
- Does not modify how agents are defined -- just adds optional
  `expert-role` field
- Does not change how plugins declare agents -- existing
  `aida-config.json` is sufficient
- Does not dictate how consuming skills dispatch agents -- provides
  the list, skills handle dispatch
- Does not add Python dependencies beyond what's already in the venv
