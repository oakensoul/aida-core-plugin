---
type: reference
title: Validate Workflow
description: Process for validating Claude Code extensions against schema rules
---

# Validate Workflow

This document describes the workflow for validating existing Claude Code
extensions against the frontmatter schema.

## Overview

Validation checks components against:

- Name format (kebab-case, 2-50 chars)
- Description length (10-500 chars)
- Version format (semver X.Y.Z)
- Required fields for each type
- Tag format (kebab-case)

## Validation Rules

### All Components

| Field         | Rule                                       | Example                     |
| ------------- | ------------------------------------------ | --------------------------- |
| `type`        | Required, enum value                       | `agent`, `command`, `skill` |
| `name`        | Required, `^[a-z][a-z0-9-]*$`, 2-50 chars  | `my-agent`                  |
| `description` | Required, 10-500 chars                     | `Agent that handles...`     |
| `version`     | Required, `^\d+\.\d+\.\d+$`                | `0.1.0`                     |
| `tags`        | Required array, each tag kebab-case        | `["core", "api"]`           |

### Command-Specific

| Field           | Rule            | Example       |
| --------------- | --------------- | ------------- |
| `args`          | Optional string | `""`          |
| `allowed-tools` | Optional string | `"*"`         |
| `argument-hint` | Optional string | `"[options]"` |

### Plugin-Specific

| Field         | Rule            | Example                |
| ------------- | --------------- | ---------------------- |
| `name`        | Required string | `"my-plugin"`          |
| `version`     | Required semver | `"0.1.0"`              |
| `description` | Required string | `"Plugin description"` |

## Usage

### Validate Single Component

```bash
python manage.py --execute --context='{"operation": "validate", "type": "agent", "name": "my-agent"}'
```

### Validate All Components of Type

```bash
python manage.py --execute --context='{"operation": "validate", "type": "agent", "all": true}'
```

### Validate Across Locations

```bash
python manage.py --execute --context='{"operation": "validate", "type": "agent", "all": true, "location": "all"}'
```

## Output Format

### Success (All Valid)

```json
{
  "success": true,
  "all_valid": true,
  "results": [
    {
      "name": "my-agent",
      "location": "user",
      "path": "~/.claude/agents/my-agent/my-agent.md",
      "valid": true,
      "errors": []
    }
  ],
  "summary": "Validated 1 agent(s): 1 valid, 0 invalid"
}
```

### Partial Failure

```json
{
  "success": true,
  "all_valid": false,
  "results": [
    {
      "name": "my-agent",
      "location": "user",
      "path": "~/.claude/agents/my-agent/my-agent.md",
      "valid": true,
      "errors": []
    },
    {
      "name": "bad-agent",
      "location": "user",
      "path": "~/.claude/agents/bad-agent/bad-agent.md",
      "valid": false,
      "errors": [
        "Description: Description must be at least 10 characters"
      ]
    }
  ],
  "summary": "Validated 2 agent(s): 1 valid, 1 invalid"
}
```

## Common Validation Errors

| Error                             | Cause                             | Fix                        |
| --------------------------------- | --------------------------------- | -------------------------- |
| Name: must start with lowercase   | Name starts with number/uppercase | Rename to start with `a-z` |
| Name: must be 2-50 characters     | Name too short/long               | Adjust name length         |
| Description: must be 10-500 chars | Description too short/long        | Expand/trim description    |
| Version: must be X.Y.Z            | Invalid version format            | Use semver format          |
| Tags: must be kebab-case          | Tag has invalid characters        | Fix tag format             |

## Integration with CI/CD

Add validation to your CI pipeline:

```yaml
# .github/workflows/validate.yml
- name: Validate AIDA Components
  run: |
    python skills/claude-code-management/scripts/manage.py \
      --execute \
      --context='{"operation": "validate", "type": "agent", "all": true}'
```

## Frontmatter Schema Reference

The full schema is defined in `.frontmatter-schema.json`. Key sections:

```json
{
  "if": { "properties": { "type": { "const": "agent" } } },
  "then": {
    "required": ["name", "description", "version", "tags"],
    "properties": {
      "name": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9-]*$",
        "minLength": 2,
        "maxLength": 50
      }
    }
  }
}
```
