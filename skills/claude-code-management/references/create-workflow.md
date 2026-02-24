---
type: reference
title: Create Workflow
description: Step-by-step process for creating Claude Code extensions
---

# Create Workflow

This document describes the workflow for creating new Claude Code extensions
(agents, skills, plugins).

## Overview

The create workflow uses a two-phase API:

1. **Phase 1 (get-questions)**: Analyze description, infer metadata, identify questions
2. **Phase 2 (execute)**: Create files using Jinja2 templates

## Phase 1: Get Questions

### Input Context

```json
{
  "operation": "create",
  "type": "agent|skill|plugin",
  "description": "User-provided description",
  "location": "user|project|plugin",
  "plugin_path": "/path/to/plugin"
}
```

### Process

1. **Parse description** - Extract key information from user's description
2. **Infer metadata**:
   - `name`: Convert description to kebab-case
   - `version`: Default to "0.1.0"
   - `tags`: Infer from keywords in description
3. **Validate inferred name** against schema rules
4. **Check for conflicts** - Ensure name doesn't already exist
5. **Return questions** for any missing/invalid data

### Output

```json
{
  "questions": [
    {
      "id": "name",
      "question": "What should this agent be named?",
      "type": "text",
      "required": true,
      "help": "Must be kebab-case",
      "default": "inferred-name"
    }
  ],
  "inferred": {
    "name": "inferred-name",
    "description": "User description",
    "version": "0.1.0",
    "tags": ["custom", "api"]
  }
}
```

## Phase 2: Execute

### Input

```json
{
  "operation": "create",
  "type": "agent",
  "name": "my-agent",
  "description": "Agent description",
  "version": "0.1.0",
  "tags": ["custom"],
  "location": "user"
}
```

### Process by Component Type

#### Agent

1. Create directory: `{location}/agents/{name}/`
2. Create `{name}.md` from `agent/agent.md.jinja2`
3. Create `knowledge/` subdirectory
4. Return success with file paths

#### Skill

1. Create directory: `{location}/skills/{name}/`
2. Create `SKILL.md` from `skill/SKILL.md.jinja2`
3. Create `references/` and `scripts/` subdirectories
4. Return success with file paths

#### Plugin

1. Create directory: `{path}/{name}/`
2. Create `.claude-plugin/plugin.json` from template
3. Create `README.md` from template
4. Create `.gitignore` from template
5. Create empty directories: `agents/`, `skills/`
6. Return success with file paths

### Output

```json
{
  "success": true,
  "message": "Created agent 'my-agent' at ~/.claude/agents/my-agent/my-agent.md",
  "files_created": [
    "~/.claude/agents/my-agent/my-agent.md"
  ],
  "path": "~/.claude/agents/my-agent/my-agent.md"
}
```

## Script Invocation

```bash
# Phase 1: Get questions
python manage.py --get-questions --context='{"operation": "create", "type": "agent", "description": "Handles database migrations"}'

# Phase 2: Execute (with any user responses merged)
python manage.py --execute --context='{"operation": "create", "type": "agent", "name": "database-migration", "description": "Handles database migrations", "version": "0.1.0", "tags": ["database"], "location": "user"}'
```

## Error Handling

| Error            | Cause                       | Resolution                  |
| ---------------- | --------------------------- | --------------------------- |
| Invalid name     | Name doesn't match pattern  | Ask user for valid name     |
| Name exists      | Component already exists    | Ask user for different name |
| Template error   | Jinja2 rendering failed     | Check template syntax       |
| Permission error | Can't write to location     | Check directory permissions |

## Best Practices

1. **Let inference work** - Only ask questions when necessary
2. **Validate early** - Check name/description before Phase 2
3. **Use dry-run** - Preview changes before creating
4. **Follow naming conventions** - kebab-case, descriptive names
