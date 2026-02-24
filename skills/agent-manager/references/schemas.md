---
type: reference
title: Agent Frontmatter Schema
description: >-
  Reference for YAML frontmatter fields in Claude Code
  agent definitions
---

# Agent Frontmatter Schema

This document provides a complete reference for YAML
frontmatter fields used in Claude Code agent (subagent)
definitions.

## Required Fields

| Field         | Type   | Pattern                | Description            |
| ------------- | ------ | ---------------------- | ---------------------- |
| `type`        | string | `agent`                | Must be "agent"        |
| `name`        | string | `^[a-z][a-z0-9-]*$`    | Unique ID (2-50 chars) |
| `description` | string | -                      | Purpose (10-500 chars) |
| `version`     | string | `^\d+\.\d+\.\d+$`      | Semantic version       |
| `tags`        | array  | -                      | Classification tags    |

## Optional Fields

| Field    | Type   | Description               |
| -------- | ------ | ------------------------- |
| `model`  | string | Preferred Claude model    |
| `color`  | string | UI display color          |
| `skills` | array  | Skills this agent uses    |

## Example Frontmatter

```yaml
---
type: agent
name: my-agent
description: >-
  Agent that handles specific tasks with domain
  expertise
version: 0.1.0
tags:
  - core
  - domain-specific
model: claude-sonnet-4.5
color: purple
skills:
  - skill-name
---
```

## Agent Directory Structure

```text
agents/
  my-agent/
    my-agent.md        # Agent definition
    knowledge/         # Agent-specific knowledge
      index.md         # Knowledge catalog
      domain.md        # Domain-specific docs
```

## Tag Conventions

Common tags used across agents:

| Tag             | Description              |
| --------------- | ------------------------ |
| `core`          | Core AIDA functionality  |
| `utility`       | General utility          |
| `automation`    | Automation workflows     |
| `api`           | API-related              |
| `database`      | Database operations      |
| `testing`       | Testing related          |
| `documentation` | Documentation generation |
| `deployment`    | Deployment/CI-CD         |
| `custom`        | User-created             |

## Version Management

Follow semantic versioning:

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, backwards compatible

### Bumping Versions

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-agent", "bump": "patch"}'

# Bump minor version (0.1.0 -> 0.2.0)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-agent", "bump": "minor"}'

# Bump major version (0.1.0 -> 1.0.0)
python manage.py --execute \
  --context='{"operation": "version", "name": "my-agent", "bump": "major"}'
```

## Validation

Validate agents against schema:

```bash
# Validate specific agent
python manage.py --execute \
  --context='{"operation": "validate", "name": "my-agent"}'

# Validate all agents
python manage.py --execute \
  --context='{"operation": "validate", "all": true}'

# Validate across all locations
python manage.py --execute \
  --context='{"operation": "validate", "all": true, "location": "all"}'
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
