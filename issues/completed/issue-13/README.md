---
type: issue
issue: 13
title: "Move config and recommendedPermissions from plugin.json to aida-config.json"
status: "Completed"
created: "2026-02-16"
completed: "2026-02-16"
actual_effort: 2
estimated_effort: 2
---

# Issue #13: Move config and recommendedPermissions from plugin.json to aida-config.json

**Status**: Completed
**Labels**: bug
**Milestone**: none
**Assignees**: none

## Description

The Claude Code plugin validator rejects unrecognized keys `config` and
`recommendedPermissions` in `.claude-plugin/plugin.json`, preventing the plugin
from loading entirely:

```text
Plugin aida-core has an invalid manifest file at
.claude-plugin/plugin.json.

Validation errors: : Unrecognized keys: "config", "recommendedPermissions"
```

The plugin manifest schema only allows: `name`, `description`, `author`,
`version`, `repository`, `homepage`, `license`, `keywords`, `commands`,
`agents`, `skills`, `hooks`, `mcpServers`, `outputStyles`, `lspServers`.

These AIDA-specific fields (`config` and `recommendedPermissions`) need to be
moved to a separate file (`.claude-plugin/aida-config.json`) that the AIDA
system can discover and read independently of the Claude Code plugin validator.

## Requirements

- [x] Remove `config` and `recommendedPermissions` keys from
      `.claude-plugin/plugin.json`
- [x] Create `.claude-plugin/aida-config.json` containing the moved fields
- [x] Update `skills/aida-dispatch/scripts/utils/plugins.py`
      `discover_installed_plugins()` to read from `aida-config.json`
- [x] Update `skills/permissions/scripts/scanner.py` `scan_plugins()` to read
      `recommendedPermissions` from `aida-config.json`
- [x] Update all unit tests in `tests/unit/test_plugin_discovery.py` and
      `tests/unit/test_permissions.py` to reflect new file location
- [x] Verify plugin loads successfully after changes

## Technical Details

### Files to modify

- `.claude-plugin/plugin.json` - Remove `config` and `recommendedPermissions`
- `.claude-plugin/aida-config.json` - New file with moved fields
- `skills/aida-dispatch/scripts/utils/plugins.py` - Update
  `discover_installed_plugins()` to read `aida-config.json` alongside
  `plugin.json`
- `skills/permissions/scripts/scanner.py` - Update `scan_plugins()` to read
  `recommendedPermissions` from `aida-config.json`
- `tests/unit/test_plugin_discovery.py` - Update test fixtures and assertions
- `tests/unit/test_permissions.py` - Update test fixtures and assertions

### New file structure

```json
// .claude-plugin/aida-config.json
{
  "config": {
    "label": "AIDA Core Configuration",
    "description": "Configure AIDA workflow preferences",
    "preferences": [
      {
        "key": "workflow.automation_level",
        "type": "choice",
        "label": "Workflow automation level",
        "options": ["Manual", "Assisted", "Automatic"],
        "default": "Assisted"
      }
    ]
  },
  "recommendedPermissions": {
    "git-operations": {
      "label": "Git Operations",
      "description": "Commit, push, branch, and other git commands",
      "rules": [
        "Bash(git add:*)",
        "Bash(git branch:*)",
        "Bash(git checkout:*)",
        "Bash(git commit:*)",
        "Bash(git fetch:*)",
        "Bash(git merge:*)",
        "Bash(git pull:*)",
        "Bash(git push:*)",
        "Bash(git rebase:*)",
        "Bash(git remote:*)",
        "Bash(git reset:*)",
        "Bash(git stash:*)"
      ],
      "suggested": "allow"
    },
    "github-cli": {
      "label": "GitHub CLI",
      "description": "Issue, PR, and repo management via gh",
      "rules": [
        "Bash(gh api:*)",
        "Bash(gh issue:*)",
        "Bash(gh label:*)",
        "Bash(gh pr:*)",
        "Bash(gh repo view:*)"
      ],
      "suggested": "allow"
    }
  }
}
```

### Plugin discovery update pattern

In `plugins.py`, after reading `plugin.json`, also attempt to read
`aida-config.json` from the same directory:

```python
aida_config_path = plugin_dir / "aida-config.json"
if aida_config_path.exists():
    aida_config = json.loads(aida_config_path.read_text())
    plugin_info["config"] = aida_config.get("config", {})
    plugin_info["recommendedPermissions"] = aida_config.get(
        "recommendedPermissions", {}
    )
```

## Success Criteria

- [x] Plugin loads without validation errors
- [x] `aida-config.json` is discovered and read by the plugin system
- [x] Plugin configuration wizard still works (config preferences)
- [x] Permissions scanner still discovers recommended permissions
- [x] All existing tests pass (with updated fixtures)
- [x] `make lint` passes
- [x] `make test` passes

## Work Tracking

- Branch: `fix/13-separate-plugin-config`
- Started: 2026-02-16
- Work directory: `issues/completed/issue-13/`

## Resolution

**Completed**: 2026-02-16

### Changes Made

- Created `.claude-plugin/aida-config.json` with `config` and
  `recommendedPermissions` fields moved from `plugin.json`
- Cleaned `plugin.json` to only standard Claude Code fields
- Added `_safe_read_file()` helper to `plugins.py` with O_NOFOLLOW for
  TOCTOU-safe file reading
- Added `_safe_read_json()` helper to `scanner.py` with same security pattern
- Refactored `discover_installed_plugins()` and `scan_plugins()` to read
  AIDA fields from `aida-config.json` (strict separation, no fallback)
- Added directory-level symlink rejection for `.claude-plugin` directories
- Reordered symlink check before `stat()` in `permissions.py`
- Updated all documentation (5 files) to reflect new file layout
- Added 16 new tests covering all security boundaries (423 total, all passing)

### Implementation Details

- Strict separation: AIDA fields are NEVER read from `plugin.json`, even as
  fallback. Missing `aida-config.json` gracefully defaults to empty `{}`
- Security hardening: O_NOFOLLOW atomic symlink rejection, fstat on fd (not
  path), path containment validation, 1MB size limits, isinstance checks
- Three rounds of code reviews (code reviewer, system architect, tech lead,
  security engineer) -- all approved

### Notes

- Pre-existing security gaps (TOCTOU races, ordering issues) were fixed
  alongside the primary bug fix
- Code duplication between `_safe_read_file` (plugins.py) and
  `_safe_read_json` (scanner.py) is intentional due to different module
  contexts and dependencies

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/13)
- PR #14: Move config and recommendedPermissions to aida-config.json
- PR #11: Plugin config discovery and permissions management
