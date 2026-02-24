---
type: reference
title: Skill Frontmatter Schema
description: Reference for YAML frontmatter fields in Claude Code skill definitions
---

# Skill Frontmatter Schema

This document provides a complete reference for YAML frontmatter
fields used in Claude Code skill definitions.

## Required Fields

These fields are required in every skill's `SKILL.md` frontmatter:

| Field         | Type   | Required | Pattern                | Description               |
| ------------- | ------ | -------- | ---------------------- | ------------------------- |
| `type`        | string | Yes      | Must be `skill`        | Component type identifier |
| `name`        | string | Yes      | `^[a-z][a-z0-9-]*$`    | Unique identifier (2-50)  |
| `description` | string | Yes      | 10-500 chars           | Purpose description       |
| `version`     | string | Yes      | `^\d+\.\d+\.\d+$`      | Semantic version          |
| `tags`        | array  | Yes      | Each tag kebab-case    | Classification tags       |

## Skill-Specific Optional Fields

| Field                      | Type    | Required | Description                           |
| -------------------------- | ------- | -------- | ------------------------------------- |
| `title`                    | string  | No       | Human-readable display title          |
| `context`                  | string  | No       | Additional context for the skill      |
| `agent`                    | string  | No       | Associated agent name                 |
| `hooks`                    | array   | No       | Lifecycle hooks the skill uses        |
| `model`                    | string  | No       | Preferred Claude model                |
| `user-invocable`           | boolean | No       | Allow `/skill-name` invocation        |
| `argument-hint`            | string  | No       | Hint shown to user at invocation      |
| `allowed-tools`            | string  | No       | Restrict tool access (e.g., `"*"`)    |
| `disable-model-invocation` | boolean | No       | Prevent model from invoking the skill |

## Example Frontmatter

### Minimal Skill

```yaml
---
type: skill
name: my-skill
description: Skill that provides specific capabilities and workflows
version: 0.1.0
tags:
  - custom
---
```

### Full Skill

```yaml
---
type: skill
name: deployment-manager
title: Deployment Manager
description: Manages deployment workflows with rollback support and health checks
version: 1.2.0
tags:
  - core
  - deployment
  - automation
context: Operates within CI/CD pipeline context
agent: devops-expert
hooks:
  - PreToolUse
  - PostToolUse
model: claude-sonnet-4
user-invocable: true
argument-hint: "[deploy|rollback|status] [target]"
allowed-tools: "Bash,Read,Write"
---
```

## Skill Directory Structure

```text
skills/
  my-skill/
    SKILL.md        # Skill definition (frontmatter + instructions)
    references/     # Workflow documentation
      workflow.md
    scripts/        # Executable scripts
      manage.py
      _paths.py
      operations/
        __init__.py
        extensions.py
        utils.py
    templates/      # Optional Jinja2 templates
      template.jinja2
```

## Tag Conventions

Common tags used for skills:

| Tag             | Description              |
| --------------- | ------------------------ |
| `core`          | Core AIDA functionality  |
| `utility`       | General utility          |
| `automation`    | Automation workflows     |
| `api`           | API-related              |
| `database`      | Database operations      |
| `testing`       | Testing related          |
| `documentation` | Documentation generation |
| `deployment`    | Deployment and CI/CD     |
| `management`    | Management operations    |
| `custom`        | User-created             |

## Version Management

Follow semantic versioning:

- **Major (X.0.0)**: Breaking changes to skill interface
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### Bumping Versions

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-skill", "bump": "patch"}'

# Bump minor version (0.1.0 -> 0.2.0)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-skill", "bump": "minor"}'

# Bump major version (0.1.0 -> 1.0.0)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-skill", "bump": "major"}'
```

## Validation

Validate skills against this schema:

```bash
# Validate specific skill
python manage.py --execute \
  --context='{"operation": "validate", "name": "my-skill"}'

# Validate all skills
python manage.py --execute \
  --context='{"operation": "validate", "all": true, "location": "all"}'
```

## Agent Skills Open Standard

Skill definitions follow conventions from the
[Agent Skills open standard](https://agentskills.io). The standard
defines how skills are discovered, invoked, and composed within
agent frameworks.
