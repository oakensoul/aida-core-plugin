---
type: reference
title: Agent Create Workflow
description: >-
  Step-by-step process for creating Claude Code agent
  (subagent) definitions
---

# Agent Create Workflow

This document describes the workflow for creating new
Claude Code agent (subagent) definitions.

## Overview

The create workflow uses a two-phase API:

1. **Phase 1 (get-questions)**: Analyze description,
   infer metadata, identify questions
2. **Phase 2 (execute)**: Create files using Jinja2
   templates or agent output

## Phase 1: Get Questions

### Input Context

```json
{
  "operation": "create",
  "description": "User-provided description",
  "location": "user|project|plugin",
  "plugin_path": "/path/to/plugin"
}
```

Note: `type` is always `agent` and is set automatically
by the manager.

### Process

1. **Parse description** -- Extract key information
2. **Infer metadata**:
   - `name`: Convert description to kebab-case
   - `version`: Default to "0.1.0"
   - `tags`: Infer from keywords in description
3. **Validate inferred name** against schema rules
4. **Check for conflicts** -- Ensure name is unique
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
  "name": "my-agent",
  "description": "Agent description",
  "version": "0.1.0",
  "tags": ["custom"],
  "location": "user"
}
```

### Process

1. Create directory: `{location}/agents/{name}/`
2. Create `{name}.md` from `agent/agent.md.jinja2`
3. Create `knowledge/` subdirectory
4. Return success with file paths

### Output

```json
{
  "success": true,
  "message": "Created agent 'my-agent' at ...",
  "files_created": [
    "~/.claude/agents/my-agent/my-agent.md"
  ],
  "path": "~/.claude/agents/my-agent/my-agent.md"
}
```

## Script Invocation

```bash
# Phase 1: Get questions
python manage.py --get-questions \
  --context='{"operation": "create", "description": "Handles database migrations"}'

# Phase 2: Execute (with user responses merged)
python manage.py --execute \
  --context='{"operation": "create", "name": "database-migration", "description": "Handles database migrations", "version": "0.1.0", "tags": ["database"], "location": "user"}'
```

## Agent-Based Creation (Phase 3)

When the `claude-code-expert` agent generates content,
pass the output to Phase 3:

```bash
python manage.py --execute \
  --context='{"operation": "create", "agent_output": {...}}'
```

The script:

1. Validates agent output structure
2. Validates frontmatter in main `.md` file
3. Creates directories and writes files
4. Returns success with created file paths

## Error Handling

| Error            | Cause                      | Resolution              |
| ---------------- | -------------------------- | ----------------------- |
| Invalid name     | Name doesn't match pattern | Ask user for valid name |
| Name exists      | Agent already exists       | Ask for different name  |
| Template error   | Jinja2 rendering failed    | Check template syntax   |
| Permission error | Can't write to location    | Check permissions       |

## Best Practices

1. **Let inference work** -- Only ask when necessary
2. **Validate early** -- Check name/description first
3. **Follow naming** -- kebab-case, descriptive names
4. **Knowledge dir** -- Always created for agents
