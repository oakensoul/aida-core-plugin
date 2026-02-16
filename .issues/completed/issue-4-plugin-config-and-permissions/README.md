---
type: issue
issue: 4
title: "Plugin configuration discovery and permissions management for /aida config"
status: "Done"
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/4"
branch: "task/4-plugin-config-and-permissions"
worktree: "issue-4-plugin-config-and-permissions"
started: "2026-02-15"
completed: "2026-02-15"
assignee: "@me"
actual_effort: "3h"
pr: 11
---

# Issue #4: Plugin configuration discovery and permissions management

**Status**: Done
**Branch**: `task/4-plugin-config-and-permissions`
**Worktree**: `issue-4-plugin-config-and-permissions`

## Description

Two related enhancements to `/aida config`:

1. **Plugin Configuration Discovery** — Plugins declare configurable
   capabilities in `plugin.json`. `/aida config` discovers installed plugins
   with config sections and presents a multi-select checklist so users pick
   which plugin integrations they want for the current project.

2. **Permissions Management** — Plugins declare recommended permissions in
   `plugin.json`. A new `/aida config permissions` skill aggregates
   recommendations from all installed plugins, presents them as categories
   (Git Operations, GitHub CLI, Docker, etc.), and writes the chosen rules to
   the correct `settings.json` scope (user vs project).

## Part 1: Plugin Configuration Discovery

### Plugin Config Declaration (in `plugin.json`)

Plugins declare a `config` section with preferences:

```json
{
  "config": {
    "label": "GitHub Workflow Integration",
    "description": "Set up PR templates, branch naming, and workflow automation",
    "preferences": [
      {
        "key": "github.pr_template",
        "type": "boolean",
        "label": "Use PR templates",
        "default": true
      }
    ]
  }
}
```

### Flow

1. Detect project facts (existing behavior)
2. Discover installed plugins with `config` sections
3. Present multi-select checklist of available plugin configs
4. Ask preference questions for selected plugins
5. Save to `aida-project-context.yml` under `plugins:` key

## Part 2: Permissions Management

### Plugin-Declared Recommended Permissions

```json
{
  "recommendedPermissions": {
    "git-operations": {
      "label": "Git Operations",
      "description": "Commit, push, branch, and other git workflow commands",
      "rules": ["Bash(git add:*)", "Bash(git commit:*)", "..."],
      "suggested": "allow"
    }
  }
}
```

### `/aida config permissions` Skill

1. Scan installed plugins for `recommendedPermissions`
2. Read current permissions from user + project settings
3. Deduplicate and categorize across all plugins
4. Present categories interactively (allow / ask / deny per category)
5. Ask scope: user settings (global) or project settings (this repo)
6. Write rules to the appropriate `settings.json`

### Bonus Features

- Permission presets ("Developer workstation", "CI-safe", "Locked down")
- Diff on plugin update (show what changed, ask to accept)
- Audit mode (`/aida config permissions --audit`)

### Permissions Precedence Reference

Highest to lowest priority:

1. Managed (system-level, cannot be overridden)
2. Command line arguments (session overrides)
3. Local (`.claude/settings.local.json`)
4. Project (`.claude/settings.json`)
5. User (`~/.claude/settings.json`)

Within a single file: deny > ask > allow.

## Files to Change

### Part 1: Config Discovery

- `skills/aida-dispatch/scripts/configure.py` — plugin discovery scan
- `skills/aida-dispatch/references/config.md` — document new config step

### Part 2: Permissions Skill

- `skills/permissions/SKILL.md` — new skill definition
- `skills/permissions/scripts/` — scanning, merging, writing logic
- `skills/permissions/references/` — rule syntax reference, presets
- `skills/aida-dispatch/SKILL.md` — add `/aida config permissions` route

### Shared

- `.claude-plugin/plugin.json` — add `config` and `recommendedPermissions`
  (dogfood)
- `agents/aida/knowledge/config-schema.md` — add `plugins:` section
- `skills/claude-code-management/references/schemas.md` — add schemas
- `agents/claude-code-expert/knowledge/plugin-development.md` — document
  patterns

### Tests

- Plugin config discovery (scanning plugin directories)
- Config preference merging into YAML
- Plugin.json config schema validation
- Permission scanning and aggregation from multiple plugins
- Permission rule deduplication and categorization
- Settings.json read/write for both user and project scopes

## Acceptance Criteria

### Config Discovery

- [x] Plugins can declare config capabilities in `plugin.json`
- [x] `/aida config` discovers installed plugins with config sections
- [x] Multi-select checklist of available plugin configs
- [x] Plugin preferences saved to `aida-project-context.yml`

### Permissions Management

- [x] Plugins can declare `recommendedPermissions` in `plugin.json`
- [x] `/aida config permissions` scans and aggregates recommendations
- [x] Interactive category-based setup with allow/ask/deny
- [x] User chooses scope (user vs project settings)
- [x] Rules written to correct `settings.json`
- [x] Integrates as optional step in `/aida config` flow

### Shared

- [x] `plugin.json` schema documented for plugin authors
- [x] All linters pass (`make lint`)
- [x] All tests pass (`make test`)

## Resolution

**Completed**: 2026-02-15
**Pull Request**: #11

### Changes Made

- Plugin config discovery with scanning, schema validation, and
  multi-select checklist generation
- Permissions management skill with two-phase interactive API,
  presets (developer-workstation, ci-safe, locked-down), and audit mode
- Scanner, aggregator, settings manager, and rule validation modules
- 352 tests covering all components
- Documentation for plugin authors (schemas, plugin development guide)
- Frontmatter validation schema extended with `issue` type

### Implementation Details

- Two-phase API pattern: `get_questions(context)` then `execute(context, responses)`
- Permission rules validated at scan time to reject malformed plugin data early
- Settings written atomically with advisory file locking (`fcntl.flock`)
- Symlink and path traversal protections in plugin cache scanning
- Cross-skill `sys.path` manipulation removed in favor of local `_paths.py`

## Work Tracking

- Started: 2026-02-15
- Completed: 2026-02-15
- Actual effort: ~3h
- Branch: `task/4-plugin-config-and-permissions`
- Worktree: `issue-4-plugin-config-and-permissions`

## Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/4)
