---
type: issue
issue: 13
title: "Move config and recommendedPermissions from plugin.json to aida-config.json"
status: "In Progress"
created: "2026-02-16"
---

# Issue #13: Move config and recommendedPermissions from plugin.json to aida-config.json

**Status**: OPEN
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

- [ ] Remove `config` and `recommendedPermissions` keys from
      `.claude-plugin/plugin.json`
- [ ] Create `.claude-plugin/aida-config.json` containing the moved fields
- [ ] Update `skills/aida-dispatch/scripts/utils/plugins.py`
      `discover_installed_plugins()` to read from `aida-config.json`
- [ ] Update `skills/permissions/scripts/scanner.py` `scan_plugins()` to read
      `recommendedPermissions` from `aida-config.json`
- [ ] Update all unit tests in `tests/unit/test_plugin_discovery.py` and
      `tests/unit/test_permissions.py` to reflect new file location
- [ ] Verify plugin loads successfully after changes

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

- [ ] Plugin loads without validation errors
- [ ] `aida-config.json` is discovered and read by the plugin system
- [ ] Plugin configuration wizard still works (config preferences)
- [ ] Permissions scanner still discovers recommended permissions
- [ ] All existing tests pass (with updated fixtures)
- [ ] `make lint` passes
- [ ] `make test` passes

## Work Tracking

- Branch: `fix/13-separate-plugin-config`
- Started: 2026-02-16
- Work directory: `issues/in-progress/issue-13/`

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/13)
- PR #11: Plugin config discovery and permissions management
