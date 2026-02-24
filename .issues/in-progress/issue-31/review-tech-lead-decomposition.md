---
type: review
reviewer: tech-lead
scope: decomposition code quality
issue: 31
branch: milestone-v1.0/refactor/31-decompose-management
date: 2026-02-24
status: complete
verdict: approve-with-findings
finding_count: 14
severity_breakdown:
  bug: 2
  design: 4
  hygiene: 5
  test_gap: 3
---

# Tech Lead Code Review: Decomposition of claude-code-management

## Review Scope

All Python source files across the 5 new manager skills, their test files,
template directories, path resolution logic, and stale reference checks.

**Files reviewed**: 28 Python source files, 10 test files, template trees for
all 5 managers, the aida SKILL.md routing table, and a full-codebase grep for
stale references.

**Test suite result**: 599 tests passed, 0 failures.

---

## Overall Assessment

The decomposition is well-executed. Each manager has a clean Two-Phase API
surface, consistent directory layout, and the routing in `skills/aida/SKILL.md`
correctly dispatches all commands to the appropriate new manager skill. The
shared utilities pattern (`scripts/shared/utils.py`) is sound, and the
operations modules are well-structured.

The findings below are real issues, not style nits. Two are bugs that should be
fixed before merge; the rest are design improvements and hygiene items that
strengthen long-term maintainability.

---

## Findings

### BUG-1: hook-manager SETTINGS_PATHS evaluated at import time (severity: bug)

**File**: `skills/hook-manager/scripts/operations/hooks.py` lines 73-79

```python
SETTINGS_PATHS = {
    "user": Path.home() / ".claude" / "settings.json",
    "project": Path.cwd() / ".claude" / "settings.json",
    "local": (
        Path.cwd() / ".claude" / "settings.local.json"
    ),
}
```

`Path.cwd()` is evaluated once at module import time and the result is stored
in the module-level dictionary. If the Python process changes its working
directory after the module is imported (or if the module is imported from a
directory different from the project root), the `project` and `local` paths
will be **permanently wrong** for the rest of the process.

The `user` path uses `Path.home()` which is stable, but `project` and `local`
need to be resolved at call time, not import time.

**Fix**: Convert `SETTINGS_PATHS` to a function or property that computes
`Path.cwd()` lazily:

```python
def _get_settings_paths() -> dict[str, Path]:
    return {
        "user": Path.home() / ".claude" / "settings.json",
        "project": Path.cwd() / ".claude" / "settings.json",
        "local": Path.cwd() / ".claude" / "settings.local.json",
    }
```

Then replace all `SETTINGS_PATHS.get(...)` calls with
`_get_settings_paths().get(...)` (or cache it per call in `_execute_list`,
`_execute_add`, etc.).

---

### BUG-2: Duplicate code paths for agent-manager and skill-manager code

**Files**:
- `skills/agent-manager/scripts/operations/extensions.py`
- `skills/skill-manager/scripts/operations/extensions.py`

These two files are nearly identical (~95% shared code). The functions
`detect_project_context()`, `infer_from_description()`,
`validate_file_frontmatter()`, `validate_agent_output()`, and the
`execute_create_from_agent()` / `execute_create_from_agent()` functions are
copy-pasted with only the component type name changed.

This is not a correctness bug today, but it is a **maintenance bug**: if a fix
is applied to one file and not the other, they will silently diverge. The
`detect_project_context()` function in particular performs expensive filesystem
scanning (`cwd.glob("**/*.py")`) and should not be duplicated.

**Impact**: Medium. Does not affect correctness now, but will cause drift.

**Fix**: Extract the shared logic into `scripts/shared/extensions_common.py`
(or a similar shared module) and have both `agent-manager` and `skill-manager`
extensions import from it. The `AGENT_CONFIG` / `SKILL_CONFIG` dictionaries
already parameterize the differences nicely; the remaining shared code could
use a factory pattern or simple function parameters.

Similarly, the `plugin-manager/scripts/operations/extensions.py` has its own
copy of `detect_project_context()` (also ~95% identical) and
`validate_agent_output()`. These should be shared too.

---

### DESIGN-1: Inconsistent _paths.py patterns across managers

**Files**:
- `skills/hook-manager/scripts/_paths.py` -- adds to sys.path
- `skills/claude-md-manager/scripts/_paths.py` -- adds to sys.path
- `skills/plugin-manager/scripts/_paths.py` -- adds to sys.path, validates
- `skills/agent-manager/scripts/_paths.py` -- does NOT add to sys.path
- `skills/skill-manager/scripts/_paths.py` -- does NOT add to sys.path

For `agent-manager` and `skill-manager`, `_paths.py` merely defines constants
(`SCRIPT_DIR`, `SKILL_DIR`, `PROJECT_ROOT`, `SHARED_UTILS`, `TEMPLATES_DIR`)
but does not modify `sys.path`. Instead, their `manage.py` files do the
`sys.path.insert()` calls directly.

Meanwhile, `hook-manager`, `claude-md-manager`, and `plugin-manager` all do
the `sys.path` setup in `_paths.py` (which is the stated purpose of the file
per its docstring).

Additionally, `agent-manager/scripts/_paths.py` is never imported by
`manage.py` (manage.py sets up paths itself), making it dead code.

**Fix**: Pick one pattern and apply it consistently. The `_paths.py` approach
(used by hook-manager, claude-md-manager, plugin-manager) is the cleaner
pattern because it centralizes path setup. Update agent-manager and
skill-manager to use the same pattern:
1. Have `_paths.py` add shared scripts to `sys.path`
2. Have `manage.py` do `import _paths  # noqa: F401` as the first local import

---

### DESIGN-2: claude-md-manager manage.py imports from operations.utils, not shared.utils

**File**: `skills/claude-md-manager/scripts/manage.py` line 31

```python
from operations.utils import safe_json_load
```

While `hook-manager/scripts/manage.py` (line 31) imports from shared utils
directly:

```python
from shared.utils import safe_json_load
```

Both work because `operations/utils.py` re-exports from `shared.utils`, but
the inconsistency is confusing. The `manage.py` entry point should import from
the same canonical location across all managers.

**Impact**: Low. Functionally correct but confusing for maintainers.

---

### DESIGN-3: skill-manager uses context["type"] = "skill" (forced override) vs agent-manager uses context.setdefault("type", "agent")

**Files**:
- `skills/agent-manager/scripts/manage.py` line 60:
  `context.setdefault("type", "agent")`
- `skills/skill-manager/scripts/manage.py` line 63:
  `context["type"] = "skill"`

The agent-manager uses `setdefault`, meaning a caller could override the type
to something other than "agent" -- which would be wrong since this manager only
handles agents. The skill-manager correctly uses a hard assignment (`=`).

**Fix**: Both managers should use hard assignment (`context["type"] = ...`)
since they are dedicated single-type managers. Using `setdefault` in
agent-manager is a potential source of confusion if a caller passes
`{"type": "skill"}` to the agent-manager.

---

### DESIGN-4: detect_project_context() uses expensive recursive globs

**Files**:
- `skills/agent-manager/scripts/operations/extensions.py` lines 238-243
- `skills/skill-manager/scripts/operations/extensions.py` lines 213-219
- `skills/plugin-manager/scripts/operations/extensions.py` lines 200-206

```python
if list(cwd.glob(indicator)) or list(
    cwd.glob(f"**/{indicator}")
):
```

The `**/*.py` style recursive glob is O(n) across the entire working directory
tree. In large monorepos this can be very slow. Called during `get_questions()`
on every `create` operation.

**Impact**: Performance degradation in large repositories.

**Recommendation**: Consider limiting the depth of the recursive glob (e.g.,
only checking the first two directory levels), or caching the result for the
duration of a single operation.

---

### HYGIENE-1: Stale "CCM" / "ccm_templates_dir" naming in generators.py

**File**: `skills/plugin-manager/scripts/operations/scaffold_ops/generators.py`
lines 200, 203, 209, 229, 264, 267, 274, 299

The parameter `ccm_templates_dir` and docstring references to "CCM templates"
are vestiges of the old `claude-code-management` name. These should be renamed
to something accurate, such as `agent_templates_dir` / `skill_templates_dir`
(since the caller in `scaffold.py` already uses `AGENT_TEMPLATES_DIR` and
`SKILL_TEMPLATES_DIR`).

```python
def render_stub_agent(
    target: Path,
    name: str,
    description: str,
    ccm_templates_dir: Path,  # <-- stale name
```

**Fix**: Rename to `agent_templates_dir` in `render_stub_agent` and
`skill_templates_dir` in `render_stub_skill`. Update docstrings accordingly.

---

### HYGIENE-2: Unused import of `Optional` in hooks.py

**File**: `skills/hook-manager/scripts/operations/hooks.py` line 12

```python
from typing import Any, Optional
```

`Optional` is imported but the `execute()` function signature uses
`Optional[Path]` for `templates_dir` which is documented as "(unused for
hooks)". Since the parameter is never actually used, both the parameter and the
import could be removed for clarity.

**Impact**: Lint warning (unused import).

**Fix**: Remove `Optional` from the import and the `templates_dir` parameter
from `execute()`, or keep it for interface consistency if all managers are
expected to share the same `execute(context, responses, templates_dir)`
signature.

---

### HYGIENE-3: Inconsistent type annotation styles

**Files**: Multiple

The codebase mixes old-style `typing` imports (`Dict`, `List`, `Optional`)
with modern built-in generics (`dict`, `list`, `tuple`):

- `claude-md-manager/scripts/operations/claude_md.py` uses `Dict`, `List`,
  `Optional` (old style)
- `agent-manager/scripts/manage.py` uses `dict[str, Any]` (modern style)
- `skill-manager/scripts/manage.py` uses `dict[str, object]` (modern style,
  but `object` instead of `Any`)
- `plugin-manager/scripts/manage.py` uses `dict[str, Any]` (modern style)
- `hook-manager/scripts/manage.py` uses `dict[str, Any]` (modern style)

The use of `dict[str, object]` in skill-manager's manage.py is inconsistent
with all other managers which use `dict[str, Any]`.

**Fix**: Standardize on modern built-in generics (`dict`, `list`, etc.) and
use `Any` consistently for the value type. This can be done incrementally.

---

### HYGIENE-4: Duplicated operations/utils.py re-export modules

**Files**:
- `skills/claude-md-manager/scripts/operations/utils.py`
- `skills/agent-manager/scripts/operations/utils.py`
- `skills/skill-manager/scripts/operations/utils.py`
- `skills/plugin-manager/scripts/operations/utils.py`

All four files are nearly identical: they compute a `_project_root`, validate
that `shared/utils.py` exists, add to `sys.path`, and re-export the same set
of functions. The only difference is the docstring.

**Impact**: Low. But when `shared/utils.py` adds a new export, all four files
need to be updated.

**Recommendation**: Consider a single shared `operations_utils_bridge.py` in
`scripts/shared/` that all operations packages import from, or accept the
duplication as an acceptable trade-off for the self-contained nature of each
skill.

---

### HYGIENE-5: `__future__` annotations import inconsistency

**Files**:
- `skills/hook-manager/scripts/_paths.py` line 7:
  `from __future__ import annotations`
- `skills/claude-md-manager/scripts/_paths.py` line 7:
  `from __future__ import annotations`

No other `_paths.py` files use this import. The `__future__` import enables
PEP 604 style unions (`X | Y`) and postponed evaluation of annotations, which
is useful for forward references. Since the project targets Python 3.10+ (per
the modern type hints used elsewhere), this import is not strictly necessary.

**Fix**: Either add it everywhere or remove it from the two files that have it.
Minor consistency issue.

---

### TEST-GAP-1: No dedicated test file for skill-manager extensions

**Gap**: There is no `tests/unit/test_skill_manage.py` or similar file that
tests the skill-manager's `operations/extensions.py` directly. The existing
`tests/unit/test_manage.py` only tests the **agent-manager**'s manage.py.

While the shared utility functions (kebab-case, validation, etc.) are tested
via `test_manage.py` and `test_shared_utils.py`, the skill-specific logic
(SKILL.md discovery via `find_components()`, skill-specific `execute_create()`
which creates `references/` and `scripts/` subdirectories) has no direct test
coverage.

**Impact**: Medium. A regression in skill-manager's `find_components()` or
`execute_create()` subdirectory creation would not be caught by tests.

**Fix**: Add `tests/unit/test_skill_manage.py` mirroring the structure of
`test_manage.py` but targeting the skill-manager.

---

### TEST-GAP-2: No test for plugin-manager extension operations

**Gap**: There is no test file for `skills/plugin-manager/scripts/operations/
extensions.py`. The scaffold tests cover `scaffold.py` thoroughly, but the
plugin extension CRUD operations (create, validate, version, list for plugin
manifests) have no direct test coverage.

**Impact**: Medium. The `find_components()` function in plugin-manager's
`extensions.py` has a unique discovery pattern (looking for
`.claude-plugin/plugin.json` inside subdirectories) that differs from
agent/skill discovery. This code path is untested.

**Fix**: Add `tests/unit/test_plugin_extensions.py`.

---

### TEST-GAP-3: Module cache clearing pattern is fragile

**Files**: All test files (test_hooks.py, test_manage.py, test_claude_md.py,
test_scaffold.py, test_scaffold_context.py, test_scaffold_generators.py,
test_scaffold_licenses.py, test_error_recovery.py)

Every test file contains this boilerplate to avoid cross-manager import
conflicts:

```python
for _mod_name in list(sys.modules):
    if _mod_name == "operations" or _mod_name.startswith("operations."):
        del sys.modules[_mod_name]
```

This works in the current test suite (all 599 tests pass) but is fragile: if
pytest changes its import order or if a conftest adds an import, the cache
clearing may happen at the wrong time.

**Impact**: Low today (tests pass), but a latent maintenance risk.

**Recommendation**: Consider using a `conftest.py` at the tests root that
handles module isolation, or restructuring the operations packages to use
unique names (e.g., `hook_operations`, `agent_operations`) to avoid the
namespace collision entirely.

---

## Stale References Check

### In Code Files (Python, JSON, YAML, Jinja2)

- `claude-code-management`: **0 references** found in any code file
- `create-plugin`: **0 references** found in any code file
- `CCM`/`ccm_templates_dir`: **8 references** in `generators.py` (see
  HYGIENE-1 above)

### In Documentation/Issue Files

References to `claude-code-management` exist in:
- `.issues/in-progress/issue-31/` (research docs) -- expected, historical
- `CHANGELOG.md` -- expected, historical record
- `.issues/completed/` -- expected, archived issues

These are documentation/issue-tracking files and do not need updating.

---

## Template Directory Verification

All 5 managers have their template directories populated correctly:

| Manager | Template Dir | Files |
|---------|-------------|-------|
| agent-manager | `templates/agent/` | `agent.md.jinja2` |
| skill-manager | `templates/skill/` | `SKILL.md.jinja2` |
| plugin-manager | `templates/extension/` | `plugin.json.jinja2`, `README.md.jinja2`, `gitignore.jinja2` |
| plugin-manager | `templates/scaffold/` | 20 scaffold templates (shared, python, typescript) |
| claude-md-manager | `templates/claude-md/` | `project.md.jinja2`, `user.md.jinja2`, `plugin.md.jinja2` |
| hook-manager | (none needed) | N/A |

The plugin-manager scaffold correctly references agent-manager and
skill-manager template directories for stub generation (lines 65-70 of
`scaffold.py`).

---

## Routing Verification (aida SKILL.md)

The routing table in `skills/aida/SKILL.md` correctly maps:
- `/aida agent *` -> `agent-manager` skill
- `/aida skill *` -> `skill-manager` skill
- `/aida plugin *` -> `plugin-manager` skill (including scaffold)
- `/aida hook *` -> `hook-manager` skill
- `/aida claude *` -> `claude-md-manager` skill

No references to the old `claude-code-management` or `create-plugin` skills
remain in the routing table.

---

## Summary

| Category | Count | Items |
|----------|-------|-------|
| Bug | 2 | BUG-1 (import-time cwd), BUG-2 (code duplication drift risk) |
| Design | 4 | DESIGN-1 through DESIGN-4 |
| Hygiene | 5 | HYGIENE-1 through HYGIENE-5 |
| Test Gap | 3 | TEST-GAP-1 through TEST-GAP-3 |
| **Total** | **14** | |

### Recommended Priority for Fixes

**Before merge (blocking)**:
1. BUG-1: Fix `SETTINGS_PATHS` to evaluate `Path.cwd()` at call time
2. HYGIENE-1: Rename `ccm_templates_dir` (stale reference to old name)

**Soon after merge (high priority)**:
3. DESIGN-1: Standardize `_paths.py` pattern across all managers
4. DESIGN-3: Use hard assignment for `context["type"]` in agent-manager
5. TEST-GAP-1: Add skill-manager test coverage
6. TEST-GAP-2: Add plugin-manager extension test coverage

**Backlog (low priority)**:
7. BUG-2/DESIGN-4: Extract shared code to reduce duplication
8. DESIGN-2, HYGIENE-2-5, TEST-GAP-3: Consistency improvements
