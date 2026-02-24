---
type: reference
title: Skill Validate Workflow
description: Process for validating Claude Code skill definitions against schema rules
---

# Skill Validate Workflow

This document describes the workflow for validating existing
Claude Code skill definitions against the frontmatter schema.

## Overview

Validation checks skills against:

- Name format (kebab-case, 2-50 characters)
- Description length (10-500 characters)
- Version format (semver X.Y.Z)
- Required fields (type, name, description, version)
- Frontmatter type must be "skill"

## Validation Rules

### Required Fields

| Field         | Rule                                       | Example                  |
| ------------- | ------------------------------------------ | ------------------------ |
| `type`        | Required, must be `skill`                  | `skill`                  |
| `name`        | Required, `^[a-z][a-z0-9-]*$`, 2-50 chars  | `my-skill`               |
| `description` | Required, 10-500 chars                     | `Skill that handles...`  |
| `version`     | Required, `^\d+\.\d+\.\d+$`                | `0.1.0`                  |
| `tags`        | Required array, each tag kebab-case        | `["core", "automation"]` |

### Skill-Specific Optional Fields

| Field                      | Type    | Description                           |
| -------------------------- | ------- | ------------------------------------- |
| `user-invocable`           | boolean | Allow `/skill-name` invocation        |
| `argument-hint`            | string  | Hint shown to user at invocation      |
| `allowed-tools`            | string  | Restrict tool access (e.g., `"*"`)    |
| `disable-model-invocation` | boolean | Prevent model from invoking the skill |

## Usage

### Validate Single Skill

```bash
python manage.py --execute \
  --context='{"operation": "validate", "name": "my-skill"}'
```

### Validate All Skills

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
      "name": "my-skill",
      "location": "user",
      "path": "~/.claude/skills/my-skill/SKILL.md",
      "valid": true,
      "errors": []
    }
  ],
  "summary": "Validated 1 skill(s): 1 valid, 0 invalid"
}
```

### Partial Failure

```json
{
  "success": true,
  "all_valid": false,
  "results": [
    {
      "name": "my-skill",
      "location": "user",
      "path": "~/.claude/skills/my-skill/SKILL.md",
      "valid": true,
      "errors": []
    },
    {
      "name": "bad-skill",
      "location": "user",
      "path": "~/.claude/skills/bad-skill/SKILL.md",
      "valid": false,
      "errors": [
        "Description: Description must be at least 10 characters"
      ]
    }
  ],
  "summary": "Validated 2 skill(s): 1 valid, 1 invalid"
}
```

## Common Validation Errors

| Error                             | Cause                             | Fix                        |
| --------------------------------- | --------------------------------- | -------------------------- |
| Name: must start with lowercase   | Name starts with number/uppercase | Rename to start with `a-z` |
| Name: must be 2-50 characters     | Name too short or too long        | Adjust name length         |
| Description: must be 10-500 chars | Description too short or too long | Expand or trim description |
| Version: must be X.Y.Z            | Invalid version format            | Use semver format          |
| Type: doesn't match 'skill'       | Wrong type in frontmatter         | Set type to `skill`        |

## Skill File Pattern

Skills are discovered by searching for `SKILL.md` files:

```text
skills/{name}/SKILL.md
```

The validator reads the YAML frontmatter from each `SKILL.md`
file and checks that the `type` field equals `skill` before
applying validation rules.
