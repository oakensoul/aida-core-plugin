---
type: skill
name: expert-registry
description: >-
  Manage expert agent activation and panel composition for
  project and global scopes. Provides list, configure, and
  panel operations for expert-based workflows like code review
  and plan grading.
version: 0.1.0
tags:
  - core
  - management
  - experts
  - panels
---

# Expert Registry

Manages expert agent activation and named panel composition.
Experts are regular agents whose frontmatter declares
`role: expert` (plus an optional `expert-role` sub-role).
The registry tracks which experts are active and groups them
into reusable named panels for structured workflows.

## Activation

This skill activates when:

- User invokes `/aida expert list`
- User invokes `/aida expert configure`
- User invokes `/aida expert panels`
- User invokes `/aida expert panel create <name>`
- User invokes `/aida expert panel remove <name>`
- Expert activation or panel management is needed

## Operations

### List Experts

Show all known expert agents and their activation status.

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "list"}'
```

Returns each expert with:

- `name` -- agent name from frontmatter
- `active` -- whether the expert is currently activated
- `expert-role` -- sub-role (`core`, `domain`, or `qa`)
- `source` -- which config file is active (`project` or
  `global`)

### Configure Experts

Interactively select which experts are active and choose
a save target (project or global scope).

Uses the two-phase API.

#### Phase 1: Gather Context

```bash
python {base_directory}/scripts/manage.py \
  --get-questions \
  --context='{"operation": "configure"}'
```

Returns:

```json
{
  "inferred": {
    "current_active": ["reviewer-agent"],
    "source": "project"
  },
  "questions": [
    {
      "id": "expert_selection",
      "type": "multi-select",
      "prompt": "Which experts should be active?",
      "choices": ["<dynamic list of available experts>"],
      "current": ["reviewer-agent"]
    },
    {
      "id": "save_target",
      "type": "choice",
      "prompt": "Save to project or global config?",
      "choices": ["project", "global"],
      "default": "project"
    }
  ]
}
```

#### Phase 2: Execute

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "configure"}' \
  --responses='{"expert_selection": ["reviewer-agent"], "save_target": "project"}'
```

Writes the `experts.active` list to the chosen config file.
Existing keys in the file are preserved.

### List Panels

Show all named panel compositions from the active config.

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "panels"}'
```

Returns each panel with:

- `name` -- panel identifier
- `members` -- list of expert names in the panel
- `stale` -- members listed but not currently active

### Panel Create

Create a new named panel or replace an existing one.

Uses the two-phase API.

#### Phase 1: Gather Context

```bash
python {base_directory}/scripts/manage.py \
  --get-questions \
  --context='{"operation": "panel-create", "panel_name": "review"}'
```

Returns the current active experts as choices plus the
current panel membership if the panel already exists.

#### Phase 2: Execute

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "panel-create", "panel_name": "review"}' \
  --responses='{"members": ["reviewer-agent", "qa-agent"]}'
```

Adds or replaces the named panel in the project config.
Panels are project-scope only (never written to global
config).

### Panel Remove

Remove a named panel from the project config.

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "panel-remove", "panel_name": "review"}'
```

Removes the key from `experts.panels` and writes the file
atomically. No-ops gracefully if the panel does not exist.

## Path Resolution

**Base Directory:** Provided when skill loads via
`<command-message>` tags.

**Script Execution:**

```text
{base_directory}/scripts/manage.py
```

**Reference Files:**

```text
{base_directory}/references/schemas.md
```

**Template Files:**

```text
{base_directory}/templates/questionnaires/configure.yml
```

## Config File Locations

| Scope     | Path                                | Panels |
| --------- | ----------------------------------- | ------ |
| `project` | `.claude/experts.yml`               | Yes    |
| `global`  | `~/.claude/experts.yml`             | No     |

Project config takes priority when `experts.active` is
present (even when empty). Falls through to global config
only when the key is absent.

## Example Workflow

### Activating Experts (Full Flow)

```text
User: /aida expert configure

1. Parse: operation=configure

2. Phase 1 (Python):
   python manage.py --get-questions --context='{"operation": "configure"}'
   Returns:
   - inferred: current_active=["reviewer-agent"], source="project"
   - questions: [expert_selection, save_target]

3. Present choices to user and collect answers

4. Phase 2 (Python):
   python manage.py --execute \
     --context='{"operation": "configure"}' \
     --responses='{"expert_selection": ["reviewer-agent", "qa-agent"],
                   "save_target": "project"}'
   - Writes experts.active to .claude/experts.yml
   - Preserves other keys in the file

5. Report to user:
   "Activated 2 experts in project config."
```

## Resources

### scripts/

- **manage.py** -- Entry point for two-phase API
- **operations/**
  - **registry.py** -- Config I/O, active-expert resolution
  - **panels.py** -- Panel resolution and role filtering

### references/

- **schemas.md** -- Config file and frontmatter schemas

### templates/questionnaires/

- **configure.yml** -- Question template for configure flow
