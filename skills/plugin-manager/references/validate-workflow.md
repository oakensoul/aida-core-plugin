---
type: reference
title: Plugin Validation Workflow
description: >-
  Process for validating Claude Code plugins against
  JSON schema rules
---

# Plugin Validation Workflow

This document describes the workflow for validating
existing Claude Code plugins against schema rules.

## Overview

Plugin validation is **JSON-based** (plugin.json), which
differs from agents and skills that use YAML frontmatter.

Validation checks plugins against:

- Name format (kebab-case, 2-50 chars)
- Description length (10-500 chars)
- Version format (semver X.Y.Z)
- Required JSON fields

## Validation Rules

### Required Fields

| Field | Rule | Example |
| --- | --- | --- |
| `name` | Required, `^[a-z][a-z0-9-]*$`, 2-50 chars | `"my-plugin"` |
| `version` | Required, `^\d+\.\d+\.\d+$` | `"0.1.0"` |
| `description` | Required, 10-500 chars | `"Plugin that..."` |

### Optional Fields

| Field | Type | Description |
| --- | --- | --- |
| `created` | string | ISO 8601 timestamp |
| `author` | string | Author name |
| `repository` | string | Repository URL |
| `license` | string | SPDX license identifier |
| `keywords` | array | Marketplace tags |
| `dependencies` | object | Plugin dependencies |

## Usage

### Validate Single Plugin

```bash
python manage.py --execute \
  --context='{"operation": "validate", "name": "my-plugin"}'
```

### Validate All Plugins

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
      "name": "my-plugin",
      "location": "user",
      "path": "/path/to/plugin",
      "valid": true,
      "errors": []
    }
  ],
  "summary": "Validated 1 plugin(s): 1 valid, 0 invalid"
}
```

### Partial Failure

```json
{
  "success": true,
  "all_valid": false,
  "results": [
    {
      "name": "my-plugin",
      "location": "user",
      "path": "/path/to/plugin",
      "valid": true,
      "errors": []
    },
    {
      "name": "bad-plugin",
      "location": "user",
      "path": "/path/to/bad-plugin",
      "valid": false,
      "errors": [
        "Description: Description must be at least 10 characters"
      ]
    }
  ],
  "summary": "Validated 2 plugin(s): 1 valid, 1 invalid"
}
```

## Common Validation Errors

| Error | Cause | Fix |
| --- | --- | --- |
| Name: must start with lowercase | Name starts with number/uppercase | Rename to start with `a-z` |
| Name: must be 2-50 characters | Name too short/long | Adjust name length |
| Description: must be 10-500 chars | Description too short/long | Expand/trim description |
| Version: must be X.Y.Z | Invalid version format | Use semver format |

## Key Differences from Agent/Skill Validation

- Plugins use **JSON** (plugin.json), not YAML frontmatter
- Plugins do not have a `type` field in metadata
- Plugins do not have `tags` in their core schema
- Version bumping modifies JSON directly, not frontmatter
- Discovery looks for `.claude-plugin/plugin.json` paths
