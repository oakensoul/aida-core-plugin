---
type: research
title: "Architecture Analysis: Decomposing claude-code-management"
author: system-architect
date: "2026-02-24"
issue: 31
---

# Architecture Analysis: Decomposing claude-code-management

## Executive Summary

The current `claude-code-management` skill is a monolithic dispatcher that
handles six distinct entity domains (agents, skills, plugins, hooks,
CLAUDE.md, and marketplace) through a single entry point (`manage.py`).
The `aida` skill routes to it as a middleman, creating three layers of
indirection: `/aida` -> `claude-code-management` -> internal dispatch.

This analysis evaluates the proposed decomposition into entity-focused
manager skills and provides recommendations on naming, shared code
strategy, template organization, routing changes, and scope questions.

---

## 1. Current Architecture Assessment

### What Exists Today

```text
skills/
  aida/SKILL.md              # Router: dispatches /aida commands
  claude-code-management/     # Monolith: handles agents, skills, plugins,
                              #   hooks, CLAUDE.md
    SKILL.md                  # 590-line skill definition
    scripts/
      manage.py               # Dispatcher: routes to operations modules
      operations/
        extensions.py          # 36KB - agents, skills, plugins (create,
                               #   validate, version, list)
        hooks.py               # 16KB - hooks (list, add, remove, validate)
        claude_md.py           # 28KB - CLAUDE.md (create, optimize,
                               #   validate, list)
        utils.py               # Re-exports from scripts/shared/utils.py
    templates/
      agent/                   # Agent Jinja2 templates
      skill/                   # Skill Jinja2 templates
      plugin/                  # Plugin Jinja2 templates (create inside
                               #   existing project)
      claude-md/               # CLAUDE.md templates
    references/
      create-workflow.md       # Extension create workflow (deprecated)
      validate-workflow.md     # Extension validation rules
      schemas.md               # Frontmatter schema reference
      claude-md-workflow.md    # CLAUDE.md create/optimize workflow
      best-practices.md        # CLAUDE.md best practices and scoring
  create-plugin/              # Separate skill: scaffolds new plugin projects
    SKILL.md
    scripts/scaffold.py
    templates/{shared,python,typescript}/
```

### Problems with Current Architecture

1. **Three layers of indirection**: `/aida agent create` -> aida SKILL.md
   -> claude-code-management SKILL.md -> manage.py -> extensions.py.
   The middle layer adds no value beyond routing.

2. **Monolithic SKILL.md**: At 590 lines, the skill definition covers
   extension operations, hook operations, and CLAUDE.md operations in a
   single document. The orchestrator must load all of this context even
   when the user only needs hook operations.

3. **Anti-pattern**: The `design-patterns.md` knowledge file explicitly
   calls out "Monolithic Skills" as an anti-pattern. A 500+ line skill
   with everything bundled violates Single Responsibility.

4. **Confusing `manage.py` dispatch**: The Python entry point duplicates
   the routing logic that belongs in the skill layer (or the aida
   dispatcher). It checks `is_hook_operation()` and
   `is_claude_md_operation()` with fragile heuristics like "has scope
   but type is not agent/skill/plugin/hook."

5. **Context waste**: When the user runs `/aida hook list`, the
   orchestrator loads the entire claude-code-management SKILL.md (all
   extension contracts, all CLAUDE.md workflows) into context. Only the
   hook section is relevant.

6. **Inconsistent scoping**: `create-plugin` (project scaffolding) is
   already a separate skill, but "create plugin extension inside an
   existing project" is buried inside claude-code-management. The user
   model is split.

---

## 2. Naming Convention Analysis

### The Core Question

The issue calls out the awkwardness of `skills/skill-manager/` -- a skill
that manages skills. Several naming patterns were considered:

| Pattern | Agent Example | Skill Example | Pros | Cons |
|---------|--------------|---------------|------|------|
| `*-manager` | `agent-manager` | `skill-manager` | Clear role, consistent | `skill-manager` is confusing |
| `*-ops` | `agent-ops` | `skill-ops` | Short, DevOps-friendly | Less descriptive |
| `manage-*` | `manage-agents` | `manage-skills` | Verb-first, clear | Inconsistent with existing naming |
| `*-crud` | `agent-crud` | `skill-crud` | Technical precision | Too implementation-focused |
| Entity name only | `agents` | `skills` | Simplest | Collides with `agents/` directory |

### Recommendation: `*-manager` with One Exception

Use the `*-manager` pattern consistently. For the skill-managing-skills
case, use `skill-manager` but mitigate confusion through documentation:

- The **directory** `skills/skill-manager/` contains a **skill** named
  `skill-manager` that **manages skill extensions**
- This parallels `skills/permissions/` -- a skill named `permissions`
  that manages permissions. The naming follows the same pattern.

**Rationale**: The `*-manager` suffix is the strongest signal of purpose.
Every alternative introduces its own confusion or inconsistency. The
`skill-manager` case is a one-time oddity that documentation resolves.
Users will invoke `/aida skill create`, not `/aida skill-manager create`
-- the directory name is internal to the plugin structure.

### Proposed Skill Names

| Skill Directory | SKILL.md `name:` | Routes From |
|-----------------|-------------------|-------------|
| `agent-manager` | `agent-manager` | `/aida agent [...]` |
| `skill-manager` | `skill-manager` | `/aida skill [...]` |
| `plugin-manager` | `plugin-manager` | `/aida plugin [create\|validate\|version\|list\|add\|remove]` |
| `hook-manager` | `hook-manager` | `/aida hook [...]` |
| `claude-md-manager` | `claude-md-manager` | `/aida claude [...]` |

---

## 3. Shared Utilities Strategy

### Current Shared Code

The project already has a shared utilities layer:

```text
scripts/shared/utils.py     # Project-level shared utilities
```

This contains: `safe_json_load`, `to_kebab_case`, `validate_name`,
`validate_description`, `validate_version`, `bump_version`,
`parse_frontmatter`, `render_template`, `get_project_root`,
`LOCATION_PATHS`, `get_location_path`.

The current `operations/utils.py` in claude-code-management is just a
re-export shim that adds `scripts/shared/` to `sys.path`.

### What Should Stay Shared vs. Move Per-Manager

**Keep in `scripts/shared/utils.py`** (used by 2+ managers):

- `safe_json_load` -- every manager needs JSON parsing
- `to_kebab_case` -- used by agent, skill, plugin managers
- `validate_name` / `validate_description` / `validate_version` --
  extension validation is shared across agent, skill, plugin
- `bump_version` -- version operations exist for agent, skill, plugin
- `parse_frontmatter` -- used by agent, skill, plugin, claude-md
- `render_template` -- used by agent, skill, plugin, claude-md, hooks
- `get_project_root` -- used everywhere
- `get_location_path` / `LOCATION_PATHS` -- used by extension managers

**Move per-manager** (domain-specific logic):

- `COMPONENT_TYPES` dict (from `extensions.py`) -- split into each
  extension manager's own constants
- `find_components()` -- refactor: each manager has its own
  `find_agents()`, `find_skills()`, etc.
- Hook-specific constants (`VALID_EVENTS`, `HOOK_TEMPLATES`) stay in
  hook-manager
- CLAUDE.md-specific constants (`REQUIRED_SECTIONS`, `TEMPLATES`) stay
  in claude-md-manager

### Recommendation

The existing `scripts/shared/utils.py` pattern is sound. Each new
manager skill imports from it. No need to create a new shared layer --
just ensure the import mechanism is clean (avoid the fragile
`sys.path.insert` with relative directory climbing).

**Improvement**: Consider adding a `conftest.py` or `_paths.py` pattern
(as `permissions` skill already uses `scripts/_paths.py`) to make
imports reliable. Each manager's `scripts/` can have a small `_paths.py`
that resolves the project root and adds `scripts/shared/` to the path.

---

## 4. Template Organization

### Current Template Layout

```text
claude-code-management/templates/
  agent/agent.md.jinja2
  skill/SKILL.md.jinja2
  plugin/{plugin.json, README.md, gitignore}.jinja2
  claude-md/{project, user, plugin}.md.jinja2
```

Additionally, `create-plugin/templates/` has its own set of templates
for project scaffolding (shared/, python/, typescript/).

### Options Evaluated

**Option A: Per-Manager Templates** (recommended)

```text
skills/agent-manager/templates/agent.md.jinja2
skills/skill-manager/templates/SKILL.md.jinja2
skills/plugin-manager/templates/{plugin.json, README.md, gitignore}.jinja2
skills/hook-manager/templates/   # (if hook templates are needed)
skills/claude-md-manager/templates/{project, user, plugin}.md.jinja2
```

**Option B: Shared Template Library**

```text
templates/                    # Top-level shared templates
  agent/agent.md.jinja2
  skill/SKILL.md.jinja2
  ...
```

**Option C: Hybrid**

Templates that are used by a single manager live with that manager.
Templates referenced cross-skill (e.g., `create-plugin` references CCM
templates for agent/skill stubs) go in a shared location.

### Recommendation: Option A (Per-Manager) with Cross-References

Each manager owns its templates. This follows the existing pattern where
`create-plugin` has its own `templates/` directory, and `memento` has
its own `templates/` directory.

For the cross-reference case: `create-plugin/SKILL.md` currently says
"CCM Templates: Agent and skill stubs reference templates from
`{project_root}/skills/claude-code-management/templates/`". After
decomposition, `create-plugin` would reference
`{project_root}/skills/agent-manager/templates/` and
`{project_root}/skills/skill-manager/templates/` instead. This is
actually cleaner -- explicit references to the owning manager.

---

## 5. Routing Changes in the `aida` Skill

### Current Routing (aida/SKILL.md)

```text
/aida agent|skill|plugin|hook [op] → claude-code-management skill
/aida claude [op]                  → claude-code-management skill
/aida plugin scaffold              → create-plugin skill (special case)
/aida memento [op]                 → memento skill
/aida config permissions           → permissions skill
/aida status|doctor|upgrade        → inline scripts
/aida config                       → inline references
/aida feedback|bug|feature-request → inline references
/aida help                         → inline text
```

### Proposed Routing (after decomposition)

```text
/aida agent [op]                   → agent-manager skill
/aida skill [op]                   → skill-manager skill
/aida plugin scaffold              → plugin-manager skill (absorbs
                                       create-plugin; see Section 8)
/aida plugin [op]                  → plugin-manager skill
/aida hook [op]                    → hook-manager skill
/aida claude [op]                  → claude-md-manager skill
/aida marketplace [op]             → marketplace-manager skill (new; see
                                       Section 7)
/aida memento [op]                 → memento skill (unchanged)
/aida config permissions           → permissions skill (unchanged)
/aida status|doctor|upgrade        → inline scripts (unchanged)
/aida config                       → inline references (unchanged)
/aida feedback|bug|feature-request → inline references (unchanged)
/aida help                         → inline text (updated to reflect
                                       new commands)
```

### Key Changes

1. **Remove the claude-code-management indirection entirely.** The aida
   skill directly routes to the appropriate manager skill.

2. **Each route is a simple entity match.** No need for the aida skill
   to parse operations -- it just identifies the entity noun and
   delegates. The manager skill handles operation parsing.

3. **The `plugin scaffold` special case goes away.** Instead of
   matching `plugin scaffold` before the general `plugin` route,
   `plugin-manager` handles all plugin operations including scaffolding.

4. **Help text updates.** Add `/aida marketplace` commands to the help
   section.

### Routing Simplification

The aida SKILL.md routing section becomes significantly simpler:

```text
### Extension Management Commands

For `agent` → invoke `agent-manager` skill
For `skill` → invoke `skill-manager` skill
For `plugin` → invoke `plugin-manager` skill
For `hook` → invoke `hook-manager` skill
For `claude` → invoke `claude-md-manager` skill
For `marketplace` → invoke `marketplace-manager` skill
```

This eliminates the complex "Extension Management Commands" section that
currently must explain how claude-code-management works internally.

---

## 6. Whether to Add a `marketplace-manager` Skill

### Analysis

The issue's target architecture includes `marketplace-manager`. Looking
at the codebase:

- ADR-008 defines the marketplace-centric distribution model
- `create-plugin` already generates `marketplace.json` files
- The `agents/claude-code-expert/knowledge/plugin-development.md` and
  `knowledge/index.md` reference marketplace concepts
- No existing management operations for marketplace exist yet

### Recommendation: Yes, but as a Stub in v1.0

Create `marketplace-manager` as a minimal skill with:

- `list` -- list installed marketplaces and available plugins
- `validate` -- validate marketplace.json in current plugin
- Future: `publish`, `search`, `install`

**Rationale**: The routing architecture should be designed for the full
entity set from the start. Adding the stub now means the aida routing
table and help text are complete. Implementation can be incremental.

If marketplace functionality is not ready for v1.0, the skill can
simply return a "coming soon" message for unimplemented operations while
still having the route reserved.

---

## 7. Whether to Add an `mcp-manager` Skill

### Analysis

MCP (Model Context Protocol) servers are an emerging extension point in
Claude Code. They allow plugins to expose tools via a standardized
protocol.

### Recommendation: Not Yet

MCP server management is not part of the current AIDA extension type
taxonomy (agent, skill, plugin, hook, CLAUDE.md, marketplace). Adding
it now would require:

1. Defining MCP as a new extension type in the framework
2. Updating `extension-types.md` and `framework-design-principles.md`
3. Creating discovery, validation, and lifecycle operations

This is better suited for a separate issue once MCP server support
matures in the Claude Code ecosystem. The decomposition should focus on
splitting existing functionality, not adding new entity types.

**If MCP management is needed sooner**, it could initially live as
operations within `plugin-manager` since MCP servers are packaged
within plugins. This follows the same pattern as `plugin scaffold`
being inside `plugin-manager`.

---

## 8. Whether `create-plugin` Should Merge into `plugin-manager`

### Analysis

Current state:

- `create-plugin` skill: scaffolds a brand new plugin **project** (git
  repo, language tooling, CI, etc.)
- `claude-code-management` plugin operations: creates plugin
  **extensions** inside an existing project, validates, versions, lists

The distinction is:

| Aspect | `create-plugin` | CCM Plugin Ops |
|--------|-----------------|----------------|
| Creates | New git repository | Files in existing project |
| Scope | Full project scaffold | Extension inside project |
| Templates | 30+ templates (shared/python/typescript) | 3 templates |
| Script | scaffold.py (400+ lines) | extensions.py (shared) |
| Output | Complete project directory | Component files |

### Recommendation: Merge into `plugin-manager`

**Merge `create-plugin` into `plugin-manager`** as one operation among
several, for these reasons:

1. **User model clarity**: `/aida plugin scaffold` and `/aida plugin
   create` both live under the `plugin` noun. Having them in the same
   manager skill is intuitive.

2. **The aida skill already handles this as a special case**: The
   current routing has a comment saying "Match this command BEFORE the
   general extension management commands." This special-casing
   disappears when both operations are in `plugin-manager`.

3. **Self-contained skill**: `plugin-manager` becomes the single
   authority on all plugin operations: scaffold, create (extension
   inside project), validate, version, list, add, remove.

4. **Precedent**: The `permissions` skill handles both interactive
   setup and audit mode -- different scopes of operation within one
   skill.

### Migration Plan

```text
skills/plugin-manager/
  SKILL.md                    # All plugin operations
  scripts/
    manage.py                 # Plugin operations dispatcher
    operations/
      extensions.py           # Create/validate/version/list
      scaffold.py             # Project scaffolding (from create-plugin)
      scaffold_ops/           # Scaffolding helpers (from create-plugin)
        context.py
        generators.py
        licenses.py
  templates/
    extension/                # Templates for creating plugin extensions
      plugin.json.jinja2
      README.md.jinja2
      gitignore.jinja2
    scaffold/                 # Project scaffolding templates
      shared/                 # (from create-plugin/templates/shared/)
      python/                 # (from create-plugin/templates/python/)
      typescript/             # (from create-plugin/templates/typescript/)
  references/
    scaffolding-workflow.md   # (from create-plugin/references/)
    validate-workflow.md      # Plugin-specific validation
    schemas.md                # Plugin-specific schemas
```

### TypeScript Scaffolding Templates

The TypeScript templates in `create-plugin/templates/typescript/`
(package.json, tsconfig, eslint, vitest, etc.) move into
`plugin-manager/templates/scaffold/typescript/`. They are specifically
for project scaffolding, not for creating extensions, so the
subdirectory grouping under `scaffold/` keeps them separate from
extension templates.

---

## 9. Proposed Target Architecture

### Directory Structure

```text
skills/
  aida/                       # Router (simplified dispatch)
    SKILL.md                  # Lean routing table
    scripts/                  # (unchanged - status, doctor, etc.)
    references/               # (unchanged)
    templates/                # (unchanged)

  agent-manager/              # Agent CRUD operations
    SKILL.md
    scripts/
      manage.py               # Entry point
      operations/
        create.py
        validate.py
        version.py
        list.py
    templates/
      agent.md.jinja2
    references/
      create-workflow.md      # Agent-specific create workflow
      validate-workflow.md    # Agent-specific validation
      schemas.md              # Agent frontmatter schema

  skill-manager/              # Skill CRUD operations
    SKILL.md
    scripts/
      manage.py
      operations/
        create.py
        validate.py
        version.py
        list.py
    templates/
      SKILL.md.jinja2
    references/
      create-workflow.md
      validate-workflow.md
      schemas.md

  plugin-manager/             # Plugin ops + scaffolding (merged)
    SKILL.md
    scripts/
      manage.py
      operations/
        create.py             # Extension inside existing project
        validate.py
        version.py
        list.py
        scaffold.py           # New project scaffolding
        scaffold_ops/
          context.py
          generators.py
          licenses.py
    templates/
      extension/              # Plugin extension templates
        plugin.json.jinja2
        README.md.jinja2
        gitignore.jinja2
      scaffold/               # Project scaffolding templates
        shared/
        python/
        typescript/
    references/
      scaffolding-workflow.md
      validate-workflow.md
      schemas.md

  hook-manager/               # Hook operations
    SKILL.md
    scripts/
      manage.py
      operations/
        list.py
        add.py
        remove.py
        validate.py
    templates/                # Hook templates (formatter, logger, etc.)
    references/

  claude-md-manager/          # CLAUDE.md operations
    SKILL.md
    scripts/
      manage.py
      operations/
        create.py
        optimize.py
        validate.py
        list.py
    templates/
      project.md.jinja2
      user.md.jinja2
      plugin.md.jinja2
    references/
      claude-md-workflow.md
      best-practices.md

  marketplace-manager/        # Marketplace operations (stub)
    SKILL.md
    scripts/
      manage.py               # Minimal implementation
    references/

  memento/                    # (unchanged)
  permissions/                # (unchanged)

scripts/
  shared/
    utils.py                  # (unchanged - shared utilities)
```

### Operation-per-File vs. Monolithic Operations Module

The current `extensions.py` is 36KB because it handles create, validate,
version, and list for all three extension types. The proposed split has
two axes:

1. **By entity** (agent, skill, plugin) -- each gets its own manager
2. **By operation** (create, validate, version, list) -- each gets its
   own file within the manager

This means `agent-manager/scripts/operations/create.py` only contains
agent creation logic. This is much easier to maintain, test, and reason
about than the current structure.

However, for the initial decomposition, it is acceptable to have a
single `operations.py` per manager if the entity's operations are
compact. The operation-per-file split can be a follow-up refinement.

---

## 10. Decomposition Strategy: How to Execute

### Recommended Approach: Extract One Manager at a Time

**Phase 1: Extract `hook-manager`** (lowest risk)

- Hooks are the most self-contained domain
- `operations/hooks.py` has minimal dependencies on shared extension logic
- No cross-references from other skills
- Good proof-of-concept for the pattern

**Phase 2: Extract `claude-md-manager`**

- Also self-contained
- `operations/claude_md.py` depends only on shared utils
- References (best-practices.md, claude-md-workflow.md) are
  domain-specific

**Phase 3: Split extension types into `agent-manager`, `skill-manager`,
`plugin-manager`**

- This is the largest refactor: splitting `extensions.py` (36KB)
- Share `find_components()` pattern but specialize per entity
- Merge `create-plugin` into `plugin-manager`

**Phase 4: Add `marketplace-manager` stub**

- Minimal skill with placeholder operations
- Wire up routing in aida SKILL.md

**Phase 5: Remove `claude-code-management` and `create-plugin`**

- Delete the old monolith
- Update all cross-references
- Update tests

### Test Strategy

Each phase should include:

1. Extract the manager skill
2. Create manager-specific tests (can start by moving existing tests)
3. Update aida routing to use the new manager
4. Verify old tests still pass (for remaining monolith operations)
5. Remove the old code from the monolith

---

## 11. Impact on `extensions.py` Split

The current `extensions.py` handles three entity types through a shared
`COMPONENT_TYPES` dictionary and shared functions like
`find_components()`, `create_component()`, `validate_component()`, etc.

### What Becomes Shared (stays in `scripts/shared/`)

Functions that are truly generic across agents, skills, and plugins:

- Name/description/version validation
- Kebab-case conversion
- Frontmatter parsing
- Template rendering
- Location path resolution
- Project root detection

### What Gets Specialized (moves to each manager)

- `COMPONENT_TYPES` entries -- each manager defines its own config
- `find_components()` -- becomes `find_agents()`, `find_skills()`,
  `find_plugins()` with entity-specific logic
- Agent output contracts -- each manager defines its own
- Template paths -- each manager owns its templates

### New Shared Abstractions (optional)

If the agent-manager, skill-manager, and plugin-manager share enough
structure, a `scripts/shared/extension_base.py` could provide:

```python
class ExtensionManager:
    """Base class for extension managers."""
    component_type: str
    directory: str
    file_pattern: str
    template: str

    def find(self, location, plugin_path=None): ...
    def create(self, context, responses, templates_dir): ...
    def validate(self, context): ...
    def version(self, context): ...
    def list(self, context): ...
```

However, this should only be introduced if the three managers genuinely
share enough logic to justify the abstraction. Over-abstracting
prematurely is an anti-pattern per the project's own design-patterns.md.
Start with duplication, then extract if a clear pattern emerges.

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing `/aida` commands | Medium | High | Phased extraction with routing fallback |
| Shared utils import failures | Medium | Medium | Standardize import pattern (_paths.py) |
| Test coverage gaps during split | Medium | Medium | Move tests with code, verify each phase |
| Template path resolution breaks | Low | Medium | Each manager resolves relative to its own SKILL_DIR |
| Cross-skill references break | Low | Low | Update create-plugin references during plugin-manager merge |
| Context window overhead from more skills | Low | Low | Only one manager loads at a time (already true) |

---

## 13. Summary of Recommendations

| Decision | Recommendation |
|----------|---------------|
| Naming convention | `*-manager` consistently (including `skill-manager`) |
| Shared utilities | Keep `scripts/shared/utils.py`; add `_paths.py` per manager |
| Template organization | Per-manager templates; cross-reference by project path |
| Routing changes | Direct entity-to-manager routing; remove CCM indirection |
| `marketplace-manager` | Yes, as a stub in v1.0 |
| `mcp-manager` | Not yet; revisit when MCP support matures |
| `create-plugin` merge | Yes, merge into `plugin-manager` |
| TypeScript templates | Move to `plugin-manager/templates/scaffold/typescript/` |
| Extraction order | hooks -> claude-md -> extensions split -> marketplace -> cleanup |
| New shared abstractions | Only if duplication warrants it after initial split |
