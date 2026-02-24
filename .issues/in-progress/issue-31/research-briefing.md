---
type: research
title: "Issue #31 Research Briefing: Decompose claude-code-management"
description: >
  Synthesized findings from docs research, architecture analysis, codebase
  analysis, framework review, and UX assessment for the decomposition of the
  monolithic claude-code-management skill.
status: final
date: 2026-02-24
synthesized_by: claude-code-expert
sources:
  - research-docs.md (docs-researcher)
  - research-architecture.md (system-architect)
  - research-codebase.md (code-analyst)
  - research-framework.md (claude-code-expert)
  - research-user-perspective.md (shell-systems-ux-designer)
---

# Issue #31 Research Briefing

## Part 1: Executive Summary

### What Changed in Claude Code

Claude Code has evolved significantly since the `claude-code-management` skill
was written. The docs researcher catalogued 57 documentation pages, finding
18 new features and over 10 areas where our knowledge base is outdated.

**Most significant changes for this issue:**

1. **Skills frontmatter has expanded** -- New fields: `context`, `agent`,
   `hooks`, `model`, and the `context: fork` mode for running skills in
   subagents. Skills now conform to the Agent Skills open standard (agentskills.io).
2. **Subagent frontmatter has expanded** -- New fields: `permissionMode`,
   `maxTurns`, `memory`, `background`, `isolation`, `mcpServers`, `hooks`.
   Subagents now have persistent memory and worktree isolation support.
3. **Plugins now bundle more component types** -- LSP servers (`.lsp.json`),
   MCP servers (`.mcp.json`), hooks (`hooks/hooks.json`), default settings
   (`settings.json`), output styles (`outputStyles/`).
4. **Hook system expanded** -- 17 events (up from 10), three hook types
   (`command`, `prompt`, `agent` -- the last two involve the LLM and are
   not deterministic).
5. **Agent teams are experimental** -- Multi-instance coordination with
   shared task lists, inter-agent messaging, and new hook events
   (`TeammateIdle`, `TaskCompleted`).
6. **New memory and instruction mechanisms** -- Auto memory
   (`~/.claude/projects/<project>/memory/`), modular rules (`.claude/rules/`),
   `CLAUDE.local.md` for personal project preferences.

**What has NOT changed:**

The fundamental WHO/HOW/CONTEXT/MEMORY/AUTOMATION taxonomy remains accurate.
The file-based extension model (YAML frontmatter + markdown) is still the
primary extension mechanism. Plugin development is still markdown-based, not
TypeScript.

---

## Part 2: Architecture Recommendation

### Recommended Target Structure

```text
skills/
  aida/                       # Router (simplified dispatch)
    SKILL.md                  # Direct entity-to-manager routing
    scripts/                  # (unchanged)
    references/               # (unchanged)

  agent-manager/              # Agent CRUD
    SKILL.md
    scripts/
      manage.py               # Simplified entry point (no routing)
      operations/
        extensions.py         # Agent-specific create/validate/version/list
        utils.py              # Imports from scripts/shared/utils.py
    templates/
      agent.md.jinja2
    references/
      create-workflow.md
      validate-workflow.md
      schemas.md

  skill-manager/              # Skill CRUD
    SKILL.md
    scripts/
      manage.py
      operations/
        extensions.py         # Skill-specific create/validate/version/list
        utils.py
    templates/
      SKILL.md.jinja2
    references/
      create-workflow.md
      validate-workflow.md
      schemas.md

  plugin-manager/             # Plugin ops + scaffolding (merged from create-plugin)
    SKILL.md
    scripts/
      manage.py
      operations/
        extensions.py         # Plugin extension create/validate/version/list
        scaffold.py           # New plugin project scaffolding (from create-plugin)
        scaffold_ops/         # (from create-plugin)
          context.py
          generators.py
          licenses.py
        utils.py
    templates/
      extension/              # Plugin extension templates
        plugin.json.jinja2
        README.md.jinja2
        gitignore.jinja2
      scaffold/               # Project scaffolding templates (from create-plugin)
        shared/
        python/
        typescript/
    references/
      scaffolding-workflow.md
      validate-workflow.md
      schemas.md

  hook-manager/               # Hook ops (cleanest split -- fully independent)
    SKILL.md
    scripts/
      manage.py
      operations/
        hooks.py              # Current hooks.py (minimal changes)
    references/
      hooks-reference.md

  claude-md-manager/          # CLAUDE.md ops
    SKILL.md
    scripts/
      manage.py
      operations/
        claude_md.py          # Current claude_md.py (minimal changes)
        utils.py
    templates/
      claude-md/
        project.md.jinja2
        user.md.jinja2
        plugin.md.jinja2
    references/
      claude-md-workflow.md
      best-practices.md

  memento/                    # (unchanged)
  permissions/                # (unchanged)

scripts/
  shared/
    utils.py                  # (unchanged -- used by all managers)
```

### What Changes in aida/SKILL.md Routing

**Before:**

```text
/aida agent|skill|plugin|hook [op] → claude-code-management skill
/aida claude [op]                  → claude-code-management skill
/aida plugin scaffold              → create-plugin skill (special case!)
```

**After:**

```text
/aida agent [op]        → agent-manager skill
/aida skill [op]        → skill-manager skill
/aida plugin [op]       → plugin-manager skill (all plugin ops, no special case)
/aida hook [op]         → hook-manager skill
/aida claude [op]       → claude-md-manager skill
```

The three-layer indirection (`/aida` -> `claude-code-management` -> manage.py)
collapses to two layers (`/aida` -> specific manager).

### Marketplace Manager Decision

**Defer `marketplace-manager` to a follow-on issue.**

Rationale from both architecture and UX research:
- No existing operations to put in it (current `claude-code-management` has
  no marketplace operations)
- `create-plugin` generates `marketplace.json` but this moves into
  `plugin-manager`
- Creating a stub risks premature API commitment
- Adding it later is straightforward; routing table has a reserved slot

### MCP Manager Decision

**No `mcp-manager` at v1.0.**

MCP configuration belongs in `settings.json` management (potentially a
future settings manager) or as bundled configs within plugin scaffolding.
The architecture team confirms: defer until MCP support matures in the
ecosystem.

---

## Part 3: User Experience Assessment

### Command Surface

The user-facing command grammar **does not change**. Users continue to use
`/aida agent create`, `/aida hook list`, etc. The routing is an internal
concern invisible to users.

### Improvements Enabled by the Decomposition

1. **Focused context loading** -- When user runs `/aida hook list`, only
   `hook-manager`'s SKILL.md loads (not 600 lines covering all entities).
   This preserves context window for the user's actual work.

2. **Entity-specific error messages** -- Each manager can provide errors
   that reference the user's actual command, not internal context fields
   from `manage.py`.

3. **Entity-specific help** -- Each manager can show focused help when
   invoked with just an entity name and no verb:
   ```text
   /aida agent
   → Available commands: create, validate, version, list
   → Examples: /aida agent create "handles code reviews"
   ```

4. **No more special-case routing** -- `plugin scaffold` no longer needs
   to be caught before general plugin routing. `plugin-manager` handles
   all plugin operations.

### Cross-Cutting Operations

The UX research identifies two cross-cutting operations worth preserving:

- `/aida validate --all` -- fan out to all managers, aggregate results
- `/aida list` -- optional summary across all entity types

Recommendation: implement at the aida dispatcher level, not inside any
individual manager.

---

## Part 4: Key Decisions

### Decision 1: Extraction Order

**Recommendation: Phased extraction, lowest-risk first**

| Phase | Action | Risk | Rationale |
| ----- | ------ | ---- | --------- |
| 1 | Extract `hook-manager` | Low | `hooks.py` is fully self-contained |
| 2 | Extract `claude-md-manager` | Low | `claude_md.py` minimal shared dependencies |
| 3 | Split extensions into `agent-manager` + `skill-manager` | Medium | Share 7 utils functions; more logic |
| 4 | Merge `create-plugin` into `plugin-manager` + extraction | Medium | Cross-skill template path update needed |
| 5 | Update `aida` routing + remove old skills | Low | After managers are stable |

### Decision 2: Operations-per-File vs. Monolithic Operations Module

The architecture research proposes splitting `extensions.py` into
`create.py`, `validate.py`, `version.py`, `list.py` per manager.

**Recommendation: Start with one `extensions.py` per manager, then split
if operations grow.**

Each manager's `extensions.py` will be much smaller than the current monolith's
987-line `extensions.py` (roughly one-third the lines for each entity type).
Operation-per-file adds complexity without immediate benefit at that size.
Refactor when any single file exceeds ~400 lines.

### Decision 3: Template Ownership

**Recommendation: Per-manager templates (Option A from architecture research)**

- `agent-manager/templates/agent.md.jinja2`
- `skill-manager/templates/SKILL.md.jinja2`
- `plugin-manager/templates/extension/` and `templates/scaffold/`
- `hook-manager/` has no templates (hooks are JSON config, not files)
- `claude-md-manager/templates/claude-md/`

After split, update `create-plugin/scaffold.py`'s `CCM_TEMPLATES_DIR`:

```python
# Before:
CCM_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "claude-code-management" / "templates"

# After (per component):
AGENT_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "agent-manager" / "templates"
SKILL_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "skill-manager" / "templates"
```

This becomes a non-issue once `create-plugin` merges into `plugin-manager`.

### Decision 4: Shared Utilities Import Pattern

**Recommendation: Adopt `_paths.py` pattern per manager**

The current `operations/utils.py` re-export shim uses fragile relative
path climbing. The architecture research recommends following the `permissions`
skill's `scripts/_paths.py` pattern:

```python
# Each manager's scripts/_paths.py
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # adjust as needed
SHARED_UTILS = PROJECT_ROOT / "scripts" / "shared"
```

Then in each operations module:
```python
import sys
from scripts._paths import SHARED_UTILS
sys.path.insert(0, str(SHARED_UTILS))
from utils import safe_json_load, validate_name, ...
```

### Decision 5: COMPONENT_TYPES Split Strategy

The current `extensions.py` uses a shared `COMPONENT_TYPES` dict that
drives behavior for agents, skills, and plugins. After the split, each
manager defines its own configuration.

**Recommendation: Inline constants per manager, not a shared config.**

Agents, skills, and plugins differ enough that a shared `COMPONENT_TYPES`
is premature abstraction. Each manager defines:
- Its own directory name (`agents/`, `skills/`, etc.)
- Its own file pattern (`{name}.md`, `SKILL.md`)
- Its own template path (relative to its own `templates/`)
- Its own frontmatter schema
- Its own output contract for spawning `claude-code-expert`

If a `BaseExtensionManager` class emerges naturally after the split, add
it then. Do not create it upfront.

---

## Part 5: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Breaking `/aida` commands during transition | Medium | High | Phased extraction; old skill stays until new one is tested |
| Template path breaks for `create-plugin` | Medium | Medium | Fix in Phase 4 (plugin-manager merge) |
| Shared utils import failures | Medium | Medium | Adopt `_paths.py` pattern from start |
| Test coverage gaps during split | Medium | Medium | Move tests with code; run full suite per phase |
| `extensions.py` logic duplication across managers | Low | Low | Acceptable until patterns stabilize; refactor after |
| Context window overhead (more skill files) | Low | Low | Only one manager loads per request; net improvement |
| `claude-code-expert` generates outdated artifacts | High (current state) | High | Fix knowledge base BEFORE implementing managers |

**Most critical risk:** The `claude-code-expert` knowledge base has outdated
hook names, missing skills/subagents documentation, and missing plugin
component types. If managers invoke this agent before the knowledge base
is updated, they will generate incorrect or incomplete artifacts.

---

## Part 6: Knowledge Base Updates Required

The framework review and docs research converge on the same priority list.
These must be addressed **before implementing manager skills**:

### Before Implementation (Blocking)

1. **Create `knowledge/skills.md`** -- Skills frontmatter expanded; new fields
   (`context`, `agent`, `hooks`, `model`); substitution syntax; context modes;
   Agent Skills open standard; skill discovery; SLASH_COMMAND_TOOL_CHAR_BUDGET
2. **Create `knowledge/subagents.md`** -- Built-in subagents; expanded frontmatter
   (`permissionMode`, `maxTurns`, `memory`, `background`, `isolation`, `mcpServers`,
   `hooks`); persistent memory; worktree isolation; background execution
3. **Fix `knowledge/settings.md`** -- Hook event names (`PreToolUse` not
   `preToolExecution`); hook configuration structure (nested `hooks` array +
   `type` field); current model names
4. **Update `knowledge/hooks.md`** -- 7 new hook events; 3 hook types (`command`,
   `prompt`, `agent`); async hooks; JSON output format with `hookSpecificOutput`

### During Implementation

5. **Update `knowledge/plugin-development.md`** -- LSP servers, MCP servers,
   plugin-level `hooks/hooks.json`, `settings.json`, `outputStyles/`, CLI
   commands, `${CLAUDE_PLUGIN_ROOT}`, caching behavior
6. **Update `knowledge/framework-design-principles.md`** -- Hook determinism
   qualifier (only `command` hooks are deterministic; `prompt`/`agent` involve LLM)
7. **Update `knowledge/index.md`** -- Fix external resource URLs; add entries
   for new knowledge files
8. **Update `knowledge/settings.md`** -- Outdated model names; missing settings
   fields (23+ new fields documented)

### After Implementation

9. Update `knowledge/claude-md-files.md` -- Auto memory, CLAUDE.local.md,
   rules system, import approval, enterprise path correction
10. Update `knowledge/extension-types.md` -- Agent teams note, plugin invocation
11. Update `knowledge/design-patterns.md` -- LSP/MCP bundling patterns
12. Create `knowledge/agent-teams.md` -- Full agent teams documentation
13. Create `knowledge/mcp.md` -- Dedicated MCP configuration guide

---

## Part 7: Suggested Issue Breakdown

### Sub-issue A: Update claude-code-expert Knowledge Base
**Priority: Blocker for all implementation work**

Scope:
- Create `skills.md` and `subagents.md`
- Fix `settings.md` hook names and structure
- Update `hooks.md` (new events and hook types)
- Update `index.md` URLs

### Sub-issue B: Extract hook-manager
**Priority: First implementation (lowest risk)**

Scope:
- Create `skills/hook-manager/SKILL.md`
- Move `operations/hooks.py` (minimal changes)
- Create simplified `hook-manager/scripts/manage.py`
- Update aida routing
- Move/update tests from `tests/test_hooks.py`

### Sub-issue C: Extract claude-md-manager
**Priority: Second implementation**

Scope:
- Create `skills/claude-md-manager/SKILL.md`
- Move `operations/claude_md.py` (minimal changes)
- Move claude-md templates
- Move claude-md references (`claude-md-workflow.md`, `best-practices.md`)
- Create simplified entry point
- Update aida routing
- Move tests from `tests/unit/test_claude_md.py`

### Sub-issue D: Extract agent-manager and skill-manager
**Priority: Third implementation (requires extensions.py split)**

Scope:
- Split `extensions.py` into agent-specific and skill-specific modules
- Create `skills/agent-manager/` and `skills/skill-manager/`
- Move agent templates, skill templates respectively
- Move extension references, split agent/skill schemas
- Update aida routing
- Update tests

### Sub-issue E: Create plugin-manager (merge create-plugin)
**Priority: Fourth implementation (largest change)**

Scope:
- Create `skills/plugin-manager/SKILL.md`
- Extract plugin operations from `extensions.py`
- Merge `create-plugin` skill into `plugin-manager`
- Reorganize templates: `extension/` and `scaffold/`
- Remove `create-plugin` skill
- Update all cross-references to CCM templates
- Update `plugin-development.md` with new plugin structure
- Update tests

### Sub-issue F: Remove claude-code-management and update aida routing
**Priority: Fifth (cleanup after all managers stable)**

Scope:
- Remove `skills/claude-code-management/`
- Finalize aida routing table (clean, entity-direct)
- Update help text
- Add cross-cutting convenience operations (`/aida validate --all`)
- Update all tests that reference CCM paths

---

## Part 8: TypeScript / MCP Considerations

### Plugin Development is NOT TypeScript

Confirmed by docs research: Claude Code plugins are markdown-based, not
TypeScript packages. Skills are SKILL.md files. Agents are .md files. No
TypeScript compilation required.

**Implication for managers:** No TypeScript API concerns. All managers will
continue using Python scripts + Jinja2 templates + markdown SKILL.md files.

### MCP Servers CAN Be TypeScript

MCP servers bundled within plugins CAN be TypeScript/Node applications
(using `npx -y @some/mcp-server` pattern). The `plugin-manager` scaffold
templates should optionally support generating an MCP server stub alongside
plugin scaffolding.

This is a follow-on capability, not a v1.0 requirement. For v1.0:
- `plugin-manager scaffold` generates the expanded plugin structure
  (with `.mcp.json` and `.lsp.json` stubs if user opts in)
- Actual MCP server code generation is deferred to a future `mcp-manager`

### Agent SDK

The Agent SDK (`https://platform.claude.com/docs/en/agent-sdk/overview`)
provides programmatic access to Claude Code capabilities for building custom
agents outside of Claude Code. This is separate from extension development
and does not affect the manager skill architecture.

**No action required** for the decomposition. The Agent SDK is for users
building external tools, not for AIDA plugin extensions.

### Skills Open Standard

Skills now conform to the Agent Skills open standard (agentskills.io), which
works across multiple AI tools. Our manager skills will generate SKILL.md
files that conform to this standard. No special TypeScript or SDK work needed.

The main practical implication: the `skills.md` knowledge file we create
should reference the Agent Skills standard, and our SKILL.md templates should
include the fields required for cross-tool compatibility.

---

## Part 9: Summary Table

| Topic | Decision | Owner |
| ----- | -------- | ----- |
| Naming convention | `*-manager` consistently (including `skill-manager`) | - |
| `marketplace-manager` | Defer to follow-on issue | - |
| `mcp-manager` | Defer until MCP matures | - |
| `create-plugin` merge | Yes, into `plugin-manager` | Sub-issue E |
| Template organization | Per-manager (each owns its templates) | Sub-issues B-E |
| Shared utilities | Keep `scripts/shared/utils.py`; adopt `_paths.py` | Sub-issues B-E |
| Operations structure | One `extensions.py` per manager initially | Sub-issues D-E |
| Extraction order | hooks → claude-md → agent+skill → plugin → cleanup | Sub-issues B-F |
| Knowledge base updates | Critical gap (skills.md, subagents.md missing) | Sub-issue A |
| TypeScript | Not needed for extensions; defer MCP server scaffolding | - |
| Command grammar | Unchanged (zero user-facing change) | - |
| Cross-cutting ops | `validate --all` at aida dispatcher level | Sub-issue F |
