# Codebase Deep Dive: claude-code-management Decomposition Analysis

## 1. Current Architecture Overview

The monolithic `claude-code-management` skill is a single entry point (`manage.py`)
that dispatches to three operation modules via target/type detection:

```text
manage.py (router)
  ├── operations/extensions.py   → agents, skills, plugins (create/validate/version/list)
  ├── operations/claude_md.py    → CLAUDE.md files (create/optimize/validate/list)
  ├── operations/hooks.py        → settings.json hooks (list/add/remove/validate)
  └── operations/utils.py        → re-exports from scripts/shared/utils.py
```

Entry point: `skills/claude-code-management/scripts/manage.py`

## 2. Dependency Map

### 2.1 Import Graph

```text
manage.py
  ├── operations.utils.safe_json_load
  ├── operations.extensions  (full module)
  ├── operations.claude_md   (full module)
  └── operations.hooks       (full module)

operations/utils.py
  └── scripts/shared/utils.py (re-exports ALL symbols)

operations/extensions.py
  ├── json, re, datetime, pathlib, typing
  ├── yaml (PyYAML)
  └── operations.utils: to_kebab_case, validate_name, validate_description,
      validate_version, bump_version, get_location_path, render_template

operations/claude_md.py
  ├── json, re, sys, datetime, pathlib, typing
  └── operations.utils: get_project_root, parse_frontmatter, render_template
  └── (optional) aida/scripts/utils/inference module (dynamic import with fallback)

operations/hooks.py
  ├── json, pathlib, typing
  └── NO imports from operations.utils (fully self-contained)

scripts/shared/utils.py
  ├── json, re, functools, pathlib, typing
  └── jinja2 (lazy import inside render_template)
```

### 2.2 Cross-Module Dependencies

| Module | Depends On (from shared utils) |
| --- | --- |
| `extensions.py` | `to_kebab_case`, `validate_name`, `validate_description`, `validate_version`, `bump_version`, `get_location_path`, `render_template` |
| `claude_md.py` | `get_project_root`, `parse_frontmatter`, `render_template` |
| `hooks.py` | **Nothing** (fully independent) |
| `manage.py` | `safe_json_load` only |

### 2.3 Template Dependencies

| Module | Templates Used |
| --- | --- |
| `extensions.py` | `agent/agent.md.jinja2`, `skill/SKILL.md.jinja2`, `plugin/plugin.json.jinja2`, `plugin/README.md.jinja2`, `plugin/gitignore.jinja2` |
| `claude_md.py` | `claude-md/project.md.jinja2`, `claude-md/user.md.jinja2`, `claude-md/plugin.md.jinja2` |
| `hooks.py` | **None** (generates JSON configuration, not files from templates) |

### 2.4 Cross-Skill Dependencies

The `create-plugin` skill depends on `claude-code-management` templates:

```python
# In scaffold.py
CCM_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "claude-code-management" / "templates"
```

Used for rendering agent stubs and skill stubs (`agent/agent.md.jinja2`,
`skill/SKILL.md.jinja2`). These are the same templates used by `extensions.py`.

## 3. Shared Code Inventory

### 3.1 scripts/shared/utils.py (11 functions + 1 constant)

All functions in the shared utils module and their consumers:

| Function | extensions.py | claude_md.py | hooks.py | manage.py | create-plugin |
| --- | --- | --- | --- | --- | --- |
| `safe_json_load` | - | - | - | YES | YES |
| `to_kebab_case` | YES | - | - | - | YES |
| `validate_name` | YES | - | - | - | YES |
| `validate_description` | YES | - | - | - | YES |
| `validate_version` | YES | - | - | - | YES |
| `bump_version` | YES | - | - | - | - |
| `parse_frontmatter` | - | YES | - | - | - |
| `render_template` | YES | YES | - | - | YES |
| `get_project_root` | - | YES | - | - | - |
| `get_location_path` | YES | - | - | - | - |
| `LOCATION_PATHS` (deprecated) | - | - | - | - | - |

### 3.2 operations/utils.py (Thin Re-Export Wrapper)

This module exists solely to re-export symbols from `scripts/shared/utils.py`.
It adds no logic of its own. It calculates the path to `scripts/shared/utils.py`
using relative parent traversal (5 levels up from its own location).

### 3.3 Functions Used by Multiple Modules

**High sharing (3+ consumers):**

- `render_template` - extensions, claude_md, create-plugin
- `validate_name` - extensions, create-plugin
- `validate_description` - extensions, create-plugin
- `validate_version` - extensions, create-plugin
- `safe_json_load` - manage.py, create-plugin
- `to_kebab_case` - extensions, create-plugin

**Single consumer:**

- `bump_version` - extensions only
- `parse_frontmatter` - claude_md only
- `get_project_root` - claude_md only
- `get_location_path` - extensions only

## 4. Module Analysis: What Each Handles

### 4.1 extensions.py (987 lines)

**Entity types:** agent, skill, plugin

**Operations:**

- `get_questions()` - Phase 1: infer metadata, detect project context, return questions
- `execute()` - Phase 2/3 router:
  - `execute_create()` - Template-based creation (legacy)
  - `execute_create_from_agent()` - Agent-output-based creation (new, Phase 3)
  - `execute_validate()` - Validate component files
  - `execute_version()` - Bump version in frontmatter
  - `execute_list()` - List components by type/location

**Key data structures:**

- `COMPONENT_TYPES` dict - Maps type to directory, file pattern, template, subdirectory flag
- `find_components()` - Searches for components across locations
- `component_exists()` - Name collision check
- `infer_from_description()` - Name/tag inference from text
- `detect_project_context()` - Language/framework/tool detection
- `validate_agent_output()` - Validates agent JSON contract
- `validate_file_frontmatter()` - YAML frontmatter validation

**Unique to extensions (not shared):**

- `COMPONENT_TYPES` configuration
- Agent output validation logic
- Frontmatter validation (uses yaml.safe_load, not the simple parser in shared utils)
- Two creation modes (template-based and agent-based)

### 4.2 claude_md.py (912 lines)

**Entity:** CLAUDE.md configuration files

**Operations:**

- `get_questions()` - Phase 1: detect context, audit existing files
- `execute()` - Phase 2 router:
  - `execute_create()` - Create new CLAUDE.md from template
  - `execute_optimize()` - Audit and fix existing CLAUDE.md
  - `execute_validate()` - Validate CLAUDE.md structure
  - `execute_list()` - List CLAUDE.md files across scopes

**Key data structures:**

- `REQUIRED_SECTIONS` / `RECOMMENDED_SECTIONS` - Validation criteria
- `TEMPLATES` dict - Maps scope to template name
- Audit scoring system (0-100 scale)

**Unique to claude_md (not shared):**

- `detect_sections()` - Markdown section parser
- `extract_commands_from_makefile()` / `extract_commands_from_package_json()`
- `extract_readme_description()`
- `detect_project_context()` - Different from extensions version! Richer, uses
  aida inference module with fallback
- `validate_claude_md()` / `calculate_audit_score()` / `generate_audit_findings()`

### 4.3 hooks.py (480 lines)

**Entity:** Lifecycle hooks in settings.json

**Operations:**

- `get_questions()` - Gather hook configuration questions
- `execute()` - Router:
  - `_execute_list()` - List hooks from settings files
  - `_execute_add()` - Add hook to settings.json
  - `_execute_remove()` - Remove hook from settings.json
  - `_execute_validate()` - Validate hook configurations

**Key data structures:**

- `VALID_EVENTS` - Enumeration of valid hook events
- `HOOK_TEMPLATES` - Common hook presets (formatter, logger, blocker, notifier)
- `SETTINGS_PATHS` - Settings file locations by scope

**Unique to hooks (not shared):**

- All settings.json I/O (`_load_settings`, `_save_settings`)
- Hook extraction from settings structure
- Hook template system
- Completely self-contained - no dependency on shared utils

### 4.4 manage.py (214 lines)

**Role:** CLI entry point and router

**Functions:**

- `is_hook_operation()` - Route detection for hooks
- `is_claude_md_operation()` - Route detection for CLAUDE.md
- `get_questions()` - Dispatches to module-specific get_questions
- `execute()` - Dispatches to module-specific execute
- `main()` - CLI argument parsing

## 5. create-plugin: Pattern Analysis

### 5.1 How It Separated from the Monolith

The `create-plugin` skill was designed as an independent skill from the start,
not extracted from `claude-code-management`. Key design decisions:

1. **Own entry point:** `scaffold.py` with its own two-phase API
   (`--get-questions` / `--execute`)
2. **Own operations package:** `scaffold_ops/` with context, generators, licenses
3. **Own templates:** `templates/shared/`, `templates/python/`, `templates/typescript/`
4. **Shared utilities via scripts/shared/utils.py:** Imports directly, not
   through operations/utils.py wrapper
5. **Cross-dependency for stubs:** References CCM templates for agent/skill stubs

### 5.2 Patterns Established

| Pattern | Detail |
| --- | --- |
| Two-phase API | `--get-questions` returns JSON questions; `--execute` does the work |
| Script + ops package | `scaffold.py` + `scaffold_ops/` mirrors `manage.py` + `operations/` |
| Shared utils import | `from shared.utils import ...` via sys.path to PROJECT_ROOT/scripts |
| Template organization | `templates/{scope}/` with Jinja2 files |
| Validation-first | Validate all inputs before executing |
| Result contract | Returns `{"success": bool, "message": str, ...}` consistently |

### 5.3 Language-Specific Template Patterns

Templates are organized into three tiers:

```text
templates/
  ├── shared/       → Language-independent (plugin.json, CLAUDE.md, README, linter configs)
  ├── python/       → Python toolchain (pyproject.toml, conftest.py, .python-version, CI)
  └── typescript/   → TypeScript toolchain (package.json, tsconfig, eslint, vitest, CI)
```

Composite files (`.gitignore`, `Makefile`) are assembled from shared + language
blocks at render time via `assemble_gitignore()` and `assemble_makefile()`.

## 6. Proposed Split Strategy

### 6.1 New Manager Skills

Based on the analysis, the monolith should decompose into three entity-focused managers:

| New Skill | Source Module | Entity Types | Current Code |
| --- | --- | --- | --- |
| `manage-extensions` | extensions.py | agents, skills, plugins | 987 lines |
| `manage-claude-md` | claude_md.py | CLAUDE.md files | 912 lines |
| `manage-hooks` | hooks.py | settings.json hooks | 480 lines |

### 6.2 What Goes Where

#### manage-extensions

```text
skills/manage-extensions/
  ├── SKILL.md
  ├── scripts/
  │   ├── manage.py              ← simplified entry point (extensions only)
  │   └── operations/
  │       ├── __init__.py
  │       ├── extensions.py      ← current extensions.py (minor refactor)
  │       └── utils.py           ← imports from scripts/shared/utils.py
  ├── templates/                 ← moved from claude-code-management/templates
  │   ├── agent/
  │   │   └── agent.md.jinja2
  │   ├── skill/
  │   │   └── SKILL.md.jinja2
  │   └── plugin/
  │       ├── plugin.json.jinja2
  │       ├── README.md.jinja2
  │       └── gitignore.jinja2
  └── references/
      ├── create-workflow.md
      ├── validate-workflow.md
      └── schemas.md
```

**Notes:**

- The `create-plugin` skill currently references CCM templates for stubs.
  After split, it would reference `manage-extensions/templates/` instead.
- Consider whether `create-plugin` stub rendering should move into
  `manage-extensions` as a shared function, or `create-plugin` should copy
  the templates it needs.

#### manage-claude-md

```text
skills/manage-claude-md/
  ├── SKILL.md
  ├── scripts/
  │   ├── manage.py              ← simplified entry point (claude-md only)
  │   └── operations/
  │       ├── __init__.py
  │       ├── claude_md.py       ← current claude_md.py (as-is)
  │       └── utils.py           ← imports from scripts/shared/utils.py
  ├── templates/
  │   └── claude-md/
  │       ├── project.md.jinja2
  │       ├── user.md.jinja2
  │       └── plugin.md.jinja2
  └── references/
      ├── claude-md-workflow.md
      └── best-practices.md
```

**Notes:**

- `claude_md.py` has its own `detect_project_context()` that is completely
  different from the one in `extensions.py`. No conflict.
- Uses `parse_frontmatter` from shared utils; `extensions.py` uses its own
  inline parsing. No shared frontmatter concern.

#### manage-hooks

```text
skills/manage-hooks/
  ├── SKILL.md
  ├── scripts/
  │   ├── manage.py              ← simplified entry point (hooks only)
  │   └── operations/
  │       ├── __init__.py
  │       └── hooks.py           ← current hooks.py (as-is, already independent)
  └── references/
      └── hooks-reference.md
```

**Notes:**

- `hooks.py` is already fully self-contained. It imports nothing from shared
  utils and uses no templates. This is the cleanest split.
- Only needs `safe_json_load` for the entry point `manage.py`, which can be
  imported directly from `scripts/shared/utils.py`.
- No templates directory needed (hooks are JSON config, not file generation).

### 6.3 What Stays Shared

The `scripts/shared/utils.py` module should remain as-is in its current location.
All new manager skills would import from it the same way `create-plugin` already
does:

```python
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from shared.utils import safe_json_load, validate_name, ...
```

The `operations/utils.py` re-export wrapper can be eliminated in each new skill.
Instead, each skill's scripts can import directly from `shared.utils`.

### 6.4 Template Organization Plan

**Current state:**

```text
skills/claude-code-management/templates/
  ├── agent/          → used by extensions.py + create-plugin stubs
  ├── skill/          → used by extensions.py + create-plugin stubs
  ├── plugin/         → used by extensions.py only
  └── claude-md/      → used by claude_md.py only
```

**Proposed state:**

```text
skills/manage-extensions/templates/
  ├── agent/agent.md.jinja2
  ├── skill/SKILL.md.jinja2
  └── plugin/{plugin.json, README.md, gitignore}.jinja2

skills/manage-claude-md/templates/
  └── claude-md/{project, user, plugin}.md.jinja2

skills/manage-hooks/
  (no templates - hooks generate JSON config directly)
```

**create-plugin cross-reference update:**

```python
# Before:
CCM_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "claude-code-management" / "templates"

# After:
EXTENSION_TEMPLATES_DIR = PROJECT_ROOT / "skills" / "manage-extensions" / "templates"
```

### 6.5 manage.py Entry Point Simplification

Each new manager skill gets a simplified `manage.py` that drops the routing logic:

**Before (monolith manage.py):**

```python
def get_questions(context):
    if is_hook_operation(context):
        return hooks.get_questions(context)
    elif is_claude_md_operation(context):
        return claude_md.get_questions(context)
    else:
        return extensions.get_questions(context)
```

**After (each manager's manage.py):**

```python
# manage-extensions/scripts/manage.py
def get_questions(context):
    return extensions.get_questions(context)

# manage-hooks/scripts/manage.py
def get_questions(context):
    return hooks.get_questions(context)
```

The routing logic moves up to the SKILL.md / orchestrator layer.

## 7. Test Impact Analysis

### Current Test Files

| Test File | Tests For | Impact |
| --- | --- | --- |
| `tests/unit/test_manage.py` | manage.py routing | Split across new manage.py files |
| `tests/unit/test_claude_md.py` | claude_md operations | Move to manage-claude-md tests |
| `tests/test_hooks.py` | hooks operations | Move to manage-hooks tests |
| `tests/unit/test_shared_utils.py` | scripts/shared/utils.py | No change (stays shared) |
| `tests/unit/test_utils.py` | operations/utils.py re-exports | Remove (wrapper eliminated) |
| `tests/unit/test_scaffold.py` | create-plugin scaffold.py | Update CCM_TEMPLATES_DIR path |
| `tests/unit/test_scaffold_context.py` | scaffold context ops | No change |
| `tests/unit/test_scaffold_generators.py` | scaffold generators | Update CCM template refs |
| `tests/unit/test_scaffold_licenses.py` | scaffold licenses | No change |
| `tests/unit/test_agent_discovery.py` | Agent finding | May need path updates |
| `tests/unit/test_plugin_discovery.py` | Plugin finding | May need path updates |
| `tests/unit/test_security_edge_cases.py` | Security tests | Review for path changes |

## 8. Risk Assessment

### Low Risk

- **hooks.py split**: Already fully independent. No shared state, no templates,
  no cross-dependencies. Can be extracted immediately.
- **claude_md.py split**: Only depends on 3 shared utility functions. Self-contained
  templates. Clean separation.

### Medium Risk

- **extensions.py split**: Has the most shared utility usage (7 functions). Also
  has the cross-dependency from `create-plugin` for stub templates.
- **Template path updates**: `create-plugin` references CCM templates. Needs
  coordinated update.

### Considerations

- The two different `detect_project_context()` functions (one in `extensions.py`,
  one in `claude_md.py`) have different signatures and return different data.
  They should NOT be unified - they serve different purposes.
- The `operations/utils.py` re-export pattern was needed when all modules lived
  under one skill. After decomposition, direct imports from `shared.utils` are
  cleaner (matching the `create-plugin` pattern).
- The monolith's `manage.py` routing logic (`is_hook_operation()`,
  `is_claude_md_operation()`) becomes unnecessary when each skill has its own
  entry point. Routing moves to the `/aida` skill dispatcher.
