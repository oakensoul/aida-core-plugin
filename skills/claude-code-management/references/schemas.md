---
type: reference
title: Frontmatter Schemas
description: Reference for YAML frontmatter fields in Claude Code extensions
---

# Frontmatter Schemas

This document provides a complete reference for YAML frontmatter fields
used in Claude Code extensions.

## Common Fields

These fields are required for all component types:

| Field         | Type   | Required | Pattern               | Description                                  |
| ------------- | ------ | -------- | --------------------- | -------------------------------------------- |
| `type`        | string | Yes      | enum                  | Component type: `agent`, `skill`             |
| `name`        | string | Yes      | `^[a-z][a-z0-9-]*$`   | Unique identifier (2-50 chars)               |
| `description` | string | Yes      | -                     | Purpose description (10-500 chars)           |
| `version`     | string | Yes      | `^\d+\.\d+\.\d+$`     | Semantic version                             |
| `tags`        | array  | Yes      | -                     | Classification tags                          |

## Agent Schema

```yaml
---
type: agent
name: my-agent
description: Agent that handles specific tasks with expertise
version: 0.1.0
tags:
  - core
  - domain-specific
model: claude-sonnet-4.5    # Optional: preferred model
color: purple               # Optional: UI color
skills:                     # Optional: skills this agent uses
  - skill-name
---
```

### Agent-Specific Fields

| Field    | Type   | Required | Description               |
| -------- | ------ | -------- | ------------------------- |
| `model`  | string | No       | Preferred Claude model    |
| `color`  | string | No       | UI display color          |
| `skills` | array  | No       | Skills this agent uses    |

### Agent Directory Structure

```text
agents/
└── my-agent/
    ├── my-agent.md      # Agent definition
    └── knowledge/       # Agent-specific knowledge
        ├── index.md     # Knowledge catalog
        └── domain.md    # Domain-specific docs
```

## Skill Schema

```yaml
---
type: skill
name: my-skill
description: Skill that provides specific capabilities and workflows
version: 0.1.0
tags:
  - core
  - automation
---
```

### Skill Directory Structure

```text
skills/
└── my-skill/
    ├── SKILL.md        # Skill definition
    ├── references/     # Workflow documentation
    │   └── workflow.md
    ├── scripts/        # Executable scripts
    │   └── action.py
    └── templates/      # Optional: Jinja2 templates
```

## Plugin Schema (plugin.json)

The `plugin.json` file contains only standard Claude Code fields:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Plugin that extends Claude Code functionality",
  "created": "2025-01-01T00:00:00Z",
  "author": "Author Name",
  "repository": "https://github.com/...",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "dependencies": {}
}
```

## AIDA Config Schema (aida-config.json)

AIDA-specific fields (`config` and `recommendedPermissions`) live in
a separate `aida-config.json` file inside `.claude-plugin/`. This
avoids conflicts with the Claude Code plugin validator which rejects
unrecognized keys in `plugin.json`.

```json
{
  "config": { },
  "recommendedPermissions": { }
}
```

### Plugin Config Section

Plugins can declare user-configurable preferences via the `config`
section in `aida-config.json`:

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
| ----- | ---- | -------- | ----------- |
| `config.label` | string | Yes | Display name for config section |
| `config.description` | string | Yes | Help text for the config section |
| `config.preferences` | array | Yes | List of preference definitions |

#### Preference Types

| Type | Fields | Description |
| ---- | ------ | ----------- |
| `boolean` | `key`, `label`, `default` | On/off toggle |
| `choice` | `key`, `label`, `options`, `default` | Select from list |
| `string` | `key`, `label`, `default` | Free-text input |

#### Preference Fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `key` | string | Yes | Dot-notation identifier (e.g., `feature.enabled`) |
| `type` | string | Yes | One of: `boolean`, `choice`, `string` |
| `label` | string | Yes | Human-readable label |
| `options` | array | For `choice` | Available options |
| `default` | any | No | Default value |

### Plugin Recommended Permissions Section

Plugins can declare Claude Code permission recommendations via the
`recommendedPermissions` section in `aida-config.json`. Each category
groups related permission rules:

```json
{
  "recommendedPermissions": {
    "git-operations": {
      "label": "Git Operations",
      "description": "Commit, push, branch, and other git commands",
      "rules": [
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(git push:*)"
      ],
      "suggested": "allow"
    },
    "file-operations": {
      "label": "File Operations",
      "description": "Read and write project files",
      "rules": [
        "Bash(cat:*)",
        "Bash(mkdir:*)"
      ],
      "suggested": "ask"
    }
  }
}
```

#### Permission Category Fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `label` | string | Yes | Display name for the category |
| `description` | string | Yes | What these permissions cover |
| `rules` | array | Yes | Permission rule strings |
| `suggested` | string | Yes | Default action: `allow`, `ask`, or `deny` |

#### Rule Format Reference

Rules follow the pattern `Tool(command:args)`:

| Pattern | Example | Description |
| ------- | ------- | ----------- |
| `Bash(cmd:*)` | `Bash(git add:*)` | Allow cmd with any args |
| `Bash(cmd:specific)` | `Bash(git push:origin)` | Allow specific args |
| `Bash(cmd:prefix*)` | `Bash(npm:run *)` | Allow args with prefix |

### Plugin Directory Structure

```text
my-plugin/
├── .claude-plugin/
│   ├── plugin.json       # Standard Claude Code metadata
│   └── aida-config.json  # AIDA config + permissions
├── agents/               # Plugin agents
├── commands/             # Plugin commands
├── skills/               # Plugin skills
├── templates/            # Optional: shared templates
├── README.md             # Plugin documentation
└── .gitignore            # Git ignores
```

## Tag Conventions

Common tags used across components:

| Tag             | Description                |
| --------------- | -------------------------- |
| `core`          | Core AIDA functionality    |
| `utility`       | General utility            |
| `automation`    | Automation workflows       |
| `api`           | API-related                |
| `database`      | Database operations        |
| `testing`       | Testing related            |
| `documentation` | Documentation generation   |
| `deployment`    | Deployment/CI-CD           |
| `custom`        | User-created               |

## Version Management

Follow semantic versioning:

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### Bumping Versions

```bash
# Bump patch version (0.1.0 -> 0.1.1)
/aida agent version my-agent patch

# Bump minor version (0.1.0 -> 0.2.0)
/aida agent version my-agent minor

# Bump major version (0.1.0 -> 1.0.0)
/aida agent version my-agent major
```

## Validation

Validate components against schema:

```bash
# Validate specific component
/aida agent validate my-agent

# Validate all components of a type
/aida agent validate --all

# Validate across all locations
/aida agent validate --all --location all
```

## JSON Schema Location

The full JSON schema is at:

```text
.frontmatter-schema.json
```

This schema is used by:

- `scripts/validate_frontmatter.py` for linting
- `manage.py` for creation validation
- IDE extensions for autocomplete
