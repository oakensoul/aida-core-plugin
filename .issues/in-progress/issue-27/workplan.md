---
type: workplan
issue: 27
title: "Workplan: /aida plugin update"
date: 2026-02-24
reviewers:
  - system-architect
  - claude-code-expert
  - product-manager
  - tech-lead
status: draft
---

# Workplan: /aida plugin update (Issue #27)

## Executive Summary

This workplan defines the implementation of `/aida plugin update`, a
standards migration tool that brings existing plugins into compliance
with the current scaffolding templates. As AIDA plugin standards evolve
(new linting configs, updated Makefile targets, CI workflows, required
files), plugins scaffolded under older versions fall behind with no
automated way to catch up. The update operation closes that gap by
scanning a plugin against the latest templates, producing a categorized
diff report, and applying non-destructive patches with user approval.

The design follows the project's established two-phase API pattern: Phase
1 scans the plugin and returns a read-only diff report with questions
about merge strategy preferences; Phase 2 applies the approved patches.
This mirrors the existing scaffold operation's architecture while keeping
implementation fully decoupled. Templates are the shared source of truth
between scaffold and update -- both consume them independently, and no
code coupling is introduced between the two modules.

The implementation is structured as a new `operations/update.py` module
with an `update_ops/` subpackage containing scanner, differ, patcher,
and strategy modules. The file classification system uses four categories
(custom/skip, boilerplate/overwrite, composite/merge, missing/add) with
sensible defaults that minimize user decisions while preserving safety.
Backups are created before any modification, and all writes use atomic
file operations. The estimated effort is 6-8 person-days across 11
implementation tasks.

## Architecture Decisions

1. **New module, not an extension of scaffold.py.** The update operation
   gets its own `operations/update.py` entry point and `update_ops/`
   subpackage, following the same structural pattern as
   `scaffold.py` / `scaffold_ops/`. This keeps responsibilities clean
   and avoids bloating scaffold with comparison logic. (All reviewers
   agreed.)

2. **Templates are a shared contract, not shared code.** Both scaffold
   and update independently consume the Jinja2 templates in
   `templates/scaffold/`. The update operation renders templates to
   produce "expected" content, then compares against actual files. No
   code is shared between scaffold and update beyond the template
   files themselves and the `render_template` utility from
   `shared/utils.py`. (System Architect, Claude Code Expert.)

3. **`GENERATOR_VERSION` extracted to shared constant.** The version
   string currently lives in `scaffold.py` line 72. It will be moved
   to a new `operations/constants.py` file so both scaffold and update
   can reference the canonical version without importing each other.
   (System Architect.)

4. **Template variable construction extracted to shared helper.** The
   `variables` dict built in `scaffold.py:execute()` (lines 391-433)
   will be extracted into a `build_template_variables()` function in a
   new `operations/shared.py` module. Update needs the same variables
   to render templates for comparison. (System Architect, Tech Lead.)

5. **`generator_version` tracked in `aida-config.json`.** The version
   of the scaffolder that created (or last updated) the plugin is
   stored in `.claude-plugin/aida-config.json` under a new
   `"generator_version"` key. This avoids polluting `plugin.json`
   (which is Claude Code's schema) with AIDA-specific metadata. The
   scaffold operation will be updated to write this field. (Claude
   Code Expert, System Architect, Product Manager -- Tech Lead
   initially proposed `plugin.json` but deferred to consensus.)

6. **Four-category file classification with fixed defaults.** Files
   are classified into categories with default strategies that minimize
   user decisions. See the File Classification table below. (All
   reviewers agreed on categories; strategies reflect resolved
   disagreements.)

7. **Phase 1 is read-only; Phase 2 is user-approved patch.** Phase 1
   performs a full scan and returns the diff report inside the
   `inferred` payload (matching the existing response shape). Phase 2
   re-scans to confirm state, then applies patches per the approved
   strategy. (All reviewers.)

8. **Backup before modification.** Before any file is modified, the
   entire plugin directory is backed up to `.aida-backup/{timestamp}/`.
   This location is visible and not nested inside `.claude-plugin/`.
   (System Architect -- Tech Lead initially proposed
   `.claude-plugin/.update-backup/` but the more visible location was
   preferred.)

9. **Atomic file writes.** All file writes go to a `.tmp` sibling
   first, then are renamed into place. This prevents partial writes
   from corrupting files on failure. (Tech Lead.)

10. **Conservative Makefile merge for v1.0.** The Makefile merge
    strategy adds missing targets only; it does not modify existing
    targets. Sentinel comment markers in templates are planned for v1.1
    to enable section-level diffing. (Tech Lead for v1.0 approach;
    Claude Code Expert for v1.1 sentinel design.)

11. **CI workflows: add-if-missing, skip-if-exists.** CI workflow files
    (`.github/workflows/ci.yml`) are added only if the file does not
    exist. Existing CI files are never modified because they are too
    diverse to auto-merge safely. (Product Manager, Tech Lead.)

12. **Dependency files flagged for manual review.** `pyproject.toml` and
    `package.json` are never auto-merged. The diff report flags them
    with a "manual review recommended" note listing specific
    differences. (System Architect.)

## File Classification and Merge Strategies

| Category | Strategy | Files | Rationale | User Override? |
| --- | --- | --- | --- | --- |
| **Custom content** | `skip` | `CLAUDE.md`, `README.md`, `LICENSE` | User-authored content; never override | No |
| **AIDA metadata** | `skip` | `.claude-plugin/aida-config.json` | User-configured preferences/permissions | No |
| **Pure boilerplate** | `overwrite` | `.markdownlint.json`, `.yamllint.yml`, `.frontmatter-schema.json`, `.python-version`, `.nvmrc`, `.prettierrc.json`, `eslint.config.mjs`, `tsconfig.json`, `vitest.config.ts` | Entirely template-generated; safe to replace | Yes (can override to `skip`) |
| **Plugin metadata** | `overwrite` | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Schema-driven, safe to regenerate (preserves user values) | Yes (can override to `skip`) |
| **Composite: gitignore** | `merge` | `.gitignore` | Append-only: add missing entries, never remove | No |
| **Composite: makefile** | `merge` | `Makefile` | Add missing targets only; never modify existing | No |
| **CI workflows** | `add` | `.github/workflows/ci.yml` | Add if missing; skip if exists | Yes (can override to `skip`) |
| **Dependency configs** | `manual_review` | `pyproject.toml`, `package.json` | Too risky to auto-merge; flag differences | No |
| **Test scaffolding** | `add` | `tests/conftest.py` | Add if missing; skip if exists | Yes (can override to `skip`) |
| **New additions** | `add` | Any template file not in plugin | Added if file does not exist | Yes (can override to `skip`) |

## Scope: v1.0 MVP

### In Scope

- P0: Full plugin scan with categorized diff report (Phase 1)
- P0: Add missing files from templates
- P0: Append-only `.gitignore` merge (add missing entries)
- P0: Conservative Makefile merge (add missing targets)
- P0: Overwrite pure boilerplate linting configs
- P0: Post-update summary with manual steps remaining
- P0: Two-phase workflow matching existing API pattern
- P0: Language detection from existing plugin structure
- P0: Backup before any modification
- P0: `generator_version` tracking in `aida-config.json`
- P0: Update SKILL.md with update operation documentation
- P0: Reference document `update-workflow.md`
- P1: Single strategy override question for boilerplate class
- P1: Dirty git tree warning (advisory, non-blocking)
- P1: Plugin metadata regeneration preserving user values

### Out of Scope (Deferred)

- Per-file interactive accept/skip (v1.1)
- Inline diff preview for modified files (v1.1)
- Sentinel comment markers in Makefile templates (v1.1)
- `--dry-run` CLI flag (Phase 1 already serves this purpose)
- "outdated" indicator in `plugin list` output (v1.1)
- Multi-language detection (v1.1)
- Batch update across multiple plugins (v1.1)
- Git auto-commit after update (v1.1)
- Remote/installed plugin update support (v2.0)
- Migration scripts for complex version jumps (v2.0)
- Version delta maps / changelog-driven migrations (v2.0)
- Backup retention policy / auto-cleanup (v1.1)

## Implementation Tasks

### Task 1: Extract shared constants and template variable builder

**Description:** Move `GENERATOR_VERSION` from `scaffold.py` into a new
`operations/constants.py`. Extract the template variable construction
logic from `scaffold.py:execute()` (lines 362-433) into a
`build_template_variables()` function in a new `operations/shared.py`.
Update `scaffold.py` to import from both new modules. All existing
scaffold tests must continue to pass.

**Files to create:**

- `skills/plugin-manager/scripts/operations/constants.py`
- `skills/plugin-manager/scripts/operations/shared.py`

**Files to modify:**

- `skills/plugin-manager/scripts/operations/scaffold.py`
  (remove `GENERATOR_VERSION` definition, import from `constants`;
  replace inline variable building with call to
  `build_template_variables()`)

**Dependencies:** None (foundational task).

**Size:** S

**Key implementation notes:**

- `constants.py` contains only `GENERATOR_VERSION = "0.9.0"` and
  `SUPPORTED_LANGUAGES = ("python", "typescript")` (both currently
  in scaffold.py).
- `build_template_variables(context, license_text)` returns the
  `dict[str, Any]` currently built inline. It takes the full context
  dict and the resolved license text as inputs.
- `shared.py` imports from `constants.py` and from `scaffold_ops`
  helpers (like `_normalize_python_version`) as needed.
- Do NOT move `SCAFFOLD_TEMPLATES_DIR` or other path constants --
  those stay in their respective modules.
- Run `make test` to confirm no regressions.

---

### Task 2: Add `generator_version` to `aida-config.json` template and scaffold output

**Description:** Add a `"generator_version"` field to the
`aida-config.json.jinja2` template so newly scaffolded plugins
track which version of the scaffolder created them. Update the
schemas reference document.

**Files to modify:**

- `skills/plugin-manager/templates/scaffold/shared/aida-config.json.jinja2`
  (add `"generator_version": {{ generator_version | tojson }}` at
  top level)
- `skills/plugin-manager/references/schemas.md`
  (document the new field under `## aida-config.json`)

**Dependencies:** Task 1 (uses `GENERATOR_VERSION` from constants).

**Size:** S

**Key implementation notes:**

- The `generator_version` variable is already passed to templates by
  scaffold (line 432 in scaffold.py). The template just needs to
  consume it.
- Place the field at the top level of `aida-config.json`, not nested
  inside `config`:

  ```json
  {
    "generator_version": "0.9.0",
    "config": { ... },
    ...
  }
  ```

- Update existing scaffold tests that snapshot `aida-config.json`
  output to expect the new field.
- For plugins scaffolded before this change (no `generator_version`
  field), the update scanner (Task 4) will treat them as version
  `"0.0.0"` (unknown/pre-tracking).

---

### Task 3: Create `update_ops/` subpackage with dataclasses and strategy registry

**Description:** Create the `update_ops/` subpackage with core data
structures (`FileStatus`, `ScanResult`, `FileDiff`, `DiffReport`,
`PatchResult`) and the strategy registry that maps file paths to
categories and default strategies.

**Files to create:**

- `skills/plugin-manager/scripts/operations/update_ops/__init__.py`
- `skills/plugin-manager/scripts/operations/update_ops/models.py`
- `skills/plugin-manager/scripts/operations/update_ops/strategies.py`

**Dependencies:** Task 1 (imports `SUPPORTED_LANGUAGES` from constants).

**Size:** M

**Key implementation notes:**

- `models.py` defines these dataclasses:

  ```python
  from dataclasses import dataclass, field
  from enum import Enum

  class FileCategory(Enum):
      CUSTOM = "custom"
      BOILERPLATE = "boilerplate"
      COMPOSITE = "composite"
      CI_WORKFLOW = "ci_workflow"
      DEPENDENCY_CONFIG = "dependency_config"
      TEST_SCAFFOLD = "test_scaffold"
      METADATA = "metadata"
      NEW_ADDITION = "new_addition"

  class MergeStrategy(Enum):
      SKIP = "skip"
      OVERWRITE = "overwrite"
      MERGE = "merge"
      ADD = "add"
      MANUAL_REVIEW = "manual_review"

  class FileStatus(Enum):
      MISSING = "missing"
      OUTDATED = "outdated"
      UP_TO_DATE = "up_to_date"
      CUSTOM_SKIP = "custom_skip"

  @dataclass
  class FileDiff:
      path: str
      category: FileCategory
      status: FileStatus
      strategy: MergeStrategy
      expected_content: str | None = None
      actual_content: str | None = None
      diff_summary: str = ""

  @dataclass
  class DiffReport:
      plugin_path: str
      language: str
      generator_version: str
      current_version: str
      files: list[FileDiff] = field(default_factory=list)

      @property
      def missing_files(self) -> list[FileDiff]:
          return [f for f in self.files
                  if f.status == FileStatus.MISSING]

      @property
      def outdated_files(self) -> list[FileDiff]:
          return [f for f in self.files
                  if f.status == FileStatus.OUTDATED]

      @property
      def up_to_date_files(self) -> list[FileDiff]:
          return [f for f in self.files
                  if f.status == FileStatus.UP_TO_DATE]

      @property
      def custom_skip_files(self) -> list[FileDiff]:
          return [f for f in self.files
                  if f.status == FileStatus.CUSTOM_SKIP]

  @dataclass
  class PatchResult:
      path: str
      action: str  # "created", "updated", "skipped", "failed"
      message: str
      backup_path: str = ""
  ```

- `strategies.py` defines the `FileSpec` mapping and
  `get_file_specs(language)` function:

  ```python
  @dataclass
  class FileSpec:
      path: str
      template: str  # template path relative to scaffold dir
      category: FileCategory
      default_strategy: MergeStrategy
      user_overridable: bool = False
  ```

  The function returns a list of `FileSpec` for all files that the
  scaffolder would produce for the given language. This is the
  single source of truth for file classification.

- Use modern type hints (`str | None`, not `Optional[str]`).
- All enums use lowercase string values for JSON serialization.

---

### Task 4: Implement the scanner module

**Description:** Create the scanner that reads an existing plugin
directory and produces a `DiffReport` by comparing actual files
against template-rendered expectations.

**Files to create:**

- `skills/plugin-manager/scripts/operations/update_ops/scanner.py`

**Dependencies:** Task 1 (shared template variable builder), Task 3
(models and strategy registry).

**Size:** L

**Key implementation notes:**

- `scan_plugin(plugin_path, templates_dir)` is the main entry point.
  Returns a `DiffReport`.
- Scanner flow:
  1. Read `.claude-plugin/plugin.json` to get plugin name, version,
     description, author info, etc.
  2. Read `.claude-plugin/aida-config.json` to get `generator_version`
     (default `"0.0.0"` if missing).
  3. Detect language by checking for `pyproject.toml` (python) or
     `package.json` (typescript). Fall back to directory heuristics
     (`scripts/` = python, `src/` + no `scripts/` = typescript).
  4. Build template variables using `build_template_variables()`.
  5. Get file specs using `get_file_specs(language)`.
  6. For each file spec:
     - Render the template to get expected content.
     - Read the actual file (if it exists).
     - Classify: missing, outdated (content differs), up-to-date,
       or custom-skip (based on category).
     - Populate a `FileDiff` with both contents and a summary.
- For composite files (`.gitignore`, `Makefile`), the "expected"
  content is the rendered template; the diff summary describes
  what entries/targets are missing rather than a full content diff.
- For `.gitignore` comparison: parse both into sets of non-empty,
  non-comment lines; report lines present in expected but absent
  from actual.
- For `Makefile` comparison: extract target names (lines matching
  `^[a-zA-Z_-]+:`) from both; report targets present in expected
  but absent from actual.
- For dependency configs (`pyproject.toml`, `package.json`): compare
  key structural sections and summarize differences without producing
  a patch.
- The scanner MUST NOT modify any files. It is purely read-only.
- Handle missing `plugin.json` gracefully: return an error result
  (not a valid plugin directory).
- Handle missing `aida-config.json` gracefully: use defaults.

---

### Task 5: Implement the patcher module

**Description:** Create the patcher that applies approved patches to
the plugin directory, with backup and atomic writes.

**Files to create:**

- `skills/plugin-manager/scripts/operations/update_ops/patcher.py`

**Dependencies:** Task 3 (models), Task 4 (scanner for re-scan).

**Size:** L

**Key implementation notes:**

- `apply_patches(plugin_path, diff_report, overrides)` is the main
  entry point. Returns `list[PatchResult]`.
- `overrides` is a `dict[str, MergeStrategy]` allowing the user to
  override default strategies for specific file paths or categories.
- Before any modification:
  1. Create backup directory:
     `.aida-backup/{YYYYMMDD_HHMMSS}/`
     inside the plugin root.
  2. Copy all files that will be modified into the backup.
- Strategy implementations:
  - **`skip`**: Do nothing. Return `PatchResult` with action
    `"skipped"`.
  - **`overwrite`**: Write rendered template content to file using
    atomic write (write to `{path}.tmp`, then `os.replace()`).
  - **`add`**: Same as overwrite but only when file does not exist.
    If file exists, skip.
  - **`merge` (gitignore)**: Parse current `.gitignore` into a set
    of entries. Parse expected into a set. Append missing entries
    (grouped under a `# Added by aida plugin update` comment
    header). Write atomically.
  - **`merge` (makefile)**: Parse current Makefile to extract target
    names. Render expected Makefile, extract targets. For each
    missing target, extract the full target block (target line +
    recipe lines) from the rendered template and append to the
    Makefile under a `# Added by aida plugin update` comment
    header. Write atomically.
  - **`manual_review`**: Do nothing. Return `PatchResult` with
    action `"skipped"` and a message listing differences for the
    user to address manually.
- After patching, update `generator_version` in `aida-config.json`
  to the current `GENERATOR_VERSION`.
- If any write fails, log the error and continue with remaining
  files. Return all results including failures. Do NOT roll back
  other successful writes (the backup serves as rollback).
- For plugin metadata (`plugin.json`, `marketplace.json`):
  re-render template using actual plugin values (name, version,
  description from the existing file), NOT the template defaults.
  This preserves user values while updating schema structure.

---

### Task 6: Implement the `update.py` entry point

**Description:** Create the main `operations/update.py` module that
implements `get_questions()` and `execute()` following the two-phase
API pattern. Wire it into `manage.py` routing.

**Files to create:**

- `skills/plugin-manager/scripts/operations/update.py`

**Files to modify:**

- `skills/plugin-manager/scripts/manage.py`
  (add `from operations import update`, add
  `is_update_operation()` check, route to `update.get_questions()`
  and `update.execute()`)

**Dependencies:** Task 4 (scanner), Task 5 (patcher).

**Size:** M

**Key implementation notes:**

- `get_questions(context)` flow:
  1. Validate `context` has `"plugin_path"` (required -- the path
     to the existing plugin to update).
  2. Call `scanner.scan_plugin()` to produce the `DiffReport`.
  3. If scan fails (not a valid plugin), return error.
  4. Build the `inferred` payload containing the serialized
     `DiffReport` under a `"scan_result"` key.
  5. Build questions list. For v1.0, the only question is:
     - `"boilerplate_strategy"`: choice of `"overwrite"` (default)
       or `"skip"` for the boilerplate file category.
  6. Return `{"questions": [...], "inferred": {...}, "phase": "get_questions"}`.

- `execute(context, responses)` flow:
  1. Extract `plugin_path` from context.
  2. Re-scan plugin (confirm current state).
  3. Build overrides dict from user responses.
  4. Call `patcher.apply_patches()`.
  5. Build result summary:
     - Files created, updated, skipped, failed.
     - Manual steps remaining (from `manual_review` items).
     - Backup location.
     - Updated `generator_version`.
  6. Return standard result dict with `success`, `message`,
     `files_modified`, `files_created`, `files_skipped`,
     `manual_steps`, `backup_path`.

- `manage.py` changes:

  ```python
  from operations import update  # noqa: E402

  def is_update_operation(context: dict[str, Any]) -> bool:
      return context.get("operation") == "update"
  ```

  Add routing in `get_questions()` and `execute()` before the
  extension fallthrough:

  ```python
  if is_update_operation(context):
      return update.get_questions(context)

  if is_update_operation(context):
      return update.execute(context, responses)
  ```

- The update operation does NOT use `templates_dir` from `_paths.py`
  for extension templates. It uses `SCAFFOLD_TEMPLATES_DIR` from
  `scaffold.py` (or better, from its own path resolution, since
  both point to the same `templates/scaffold/` directory).

---

### Task 7: Update SKILL.md with update operation documentation

**Description:** Add the update operation to the SKILL.md document:
operations table, activation trigger, workflow section, and resources.

**Files to modify:**

- `skills/plugin-manager/SKILL.md`

**Dependencies:** Task 6 (API is defined).

**Size:** S

**Key implementation notes:**

- Add to the Activation section:
  "- User invokes /aida plugin update"
- Add to the Operations table:
  `| update | Update | Scan and patch an existing plugin to current standards |`
- Add a new `### Update Operation` section after `### Scaffold
  Operation` documenting:
  - Phase 1 command syntax with example
  - Phase 2 command syntax with example
  - What the scan report contains
  - What the patch does
  - Backup location
- Add to Resources section:
  - `operations/update.py` -- Plugin update entry point
  - `operations/update_ops/` -- Update submodules (scanner, differ,
    patcher, strategies, models)
- Add to references section:
  - `update-workflow.md` -- Update workflow reference

---

### Task 8: Create `references/update-workflow.md`

**Description:** Create the reference document that describes the
end-to-end update workflow, file classification details, and merge
strategy behavior.

**Files to create:**

- `skills/plugin-manager/references/update-workflow.md`

**Dependencies:** Task 6 (workflow is finalized).

**Size:** S

**Key implementation notes:**

- Follow the structure of `scaffolding-workflow.md` as a model.
- Include:
  - End-to-end flow (numbered steps)
  - File classification table (from this workplan)
  - Merge strategy details for each category
  - Template variable source (how they are inferred from the
    existing plugin)
  - Backup and rollback information
  - Error handling table
  - Post-update steps
- Use YAML frontmatter: `type: reference`, `title: Plugin Update
  Workflow`.
- Line length: 88 characters (matches ruff/markdownlint config).

---

### Task 9: Unit tests for scanner

**Description:** Write comprehensive unit tests for the scanner
module covering all file categories, language detection, missing
files, outdated files, up-to-date files, and edge cases.

**Files to create:**

- `tests/unit/test_update_scanner.py`

**Dependencies:** Task 4 (scanner implementation).

**Size:** L

**Key implementation notes:**

- Follow the test patterns in `tests/unit/test_scaffold.py`:
  `unittest.TestCase` classes with `@patch` decorators and
  `tempfile.TemporaryDirectory` for filesystem tests.
- Path setup block at top of file (same pattern as test_scaffold.py):

  ```python
  _project_root = Path(__file__).parent.parent.parent
  _plugin_scripts = (
      _project_root / "skills" / "plugin-manager" / "scripts"
  )
  sys.path.insert(0, str(_project_root / "scripts"))
  sys.path.insert(0, str(_plugin_scripts))
  ```

- Test classes:
  - `TestScanValidPlugin` -- scaffolded plugin with all files
    present and up to date
  - `TestScanMissingFiles` -- plugin missing specific files
  - `TestScanOutdatedFiles` -- plugin with stale boilerplate
  - `TestScanCustomFiles` -- verify CLAUDE.md, README.md are
    always classified as custom/skip
  - `TestScanLanguageDetection` -- python vs typescript detection
  - `TestScanNoPluginJson` -- invalid plugin directory
  - `TestScanNoAidaConfig` -- missing aida-config.json (defaults
    to version 0.0.0)
  - `TestScanGitignoreDiff` -- missing entries detected
  - `TestScanMakefileDiff` -- missing targets detected
  - `TestScanDependencyConfig` -- pyproject.toml flagged for
    manual review
- Create test fixtures using `tempfile.TemporaryDirectory`:
  scaffold a minimal plugin structure with known file contents,
  then selectively modify/delete files to test each scenario.
- Use the actual templates directory for rendering expected content
  (do not mock template rendering -- this catches template drift).

---

### Task 10: Unit tests for patcher

**Description:** Write unit tests for the patcher module covering
all merge strategies, atomic writes, backup creation, and error
handling.

**Files to create:**

- `tests/unit/test_update_patcher.py`

**Dependencies:** Task 5 (patcher implementation).

**Size:** L

**Key implementation notes:**

- Test classes:
  - `TestBackupCreation` -- verify backup directory structure and
    contents
  - `TestOverwriteStrategy` -- file replaced with new content
  - `TestAddStrategy` -- file created when missing, skipped when
    present
  - `TestSkipStrategy` -- file never modified
  - `TestGitignoreMerge` -- missing entries appended, existing
    entries preserved, duplicates not added
  - `TestMakefileMerge` -- missing targets appended, existing
    targets preserved
  - `TestManualReviewStrategy` -- no modification, informational
    result returned
  - `TestAtomicWrites` -- verify .tmp file is used (mock
    `os.replace` to confirm call)
  - `TestPartialFailure` -- one write fails, others succeed,
    all results returned
  - `TestGeneratorVersionUpdate` -- aida-config.json updated
    after patching
  - `TestUserOverrides` -- strategy overrides applied correctly
- Use `tempfile.TemporaryDirectory` for all filesystem tests.
- Verify backup contents match originals byte-for-byte.

---

### Task 11: Integration test and end-to-end validation

**Description:** Write integration tests that exercise the full
update flow through `manage.py` (Phase 1 scan, Phase 2 patch) and
validate the end-to-end behavior.

**Files to create:**

- `tests/unit/test_update_integration.py`

**Dependencies:** Task 6 (full flow wired up), Task 9, Task 10.

**Size:** M

**Key implementation notes:**

- Test classes:
  - `TestUpdatePhase1` -- call `manage.py --get-questions` with
    `operation: update` and verify scan report structure
  - `TestUpdatePhase2` -- call `manage.py --execute` with
    `operation: update` and verify files are patched
  - `TestUpdateRoundTrip` -- scaffold a plugin, modify some files,
    run update, verify corrections
  - `TestUpdateIdempotent` -- run update twice on same plugin,
    verify no changes on second run
  - `TestUpdatePreservesCustomContent` -- modify CLAUDE.md and
    README.md, run update, verify they are untouched
- Use `tempfile.TemporaryDirectory` to create an isolated plugin.
- Scaffold a known plugin using `scaffold.execute()`, then:
  1. Delete a boilerplate file (e.g., `.markdownlint.json`).
  2. Modify `.gitignore` to remove some entries.
  3. Delete a Makefile target.
  4. Run update Phase 1 and verify the diff report.
  5. Run update Phase 2 and verify the patched state.
  6. Run update Phase 1 again and verify everything is up to date.
- Run `make lint` on the patched plugin directory to verify the
  output is lint-clean.

## Task Dependency Graph

```text
Task 1: Extract shared constants + template var builder
  |
  +---> Task 2: Add generator_version to aida-config template
  |
  +---> Task 3: Create update_ops/ with models + strategies
          |
          +---> Task 4: Implement scanner
          |       |
          |       +---> Task 9: Unit tests for scanner
          |       |
          |       +---> Task 5: Implement patcher
          |               |
          |               +---> Task 10: Unit tests for patcher
          |               |
          |               +---> Task 6: Implement update.py + manage.py routing
          |                       |
          |                       +---> Task 7: Update SKILL.md
          |                       |
          |                       +---> Task 8: Create update-workflow.md
          |                       |
          |                       +---> Task 11: Integration tests

Parallelizable groups:
  - Tasks 2 and 3 (after Task 1)
  - Tasks 9 and 5 (after Task 4)
  - Tasks 7, 8, and 11 (after Task 6)
```

## Acceptance Criteria

These criteria are derived from the Product Manager review, refined
with technical constraints from the other reviewers.

**AC-1: Scan report accuracy.** Phase 1 produces a categorized diff
report that correctly classifies every scaffolded file into one of
the four categories (custom, boilerplate, composite, new) with
accurate status (missing, outdated, up-to-date, custom-skip).

**AC-2: Missing file detection.** Files present in the current
scaffold templates but absent from the plugin are reported as
MISSING with the correct add/overwrite strategy.

**AC-3: Outdated file detection.** Boilerplate files whose content
differs from the current template rendering are reported as
OUTDATED.

**AC-4: Custom content preservation.** `CLAUDE.md`, `README.md`,
`LICENSE`, and `aida-config.json` are never modified by the update
operation regardless of their content.

**AC-5: Boilerplate overwrite.** When the user approves (or accepts
the default), outdated boilerplate files are replaced with current
template output.

**AC-6: Gitignore merge.** Missing `.gitignore` entries are appended
without removing or reordering existing entries.

**AC-7: Makefile merge.** Missing Makefile targets are appended
without modifying or removing existing targets.

**AC-8: Backup creation.** A timestamped backup of all files that
will be modified is created at `.aida-backup/{timestamp}/` before
any patches are applied.

**AC-9: Generator version tracking.** After a successful update,
`aida-config.json` contains the current `generator_version`. Newly
scaffolded plugins also include this field.

**AC-10: Idempotent.** Running update on an already up-to-date
plugin produces no changes and reports all files as UP_TO_DATE.

**AC-11: Language detection.** The scanner correctly detects Python
vs TypeScript plugins based on `pyproject.toml` / `package.json`
presence.

**AC-12: Dependency config safety.** `pyproject.toml` and
`package.json` are never auto-modified. Differences are reported
for manual review.

**AC-13: Two-phase API compliance.** The update operation follows
the same `get_questions()` / `execute()` pattern as scaffold and
extension operations, with the same JSON response shape.

## Testing Strategy

### Unit Tests (Tasks 9, 10)

- **Scanner tests** (`test_update_scanner.py`): ~15 test methods
  covering all file categories, language detection, edge cases.
- **Patcher tests** (`test_update_patcher.py`): ~15 test methods
  covering all strategies, atomic writes, backup, error handling.
- **Model tests**: Implicitly covered by scanner/patcher tests.
  Add dedicated tests if model logic grows beyond property methods.

### Integration Tests (Task 11)

- **Round-trip test**: Scaffold -> modify -> update -> verify.
- **Idempotency test**: Update -> update -> verify no changes.
- **Preservation test**: Modify custom files -> update -> verify
  untouched.
- **Phase 1/Phase 2 contract test**: Verify JSON response shapes.

### Test Fixtures

- Use `tempfile.TemporaryDirectory` for all filesystem tests (no
  permanent fixtures needed).
- Scaffold minimal plugins programmatically using the existing
  `scaffold.execute()` function (integration tests) or by creating
  files directly (unit tests).
- Use the real templates directory for rendering (catches template
  drift; no mocking of template content).

### Test Conventions

- `unittest.TestCase` with `@patch` decorators (matching existing
  test patterns in `tests/unit/test_scaffold.py`).
- Path setup via `sys.path.insert()` at top of each test file.
- Module cache clearing for operations imports (same pattern as
  existing tests).
- Ruff-compliant: 88-char line length, modern type hints.

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Makefile merge produces invalid syntax | Medium | High | Conservative approach: only append complete target blocks; validate by checking for tab-indented recipe lines. Add lint verification in integration tests. |
| R2 | Template changes break scanner expectations | Medium | Medium | Scanner uses real template rendering, not hardcoded expectations. Integration test scaffolds then updates to catch drift. |
| R3 | `.gitignore` merge adds duplicate entries | Low | Low | Set-based comparison ensures entries are only added if truly missing. |
| R4 | Plugin has manually restructured files | Medium | Medium | Scanner only checks files listed in the strategy registry. Unknown files are ignored. The report clearly shows what was checked. |
| R5 | `aida-config.json` has user customizations that conflict with new field | Low | Medium | `generator_version` is added at top level, not inside `config`. JSON merge preserves existing keys. |
| R6 | Backup directory grows unbounded | Low | Low | Out of scope for v1.0. Documented as deferred (v1.1 backup retention policy). Advisory note in post-update summary. |
| R7 | Atomic write fails on some filesystems | Low | High | Fallback: if `os.replace()` fails, fall back to direct write with a warning. Backup ensures recoverability either way. |
| R8 | Version bootstrapping for pre-tracking plugins | Medium | Low | Default to `"0.0.0"` when `generator_version` is absent. Scanner compares actual content, not versions, so this is informational only. |
| R9 | Plugin uses language not yet supported | Low | Medium | Scanner validates detected language against `SUPPORTED_LANGUAGES`. Returns clear error if unsupported. |
| R10 | Test isolation: operations module cache conflicts | Medium | Medium | Use the same `sys.modules` cache-clearing pattern established in `test_scaffold.py`. |

## Open Questions

1. **Makefile `.PHONY` line handling.** When appending new targets,
   should the patcher also update the `.PHONY` declaration? The
   current scaffold templates declare `.PHONY` at the section level.
   Recommendation: Yes, append missing target names to the
   appropriate `.PHONY` line, or add a new `.PHONY` line for the
   appended block.

2. **Plugin metadata re-rendering.** When overwriting `plugin.json`
   or `marketplace.json`, the patcher re-renders the template with
   values read from the existing file. Should we deep-merge existing
   JSON with template output, or render fresh and overwrite?
   Recommendation: Read existing values, use them as template
   variables, render fresh. This updates schema structure while
   preserving user data.

3. **Multi-language plugins.** Should the scanner support plugins
   that have both Python and TypeScript tooling? Recommendation:
   Not for v1.0. Detect the primary language and warn if artifacts
   of both are present.

4. **Update from non-scaffolded plugins.** Plugins created manually
   (not via `/aida plugin scaffold`) may have very different
   structures. Should update support them? Recommendation: Yes,
   with reduced confidence. The scanner reports what it finds; the
   patcher only modifies files in the strategy registry. Manual
   plugins get an advisory note in the report.

## Definition of Done

- [ ] `operations/constants.py` created with `GENERATOR_VERSION` and
      `SUPPORTED_LANGUAGES`
- [ ] `operations/shared.py` created with `build_template_variables()`
- [ ] `scaffold.py` imports from `constants.py` and `shared.py`;
      all existing scaffold tests pass
- [ ] `aida-config.json.jinja2` template includes `generator_version`
- [ ] `schemas.md` updated with `generator_version` documentation
- [ ] `update_ops/` subpackage created with `models.py` and
      `strategies.py`
- [ ] `update_ops/scanner.py` implemented and tested
- [ ] `update_ops/patcher.py` implemented and tested
- [ ] `operations/update.py` implemented with `get_questions()` and
      `execute()`
- [ ] `manage.py` routes `operation: "update"` to `update` module
- [ ] SKILL.md updated with update operation documentation
- [ ] `references/update-workflow.md` created
- [ ] Unit tests for scanner: all pass (`test_update_scanner.py`)
- [ ] Unit tests for patcher: all pass (`test_update_patcher.py`)
- [ ] Integration tests: round-trip, idempotency, preservation
      (`test_update_integration.py`)
- [ ] `make lint` passes with zero warnings
- [ ] `make test` passes with zero failures
- [ ] No regressions in existing scaffold, extension, or manage tests
