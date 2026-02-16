---
type: issue
issue: 3
title: "Move memento storage from project-level to user-level"
status: "Completed"
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/3"
pr_url: "https://github.com/oakensoul/aida-core-plugin/pull/10"
branch: "task/3-memento-user-level-storage"
worktree: "issue-3-memento-user-level-storage"
started: "2026-02-15"
assignee: "@me"
---

# Issue #3: Move memento storage from project-level to user-level

**Status**: Completed (PR #10)
**Branch**: `task/3-memento-user-level-storage`
**Worktree**: `issue-3-memento-user-level-storage`

## Description

Mementos currently live at `{project_root}/.claude/memento/`, which means
they're tied to a specific project directory and don't survive branch switches
(unless committed). Meanwhile, Claude Code's built-in Memories already handle
persistent per-project knowledge. Mementos serve a different purpose — they're
work-in-progress session snapshots — and belong at the user level where they're
branch-independent and accessible across all projects.

## Requirements

### Storage Location

- Active: `~/.claude/memento/`
- Completed: `~/.claude/memento/.completed/`

### Filename Namespacing

Use `{project}--{slug}.md` to avoid cross-project slug collisions. The `--`
separator is safe because slug validation only allows single hyphens.
User-facing slug stays simple (e.g., `fix-auth-bug`), script resolves it via
current project context.

### New Frontmatter Fields

Auto-detected nested `project:` block:

```yaml
project:
  name: aida-core-plugin
  path: /Users/.../aida-core-plugin
  repo: oakensoul/aida-core-plugin
  branch: feature/fix-auth-bug
```

### List Filtering

- Default: show mementos for the **current project** only
- `--all`: show mementos across all projects
- `--project <name>`: show mementos for a specific project

### No Migration

Clean break. Old project-level files stay where they are.

## Files to Change

### Python Script (`skills/memento/scripts/memento.py`)

- Replace `get_mementos_dir(project_root)` / `get_archive_dir(project_root)`
  with `get_user_mementos_dir()` / `get_user_archive_dir()` using
  `Path.home()`
- Add `get_project_context()` — detects name, path, repo, branch from git
- Add `make_memento_filename()` / `parse_memento_filename()` for
  `{project}--{slug}.md` namespacing
- Update `find_memento()`, `list_mementos()`, all `execute_*()` functions
- Extend `parse_frontmatter()` to handle nested `project:` block
- Update `get_questions()` for project-aware slug conflict checks and list
  filtering

### Templates

- `skills/memento/templates/work-session.md.jinja2` — add `project:`
  frontmatter block
- `skills/memento/templates/freeform.md.jinja2` — same

### Documentation

- `skills/memento/SKILL.md` — paths, list filtering docs, examples
- `skills/memento/references/memento-workflow.md` — all path refs and JSON
  examples
- `agents/aida/knowledge/memento-format.md` — file location, schema
- `agents/aida/knowledge/troubleshooting.md` — diagnostic paths
- `skills/aida-dispatch/SKILL.md` — add `--all` and `--project` list options

### Tests (`tests/unit/test_memento.py`)

- Update existing tests to mock user-level paths
- Add tests for: filename namespacing, project context detection, list
  filtering, nested frontmatter parsing

## Acceptance Criteria

- [x] Mementos stored at `~/.claude/memento/` (user-level, branch-independent)
- [x] Filenames use `{project}--{slug}.md` pattern
- [x] Project context auto-detected and saved in frontmatter
- [x] List defaults to current project; supports `--all` and `--project`
      filters
- [x] All linters pass (`make lint`)
- [x] All tests pass (`make test`)

## Work Tracking

- Started: 2026-02-15
- Branch: `task/3-memento-user-level-storage`
- Worktree: `issue-3-memento-user-level-storage`

## Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/3)
- [Pull Request #10](https://github.com/oakensoul/aida-core-plugin/pull/10)
