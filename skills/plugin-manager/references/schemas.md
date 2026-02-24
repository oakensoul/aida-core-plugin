---
type: reference
title: Plugin Schemas
description: >-
  Reference for JSON schema fields in Claude Code plugin
  metadata files
---

# Plugin Schemas

This document provides a complete reference for the JSON
schema fields used in Claude Code plugin metadata files.

## plugin.json

The `plugin.json` file contains standard Claude Code
plugin metadata. It lives at `.claude-plugin/plugin.json`
inside the plugin project root.

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Plugin that extends Claude Code",
  "created": "2025-01-01T00:00:00Z",
  "author": "Author Name",
  "repository": "https://github.com/...",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "dependencies": {}
}
```

### Required Fields

| Field | Type | Validation | Example |
| --- | --- | --- | --- |
| `name` | string | `^[a-z][a-z0-9-]*$`, 2-50 chars | `"my-plugin"` |
| `version` | string | `^\d+\.\d+\.\d+$` | `"0.1.0"` |
| `description` | string | 10-500 chars | `"Plugin that..."` |

### Optional Fields

| Field | Type | Description |
| --- | --- | --- |
| `created` | string | ISO 8601 UTC timestamp |
| `author` | string | Author name or organization |
| `repository` | string | Source repository URL |
| `license` | string | SPDX license identifier |
| `keywords` | array | Marketplace discovery tags |
| `dependencies` | object | Plugin dependency map |

## aida-config.json

AIDA-specific fields live in a separate
`aida-config.json` file inside `.claude-plugin/`. This
avoids conflicts with the Claude Code plugin validator
which rejects unrecognized keys in `plugin.json`.

```json
{
  "generator_version": "0.9.0",
  "config": { },
  "recommendedPermissions": { }
}
```

### Generator Version

The `generator_version` field records which version of the
AIDA scaffolder created or last updated the plugin. This
field is used by the `update` operation to determine what
changes need to be applied.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `generator_version` | string | No | Semver of the scaffolder that created/updated this plugin |

Plugins created before this field was introduced (or
created manually) will not have it. The update operation
treats missing `generator_version` as `"0.0.0"`
(pre-tracking).

### Config Section

Plugins can declare user-configurable preferences:

```json
{
  "config": {
    "label": "My Plugin Configuration",
    "description": "Configure plugin preferences",
    "preferences": [
      {
        "key": "feature.enabled",
        "type": "boolean",
        "label": "Enable feature X",
        "default": true
      },
      {
        "key": "output.format",
        "type": "choice",
        "label": "Output format",
        "options": ["JSON", "YAML", "Text"],
        "default": "JSON"
      },
      {
        "key": "custom.path",
        "type": "string",
        "label": "Custom output path",
        "default": "./output"
      }
    ]
  }
}
```

#### Config Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `config.label` | string | Yes | Display name |
| `config.description` | string | Yes | Help text |
| `config.preferences` | array | Yes | Preference list |

#### Preference Types

| Type | Fields | Description |
| --- | --- | --- |
| `boolean` | `key`, `label`, `default`, `required?` | On/off toggle |
| `choice` | `key`, `label`, `options`, `default`, `required?` | Select from list |
| `string` | `key`, `label`, `default`, `required?` | Free-text input |

All preference types accept an optional `required` boolean
field (defaults to `false`) indicating whether the preference
must be configured before the plugin is usable.

### Recommended Permissions Section

Plugins can declare Claude Code permission recommendations:

```json
{
  "recommendedPermissions": {
    "git-operations": {
      "label": "Git Operations",
      "description": "Commit, push, branch, etc.",
      "rules": [
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(git push:*)"
      ],
      "suggested": "allow"
    }
  }
}
```

#### Permission Category Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `label` | string | Yes | Display name |
| `description` | string | Yes | What permissions cover |
| `rules` | array | Yes | Permission rule strings |
| `suggested` | string | Yes | `allow`, `ask`, or `deny` |

#### Rule Format

Rules follow the pattern `Tool(command:args)`:

| Pattern | Example | Description |
| --- | --- | --- |
| `Bash(cmd:*)` | `Bash(git add:*)` | Allow cmd with any args |
| `Bash(cmd:specific)` | `Bash(git push:origin)` | Specific args only |
| `Bash(cmd:prefix*)` | `Bash(npm:run *)` | Args with prefix |

## marketplace.json

The marketplace listing file provides discovery metadata:

```json
{
  "display_name": "My Plugin",
  "icon": "",
  "category": "tools",
  "tags": ["productivity", "automation"],
  "screenshots": [],
  "pricing": "free"
}
```

## Plugin Directory Structure

```text
my-plugin/
├── .claude-plugin/
│   ├── plugin.json         # Standard Claude Code metadata
│   ├── marketplace.json    # Marketplace listing
│   └── aida-config.json    # AIDA config + permissions
├── agents/                 # Plugin agents
├── skills/                 # Plugin skills
├── templates/              # Optional: shared templates
├── README.md               # Plugin documentation
├── CLAUDE.md               # Claude Code instructions
└── .gitignore              # Git ignores
```

## Version Management

Follow semantic versioning:

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### Bumping Versions

```bash
# Bump patch version (0.1.0 -> 0.1.1)
/aida plugin version my-plugin patch

# Bump minor version (0.1.0 -> 0.2.0)
/aida plugin version my-plugin minor

# Bump major version (0.1.0 -> 1.0.0)
/aida plugin version my-plugin major
```
