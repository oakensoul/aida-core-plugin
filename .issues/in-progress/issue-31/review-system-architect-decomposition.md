---
type: review
title: "System Architect Review: Decomposition of claude-code-management (#31)"
reviewer: system-architect
date: 2026-02-24
scope: architecture
status: complete
files-reviewed: 62
---

# System Architect Review: Decomposition of claude-code-management

## Executive Summary

The decomposition of the monolithic `claude-code-management` skill into 5
focused manager skills is architecturally sound. The design achieves clean
separation of concerns, eliminates the unnecessary routing indirection layer,
and establishes consistent patterns across all managers. All 599 tests pass.
No stale references to the removed `claude-code-management` or `create-plugin`
skills exist in the active source tree.

The architecture follows a well-executed "strangler fig" pattern where each
domain (hooks, CLAUDE.md, agents, skills, plugins) now owns its full vertical
slice: SKILL.md definition, Python operations, templates, and reference docs.

**Overall assessment: Ready for merge with minor improvements.**

Below are specific findings categorized by severity.

---

## 1. Coupling Analysis

### 1.1 Dependency Graph (per manager)

| Manager | Depends on shared utils | Depends on other managers | Self-contained |
| --- | --- | --- | --- |
| hook-manager | Yes (safe_json_load) | No | Yes |
| claude-md-manager | Yes (parse_frontmatter, render_template, get_project_root) | Soft dep on aida/scripts/utils/inference | Mostly |
| agent-manager | Yes (full set) | No | Yes |
| skill-manager | Yes (full set) | No | Yes |
| plugin-manager | Yes (full set) | Cross-refs agent-manager + skill-manager templates for stubs | Mostly |

### 1.2 Cross-Manager Dependencies

**plugin-manager -> agent-manager/skill-manager templates (scaffold stubs):**
In `skills/plugin-manager/scripts/operations/scaffold.py` (lines 65-70):

```python
AGENT_TEMPLATES_DIR = (
    _PROJECT_ROOT / "skills" / "agent-manager" / "templates"
)
SKILL_TEMPLATES_DIR = (
    _PROJECT_ROOT / "skills" / "skill-manager" / "templates"
)
```

This is the only cross-manager dependency in the codebase. It is justified:
scaffold needs to render agent/skill stubs using the canonical templates
owned by those managers. Duplicating templates would be worse.

**claude-md-manager -> aida/scripts/utils/inference (soft dependency):**
In `skills/claude-md-manager/scripts/operations/claude_md.py` (lines 322-339),
`detect_project_context()` attempts to import from the aida skill's inference
module. The import is wrapped in try/except with a fallback, making this a
graceful degradation rather than a hard dependency. This is acceptable.

### 1.3 No Circular Dependencies

Confirmed: no manager imports from another manager's operations. The
dependency graph is a DAG rooted at `scripts/shared/utils.py`.

---

## 2. Consistency Analysis

### 2.1 Structural Pattern Adherence

All 5 managers follow the expected structure:

| Component | hook-mgr | claude-md-mgr | agent-mgr | skill-mgr | plugin-mgr |
| --- | --- | --- | --- | --- | --- |
| `SKILL.md` | Yes | Yes | Yes | Yes | Yes |
| `scripts/manage.py` | Yes | Yes | Yes | Yes | Yes |
| `scripts/_paths.py` | Yes | Yes | Yes | Yes | Yes |
| `scripts/operations/__init__.py` | Yes | Yes | Yes | Yes | Yes |
| `scripts/operations/utils.py` | **No** | Yes | Yes | Yes | Yes |
| `references/` | Yes | Yes | Yes | Yes | Yes |
| `templates/` | No | Yes | Yes | Yes | Yes |

### 2.2 Two-Phase API Contract

All managers implement the same CLI contract:

- `--get-questions --context='{...}'` returns JSON with `questions` + `inferred`
- `--execute --context='{...}' --responses='{...}'` returns JSON with `success`

The contract is consistent across all 5 managers. Agent-manager and
skill-manager additionally support a three-phase pattern (Phase 2 is
agent content generation, handled outside Python).

### 2.3 SKILL.md Frontmatter

| Field | hook-mgr | claude-md-mgr | agent-mgr | skill-mgr | plugin-mgr |
| --- | --- | --- | --- | --- | --- |
| `type: skill` | Yes | Yes | Yes | Yes | Yes |
| `name` | Yes | Yes | Yes | Yes | Yes |
| `description` | Yes | Yes | Yes | Yes | Yes |
| `version: 0.1.0` | Yes | Yes | Yes | Yes | Yes |
| `tags` | Yes | Yes | Yes | Yes | Yes |
| `title` | Yes | Yes | Yes | **Missing** | **Missing** |
| `argument_hint` | No | No | No | No | Yes |

---

## 3. Findings

### CRITICAL

*None found.* The decomposition has no blocking issues.

### MAJOR

#### M1: `_paths.py` inconsistency -- agent-manager and skill-manager do not add shared scripts to sys.path

**Files:**

- `skills/agent-manager/scripts/_paths.py`
- `skills/skill-manager/scripts/_paths.py`

**Issue:** These two `_paths.py` files define `SHARED_UTILS` but never add
it to `sys.path`. Instead, the corresponding `manage.py` files duplicate the
sys.path manipulation directly (lines 39-40):

```python
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
```

Meanwhile, hook-manager, claude-md-manager, and plugin-manager all handle
sys.path setup inside `_paths.py` itself.

**Impact:** The pattern works but creates two different conventions for how
path setup is done. If a developer adds a new import in `manage.py` before
the sys.path lines, it will fail with an inscrutable ImportError.

**Recommendation:** Move the `sys.path.insert()` calls into `_paths.py` for
agent-manager and skill-manager, matching the pattern used by the other three
managers. The `manage.py` files should only `import _paths` and then import
from operations.

#### M2: `_paths.py` inconsistency -- some use `.resolve()`, some don't

**Files:**

- `skills/hook-manager/scripts/_paths.py` (uses `.resolve()`)
- All other `_paths.py` files (do not use `.resolve()`)

**Issue:** hook-manager resolves the path to its real filesystem location:

```python
SCRIPT_DIR = Path(__file__).resolve().parent
```

All others use:

```python
SCRIPT_DIR = Path(__file__).parent
```

**Impact:** Under symlinks (e.g., when the plugin is installed via symlink),
the resolved path may differ from the unresolved path, potentially causing
the `PROJECT_ROOT` calculation to point to the wrong location.

**Recommendation:** Pick one convention and apply it consistently. Using
`.resolve()` is safer in general, but since this is a source-tree-only layout,
either is fine as long as it is uniform.

#### M3: hook-manager missing `operations/utils.py` re-export shim

**Files:**

- `skills/hook-manager/scripts/operations/` (no `utils.py`)

**Issue:** All 4 other managers have an `operations/utils.py` that re-exports
shared utilities. hook-manager does not. Its `manage.py` imports
`safe_json_load` directly from `shared.utils` instead of through
`operations.utils`.

**Impact:** If hook operations ever need shared utilities (currently they
don't), developers would need to know this manager uses a different import
pattern. It also breaks the structural uniformity across managers.

**Recommendation:** Add a minimal `operations/utils.py` shim to hook-manager
for consistency, even if it only re-exports `safe_json_load`.

#### M4: Massive code duplication in `detect_project_context()` across agent/skill/plugin extensions

**Files:**

- `skills/agent-manager/scripts/operations/extensions.py` (lines 204-322)
- `skills/skill-manager/scripts/operations/extensions.py` (lines 178-302)
- `skills/plugin-manager/scripts/operations/extensions.py` (lines 168-284)

**Issue:** The `detect_project_context()` function is copy-pasted across all
three extension managers with near-identical logic (~120 lines each). The
only differences are trivial:

- agent-manager: `framework_files` includes `"fastapi": ["main.py"]`
- plugin-manager: `framework_files` omits `"fastapi"` and `"react"`
- Minor whitespace/formatting variations

**Impact:** Bug fixes or new language/framework detection must be applied in
3 places. This is the single largest DRY violation in the decomposition.

**Recommendation:** Extract `detect_project_context()` into
`scripts/shared/utils.py` (or a new `scripts/shared/project_detection.py`).
Each manager can call the shared version, optionally passing overrides if
needed. This would eliminate ~240 lines of duplicated code.

#### M5: Duplicated `infer_from_description()` and `tag_keywords` across agent/skill/plugin extensions

**Files:** Same three extensions.py files.

**Issue:** The `infer_from_description()` function and its `tag_keywords`
dictionary are identical across all three managers (~40 lines each, ~120 total).

**Recommendation:** Extract to `scripts/shared/utils.py` alongside
`detect_project_context()`.

### MINOR

#### m1: `_paths.py` in claude-md-manager does not verify shared utils exist

**File:** `skills/claude-md-manager/scripts/_paths.py`

**Issue:** This `_paths.py` adds the scripts path to `sys.path` but does
not verify that `shared/utils.py` exists first. Agent-manager and
skill-manager perform this check in their `operations/utils.py`. Plugin-manager
performs the check in `_paths.py`. Hook-manager does not check at all.

**Recommendation:** Adopt the plugin-manager pattern (check in `_paths.py`)
across all managers for fail-fast behavior.

#### m2: Inconsistent logging format -- plugin-manager sends logs to stderr

**File:** `skills/plugin-manager/scripts/manage.py` (line 42)

**Issue:** Plugin-manager configures logging with `stream=sys.stderr`, while
all other managers use the default (stdout). This is actually better practice
(keeps logs separate from JSON output), but it is inconsistent.

**Recommendation:** Either adopt `stream=sys.stderr` across all managers (the
better choice) or remove it from plugin-manager for consistency.

#### m3: Inconsistent type annotations -- `dict[str, Any]` vs `Dict[str, Any]`

**Files:**

- hook-manager manage.py: uses `dict[str, Any]`
- agent-manager manage.py: uses `dict[str, Any]`
- skill-manager manage.py: uses `dict[str, object]` (different!)
- Operations files: mixed use of `Dict[str, Any]` (typing module)

**Issue:** skill-manager's `manage.py` uses `dict[str, object]` for type
annotations while agent-manager uses `dict[str, Any]`. The operations modules
all use `Dict[str, Any]` from the `typing` module (uppercase). Python 3.9+
supports lowercase `dict` natively, but the codebase should be consistent.

**Recommendation:** Standardize on `dict[str, Any]` (lowercase) throughout,
since the project already requires Python 3.9+ (uses `from __future__ import
annotations` in some files). Also fix skill-manager to use `Any` not `object`.

#### m4: agent-manager `manage.py` uses `setdefault` while skill-manager uses direct assignment

**Files:**

- `skills/agent-manager/scripts/manage.py` line 60: `context.setdefault("type", "agent")`
- `skills/skill-manager/scripts/manage.py` line 63: `context["type"] = "skill"`

**Issue:** agent-manager uses `setdefault` (preserves caller's type if set),
while skill-manager uses direct assignment (always forces type to "skill").
Since these are focused managers, the caller should never pass a different type.

**Recommendation:** Use direct assignment (`context["type"] = "..."`) in both
managers. The focused manager should always enforce its own type, never trust
the caller.

#### m5: plugin-manager SKILL.md missing `title` field

**File:** `skills/plugin-manager/SKILL.md`

**Issue:** The frontmatter has no `title` field. Hook-manager has
`title: Hook Manager`, claude-md-manager has `title: CLAUDE.md Manager`,
agent-manager has `title: Agent Manager`. Plugin-manager and skill-manager
are missing `title`.

**Recommendation:** Add `title: Plugin Manager` and `title: Skill Manager`
to their respective SKILL.md frontmatter for consistency.

#### m6: Inconsistent error logging style -- f-string vs %s format

**Files:**

- hook-manager, claude-md-manager, skill-manager: use f-string logging:
  `logger.error(f"Validation error: {e}")`
- agent-manager, plugin-manager: use %-style logging:
  `logger.error("Validation error: %s", e)`

**Issue:** The %-style is technically preferred for logging (defers string
formatting until the message is actually emitted), but the codebase is split.

**Recommendation:** Standardize on %-style for logging calls (consistent with
Python logging best practices).

#### m7: CHANGELOG.md contains stale reference to removed skill

**File:** `CHANGELOG.md` (line 28)

**Issue:** Contains the line:
`- Removed command template from 'skills/claude-code-management/templates/'`

This is a historical changelog entry referring to the old monolith. While
historically accurate, once the decomposition PR merges, the CHANGELOG should
document the decomposition itself.

**Recommendation:** Add a new CHANGELOG entry documenting the decomposition
(issue #31) when the PR is created.

#### m8: `from __future__ import annotations` used inconsistently

**Files:**

- `skills/hook-manager/scripts/_paths.py` -- uses it
- All other `_paths.py` files -- do not use it

**Recommendation:** Either use it everywhere or nowhere.

### SUGGESTION

#### S1: Consider a base `manage.py` module to reduce boilerplate

**Observation:** All 5 `manage.py` files share ~80% identical boilerplate
(argparse setup, JSON I/O, error handling, main loop). The only differences
are:

1. Which operations module to import
2. How `get_questions`/`execute` delegate
3. The description string

**Suggestion:** Create a `scripts/shared/cli.py` base module with a
`TwoPhaseRunner` class that handles the common CLI boilerplate. Each
`manage.py` would reduce to ~15 lines:

```python
import _paths
from shared.cli import TwoPhaseRunner
from operations import hooks
runner = TwoPhaseRunner("Hook Manager", hooks)
if __name__ == "__main__":
    sys.exit(runner.main())
```

This is a follow-up optimization, not needed for this PR.

#### S2: Consider extracting `validate_agent_output()` to shared utils

**Observation:** `validate_agent_output()` is nearly identical in
agent-manager and plugin-manager extensions.py. Skill-manager inlines the
same logic in `execute_create_from_agent()`. All three perform the same
structural validation on agent output JSON.

**Suggestion:** Extract to shared utils as `validate_extension_output()`.

#### S3: Test coverage gaps for new managers

**Observation:** The test suite has:

- `tests/test_hooks.py` -- thorough coverage of hook operations
- `tests/unit/test_manage.py` -- covers agent-manager manage.py + shared utils
- `tests/unit/test_shared_utils.py` -- covers shared utils
- `tests/unit/test_claude_md.py` -- covers CLAUDE.md operations

**Missing:**

- No dedicated test file for `skill-manager` operations
- No dedicated test file for `plugin-manager` extension operations
- No test for the routing layer (`aida/SKILL.md` is Markdown, so not
  unit-testable, but the routing logic could be validated)

The `sys.modules` cache-clearing pattern in `test_manage.py` and
`test_hooks.py` is necessary and correctly implemented to avoid cross-manager
module conflicts when pytest runs all tests in a single process. This pattern
should be documented and replicated for any new manager test files.

#### S4: Consider moving `LOCATION_PATHS` deprecation forward

**File:** `scripts/shared/utils.py` (lines 244-252)

**Observation:** `LOCATION_PATHS` is marked as deprecated but is still
exported by all `operations/utils.py` shims. Consider removing it from the
re-exports if nothing references it.

---

## 4. Routing Architecture

### 4.1 Dispatch Table Analysis

The `skills/aida/SKILL.md` routing is clean and unambiguous:

| Command Prefix | Target Skill | Status |
| --- | --- | --- |
| `agent [op]` | agent-manager | Clean |
| `skill [op]` | skill-manager | Clean |
| `plugin [op]` | plugin-manager | Clean |
| `hook [op]` | hook-manager | Clean |
| `claude [op]` | claude-md-manager | Clean |
| `memento [op]` | memento | Clean |
| `config permissions` | permissions | Clean |
| `config` | Internal (configure.py) | Clean |
| `status/doctor/upgrade` | Internal (scripts/) | Clean |
| `feedback/bug/feature-request` | Internal (feedback.py) | Clean |
| `help` / no args | Inline help text | Clean |

### 4.2 No Dead Routes

Confirmed: no routes reference `claude-code-management` or `create-plugin`.
All routes point to skills that exist in the `skills/` directory.

### 4.3 Cross-Cutting Operations

The `aida` skill correctly handles cross-cutting concerns:

- `config permissions` dispatches to the `permissions` skill (not a manager)
- Help text in SKILL.md (lines 279-333) correctly lists all 5 managers
- The help text's command examples match the actual routing table

### 4.4 Routing Clarity

Each routing section follows the same pattern:

1. Parse command to extract operation + arguments
2. Invoke the target skill with parsed context
3. Examples showing exact command-to-skill mapping

This is easy to maintain. Adding a new manager would require:

1. Add a new routing section to `aida/SKILL.md`
2. Add entries to the help text

---

## 5. Template Organization

### 5.1 Template Ownership

| Manager | Templates Owned | Location |
| --- | --- | --- |
| agent-manager | `agent/agent.md.jinja2` | `skills/agent-manager/templates/` |
| skill-manager | `skill/SKILL.md.jinja2` | `skills/skill-manager/templates/` |
| plugin-manager | `extension/*.jinja2` (3) + `scaffold/**/*.jinja2` (27) | `skills/plugin-manager/templates/` |
| claude-md-manager | `claude-md/*.jinja2` (3) | `skills/claude-md-manager/templates/` |
| hook-manager | None (hooks are JSON config, not files) | N/A |

### 5.2 Template Path References

All Python code correctly references templates relative to the skill's
own `SKILL_DIR / "templates"` via `_paths.py`. The one cross-reference
(scaffold.py referencing agent-manager and skill-manager templates) uses
`_PROJECT_ROOT` to navigate correctly.

### 5.3 Plugin-Manager Template Organization

Plugin-manager correctly separates its two template domains:

- `templates/extension/` -- for plugin extension CRUD (plugin.json, README, gitignore)
- `templates/scaffold/` -- for full project scaffolding (shared/, python/, typescript/)

The `_paths.py` exports both `EXTENSION_TEMPLATES_DIR` and
`SCAFFOLD_TEMPLATES_DIR` for explicit disambiguation. This is well-designed.

---

## 6. Test Architecture

### 6.1 Module Isolation

The `sys.modules` cache-clearing pattern is correctly implemented in:

- `tests/test_hooks.py` (lines 12-15)
- `tests/unit/test_manage.py` (lines 18-21)

This pattern is essential because multiple managers have identically-named
`operations` and `manage` modules. Without clearing, pytest would reuse the
first-imported `operations` package for all tests.

### 6.2 Test Results

All 599 tests pass (verified during review).

### 6.3 Coverage Assessment

| Manager | Test File | Coverage Level |
| --- | --- | --- |
| hook-manager | `tests/test_hooks.py` | Good (constants, questions, CRUD, validate) |
| agent-manager | `tests/unit/test_manage.py` | Good (shared utils, questions, execute, create) |
| claude-md-manager | `tests/unit/test_claude_md.py` | Good (existing) |
| skill-manager | No dedicated test | Gap |
| plugin-manager (extension) | `tests/unit/test_plugin_discovery.py` | Partial |
| plugin-manager (scaffold) | `tests/unit/test_scaffold*.py` (4 files) | Good |
| shared utils | `tests/unit/test_shared_utils.py` | Good |

---

## 7. Summary of Recommendations

### Must-fix for this PR

*None.* All findings are improvement-grade, not blockers.

### Should-fix (high value, low risk)

1. **M4/M5**: Extract `detect_project_context()` and
   `infer_from_description()` to shared utils (eliminates ~360 lines of
   duplication)
2. **M1/M2**: Normalize `_paths.py` conventions across all 5 managers
3. **M3**: Add `operations/utils.py` shim to hook-manager

### Nice-to-have (follow-up PR)

1. **S1**: Base `manage.py` runner to reduce boilerplate
2. **S2**: Shared `validate_extension_output()` helper
3. **S3**: Add test files for skill-manager and plugin-manager extensions
4. **m2**: Standardize logging to stderr across all managers
5. **m3**: Standardize type annotations
6. **m5**: Add missing `title` fields to frontmatter

---

## Appendix: File Inventory

### New Skills (5)

```text
skills/hook-manager/          (5 files: SKILL.md, manage.py, _paths.py, __init__.py, hooks.py)
skills/claude-md-manager/     (6 files: SKILL.md, manage.py, _paths.py, __init__.py, claude_md.py, utils.py)
skills/agent-manager/         (6 files: SKILL.md, manage.py, _paths.py, __init__.py, extensions.py, utils.py)
skills/skill-manager/         (6 files: SKILL.md, manage.py, _paths.py, __init__.py, extensions.py, utils.py)
skills/plugin-manager/        (10 files: SKILL.md, manage.py, _paths.py, __init__.py, extensions.py, utils.py,
                               scaffold.py, scaffold_ops/__init__.py, context.py, generators.py, licenses.py)
```

### Shared Infrastructure

```text
scripts/shared/utils.py       (shared utilities: validation, templates, paths)
```

### Updated Routing

```text
skills/aida/SKILL.md          (routing updated for direct dispatch to 5 managers)
```

### Removed (pending)

```text
skills/claude-code-management/ (monolith -- to be deleted)
skills/create-plugin/          (merged into plugin-manager)
```
