---
type: reference
title: Agent Validate Workflow
description: >-
  Process for validating Claude Code agent definitions
  against schema rules
---

# Agent Validate Workflow

This document describes the workflow for validating
existing Claude Code agent definitions against the
frontmatter schema.

## Overview

Validation checks agents against:

- Name format (kebab-case, 2-50 chars)
- Description length (10-500 chars)
- Version format (semver X.Y.Z)
- Required frontmatter fields

## Validation Rules

| Field         | Rule                                        | Example                 |
| ------------- | ------------------------------------------- | ----------------------- |
| `type`        | Required, must be `agent`                   | `agent`                 |
| `name`        | Required, `^[a-z][a-z0-9-]*$`, 2-50 chars   | `my-agent`              |
| `description` | Required, 10-500 chars                      | `Agent that handles...` |
| `version`     | Required, `^\d+\.\d+\.\d+$`                 | `0.1.0`                 |
| `tags`        | Required array, each tag kebab-case         | `["core", "api"]`       |

### Agent-Specific Fields (Optional)

| Field    | Type   | Description            |
| -------- | ------ | ---------------------- |
| `model`  | string | Preferred Claude model |
| `color`  | string | UI display color       |
| `skills` | array  | Skills this agent uses |

## Usage

### Validate Single Agent

```bash
python manage.py --execute \
  --context='{"operation": "validate", "name": "my-agent"}'
```

### Validate All Agents

```bash
python manage.py --execute \
  --context='{"operation": "validate", "all": true}'
```

### Validate Across Locations

```bash
python manage.py --execute \
  --context='{"operation": "validate", "all": true, "location": "all"}'
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
        "Description: must be at least 10 characters"
      ]
    }
  ],
  "summary": "Validated 2 agent(s): 1 valid, 1 invalid"
}
```

## Common Validation Errors

| Error                             | Cause                   | Fix                        |
| --------------------------------- | ----------------------- | -------------------------- |
| Name: must start with lowercase   | Name starts with number | Rename to start with `a-z` |
| Name: must be 2-50 characters     | Name too short/long     | Adjust name length         |
| Description: must be 10-500 chars | Description too short   | Expand/trim description    |
| Version: must be X.Y.Z            | Invalid version format  | Use semver format          |

## Integration with CI/CD

Add validation to your CI pipeline:

```yaml
# .github/workflows/validate.yml
- name: Validate Agents
  run: |
    python skills/agent-manager/scripts/manage.py \
      --execute \
      --context='{"operation": "validate", "all": true}'
```

## Frontmatter Schema Reference

The full schema is defined in `.frontmatter-schema.json`:

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
