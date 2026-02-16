---
type: reference
title: "Plan: Move Memento Storage to User-Level (Issue #3)"
---

# Plan: Move Memento Storage to User-Level (Issue #3)

## Context

Mementos currently live at `{project_root}/.claude/mementos/`, tying them to a
specific project directory and making them invisible across branches. Claude
Code's built-in Memories already handle persistent per-project knowledge.
Mementos serve a different purpose -- they're work-in-progress session snapshots
-- and belong at the user level (`~/.claude/memento/`) where they're
branch-independent and accessible across all projects.

## Team Structure

| Agent | Type | Role |
|-------|------|------|
| **lead** | general-purpose | Orchestrator, code reviews, Phase 1 core logic |
| **template-worker** | general-purpose | Phase 2 templates + Phase 4A-4C docs |
| **test-worker** | general-purpose | Phase 3 tests |
| **docs-worker** | general-purpose | Phase 4D-4E docs + final grep audit |

## Phase 1: Core Python Logic (lead)

**File:** `skills/memento/scripts/memento.py`

### 1A. Remove old constants and functions

- Delete constants `MEMENTOS_DIR` and `ARCHIVE_DIR` (lines 56-57)
- Delete `get_project_root()` (lines 117-127)
- Delete `get_mementos_dir()` (lines 130-140)
- Delete `get_archive_dir()` (lines 143-153)

### 1B. Add new helper functions

**`get_project_context()`** - Detects project name, path, repo, branch from
git. Walks up for `.git`, runs `git remote get-url origin` and
`git rev-parse --abbrev-ref HEAD`. Falls back to `cwd.name` if not in a repo.

**`get_user_mementos_dir()`** - Returns `Path.home() / ".claude" / "memento"`

**`get_user_archive_dir()`** - Returns
`Path.home() / ".claude" / "memento" / ".completed"`

**`make_memento_filename(project_name, slug)`** - Returns
`"{project}--{slug}.md"`

**`parse_memento_filename(filename)`** - Splits on first `--`, returns
`(project_name, slug)`. Raises `ValueError` if no `--` found.

### 1C. Extend `parse_frontmatter()` for nested YAML blocks

Current parser handles flat key-value, JSON arrays, YAML lists. Add support
for one level of indented nested blocks (e.g., `project:` with indented
sub-keys). Track indentation to detect nested dict start/end.

Also update `execute_update()` frontmatter reconstruction (lines 839-846) to
handle `isinstance(value, dict)` by emitting indented sub-keys.

### 1D. Update `find_memento()`

- Add `project_name` parameter (auto-detected if not provided)
- Use `make_memento_filename()` for path lookup
- Search in `get_user_mementos_dir()` / `get_user_archive_dir()`
- Include `"project"` key in return dict

### 1E. Update `list_mementos()`

- Add `project_filter` and `all_projects` parameters
- Default: filter to current project via `get_project_context()["name"]`
- Use `parse_memento_filename()` to extract project from each file
- Include `"project"` key in each memento dict

### 1F. Update `get_questions()`

- Pass project context to `find_memento()` for slug conflict checks
- Pass filtering params to `list_mementos()` in update/read/complete/remove
- Accept `all_projects` and `project_filter` context fields for list ops

### 1G. Update all `execute_*()` functions

- **`execute_create()`**: Call `get_project_context()`, pass project vars to
  template, use `get_user_mementos_dir()`, use `make_memento_filename()`
- **`execute_read()`**: Pass project context to `find_memento()`
- **`execute_list()`**: Extract and pass filtering params
- **`execute_update()`**: Pass project context to `find_memento()`
- **`execute_complete()`**: Use `get_user_archive_dir()`, pass project context
- **`execute_remove()`**: Pass project context to `find_memento()`

### Phase 1 Verification

```bash
ruff check skills/memento/scripts/memento.py
python3 skills/memento/scripts/memento.py --help
```

---

### Code Review 1 (lead reviews)

**Focus:** Correctness of `get_project_context()` edge cases (no remote,
detached HEAD, non-git dirs). `parse_frontmatter()` nested block handling.
Frontmatter round-trip in `execute_update()`. No orphan refs to old functions.

---

## Phase 2: Templates (template-worker, parallel with Review 1)

**Files:**

- `skills/memento/templates/work-session.md.jinja2`
- `skills/memento/templates/freeform.md.jinja2`

### Changes (both files)

Add `project:` nested block to YAML frontmatter after `files:`:

```jinja2
project:
  name: {{ project_name | default('') }}
  path: {{ project_path | default('') }}
  repo: {{ project_repo | default('') }}
  branch: {{ project_branch | default('') }}
```

### Phase 2 Verification

Visual inspection of YAML indentation (2-space indent). Verify variable names
match what `execute_create()` passes.

---

### Code Review 2 (lead reviews template-worker's output)

**Focus:** YAML formatting correct. Variable names match Python code. Both
templates have identical frontmatter structure.

---

## Phase 3: Tests (test-worker, after Phase 1 approved)

**File:** `tests/unit/test_memento.py`

### 3A. Add new imports

Add `make_memento_filename`, `parse_memento_filename`, `get_project_context`,
`get_user_mementos_dir`, `get_user_archive_dir` to the import block. Add
`unittest.mock` import.

### 3B. New test class: `TestMementoFilename`

- `test_make_filename` - basic namespaced filename
- `test_parse_filename` - parse with and without `.md` extension
- `test_parse_filename_no_separator` - raises `ValueError`
- `test_roundtrip` - make then parse returns original values
- `test_project_name_with_hyphens` - single hyphens don't confuse parser

### 3C. New test class: `TestNestedFrontmatter`

- `test_project_block` - full nested `project:` block parsed correctly
- `test_project_block_with_flat_fields` - nested block coexists with flat
  fields before and after
- `test_empty_nested_block` - key with no sub-keys yields empty dict

### 3D. New test class: `TestProjectContext`

Mock `subprocess.run` to test:

- Git repo with remote and branch
- Non-git directory fallback to `cwd.name`
- Subprocess failures handled gracefully

### 3E. New test class: `TestListFiltering`

Set up temp dir with mementos for multiple projects. Mock
`get_user_mementos_dir`, `get_user_archive_dir`, `get_project_context`.

- `test_list_defaults_to_current_project` - only current project's mementos
- `test_list_all_projects` - all projects shown
- `test_list_specific_project` - filter by name

### 3F. Update existing tests

Tests that call `get_questions()` or `execute()` now reach
`get_project_context()` and `get_user_mementos_dir()` internally. Add
`@unittest.mock.patch` decorators to mock these at the function level.

### 3G. Update `run_tests()`

Add new test classes to the suite.

### Phase 3 Verification

```bash
pytest tests/unit/test_memento.py -v
ruff check tests/
make test
```

---

### Code Review 3 (lead reviews test-worker's output)

**Focus:** Coverage of all new functions. Mock strategy (function-level, not
`Path.home()`). Edge cases tested. Existing tests still meaningful. No test
touches actual `~/.claude/memento/`.

---

## Phase 4: Documentation (template-worker + docs-worker, parallel, after Phase 1 approved)

### 4A. `skills/memento/SKILL.md` (template-worker)

- Update Memento Storage paths to `~/.claude/memento/` and `.completed/`
- Add `--all` and `--project <name>` to list operation examples
- Update Complete section to reference `.completed/` not `.archive/`
- Update example workflows with new paths

### 4B. `skills/memento/references/memento-workflow.md` (template-worker)

- Update all `.claude/mementos/` references to `~/.claude/memento/`
- Update `.archive/` to `.completed/`
- Add `project` field to JSON output examples
- Add `project_name/path/repo/branch` to Template Variables table
- Add `project_filter` and `all_projects` context fields for list operations

### 4C. `agents/aida/knowledge/memento-format.md` (template-worker)

- Update File Location to `~/.claude/memento/{project}--{slug}.md`
- Add `project:` nested block to Required Structure example
- Add brief note about `--` separator convention

### 4D. `agents/aida/knowledge/troubleshooting.md` (docs-worker)

- Update Memento Operations Failing section paths from `.claude/mementos/`
  to `~/.claude/memento/`
- Update fix command: `mkdir -p ~/.claude/memento`

### 4E. `skills/aida-dispatch/SKILL.md` (docs-worker)

- Add new list filter examples to Memento Commands section:
  `/aida memento list --all` and `/aida memento list --project <name>`
- Update Help Text with new list options

### Phase 4 Verification

```bash
make lint
```

Grep audit for stale references:

```bash
grep -r "\.claude/mementos" .        # should return 0 results
grep -r "\.archive" .                # should return 0 results
grep -r "get_project_root\|get_mementos_dir\|get_archive_dir" skills/ tests/
```

---

### Code Review 4 - Final Review (lead reviews all)

**Focus:** All docs consistent on paths, naming, behavior. JSON examples
match actual script output. Line length complies with `.markdownlint.json`.
No stale references anywhere. Full `make lint && make test` passes.

---

## Execution Timeline

```text
         lead              template-worker     test-worker      docs-worker
         ----              ---------------     -----------      -----------
Phase 1  [core python]
Review 1 [review core]     [Phase 2 templates]
Review 2 [review templates]
                                               [Phase 3 tests]
Phase 4                    [4A, 4B, 4C docs]                    [4D, 4E docs]
Review 3 [review tests]
Review 4 [final review of all docs + full lint + test]
```

## Acceptance Criteria

- [ ] Mementos stored at `~/.claude/memento/` (user-level, branch-independent)
- [ ] Filenames use `{project}--{slug}.md` pattern
- [ ] Project context auto-detected and saved in frontmatter
- [ ] List defaults to current project; supports `--all` and `--project`
- [ ] All linters pass (`make lint`)
- [ ] All tests pass (`make test`)
- [ ] No stale path references in codebase
- [ ] Code reviewed at each phase boundary

## Critical Files

| File | Changes |
|------|---------|
| `skills/memento/scripts/memento.py` | Core: paths, namespacing, frontmatter, filtering |
| `tests/unit/test_memento.py` | New tests + mock updates for existing tests |
| `skills/memento/templates/work-session.md.jinja2` | Add `project:` frontmatter |
| `skills/memento/templates/freeform.md.jinja2` | Add `project:` frontmatter |
| `skills/memento/SKILL.md` | Paths, list filtering, examples |
| `skills/memento/references/memento-workflow.md` | Paths, JSON examples, new fields |
| `agents/aida/knowledge/memento-format.md` | File location, schema |
| `agents/aida/knowledge/troubleshooting.md` | Diagnostic paths |
| `skills/aida-dispatch/SKILL.md` | List filter options |
