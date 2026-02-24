---
type: reference
title: Skill Create Workflow
description: Step-by-step process for creating Claude Code skill definitions
---

# Skill Create Workflow

This document describes the workflow for creating new Claude Code
skill definitions using the two-phase API.

## Overview

The create workflow uses a two-phase API:

1. **Phase 1 (get-questions)**: Analyze description, infer
   metadata, identify questions
2. **Phase 2 (execute)**: Create files using Jinja2 templates
   or agent output

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

Note: The component type is always "skill" and does not need
to be specified.

### Process

1. **Parse description** - Extract key information
2. **Infer metadata**:
   - `name`: Convert description to kebab-case
   - `version`: Default to "0.1.0"
   - `tags`: Infer from keywords in description
3. **Validate inferred name** against schema rules
4. **Check for conflicts** - Ensure name does not already exist
5. **Return questions** for any missing or invalid data

### Output

```json
{
  "questions": [
    {
      "id": "name",
      "question": "What should this skill be named?",
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
    "tags": ["custom", "api"],
    "base_path": "~/.claude"
  },
  "project_context": {
    "languages": ["python"],
    "frameworks": ["fastapi"]
  }
}
```

## Phase 2: Execute (Template-Based)

### Input

```json
{
  "operation": "create",
  "name": "my-skill",
  "description": "Skill description",
  "version": "0.1.0",
  "tags": ["custom"],
  "location": "user"
}
```

### Process

1. Create directory: `{location}/skills/{name}/`
2. Create `SKILL.md` from `skill/SKILL.md.jinja2`
3. Create `references/` subdirectory
4. Create `scripts/` subdirectory
5. Return success with file paths

### Output

```json
{
  "success": true,
  "message": "Created skill 'my-skill' at ~/.claude/skills/my-skill/SKILL.md",
  "files_created": [
    "~/.claude/skills/my-skill/SKILL.md"
  ],
  "path": "~/.claude/skills/my-skill/SKILL.md"
}
```

## Phase 3: Execute (Agent-Based)

For agent-based creation, the agent generates full file content
and the script validates and writes them.

### Input

```json
{
  "operation": "create",
  "agent_output": {
    "validation": { "passed": true, "issues": [] },
    "files": [
      { "path": "skills/my-skill/SKILL.md", "content": "..." },
      { "path": "skills/my-skill/scripts/run.py", "content": "..." },
      { "path": "skills/my-skill/references/guide.md", "content": "..." }
    ],
    "summary": {
      "created": ["SKILL.md", "scripts/run.py", "references/guide.md"],
      "next_steps": ["Review SKILL.md and customize"]
    }
  },
  "base_path": "~/.claude"
}
```

### Process

1. Validate agent output structure (required keys)
2. Validate each file entry (path, content)
3. Validate SKILL.md frontmatter (type, name, version)
4. Create directories and write files
5. Return success with created file list

## Script Invocation

```bash
# Phase 1: Get questions
python manage.py --get-questions \
  --context='{"operation": "create", "description": "Handles deployments"}'

# Phase 2: Execute (template-based)
python manage.py --execute \
  --context='{"operation": "create", "name": "deployment-handler", "description": "Handles deployments", "version": "0.1.0", "tags": ["deployment"], "location": "user"}'

# Phase 3: Execute (agent-based)
python manage.py --execute \
  --context='{"operation": "create", "agent_output": {...}, "base_path": "~/.claude"}'
```

## Error Handling

| Error            | Cause                      | Resolution                  |
| ---------------- | -------------------------- | --------------------------- |
| Invalid name     | Name doesn't match pattern | Ask user for valid name     |
| Name exists      | Skill already exists       | Ask user for different name |
| Template error   | Jinja2 rendering failed    | Check template syntax       |
| Permission error | Cannot write to location   | Check directory permissions |

## Best Practices

1. **Let inference work** - Only ask questions when necessary
2. **Validate early** - Check name and description before Phase 2
3. **Follow naming conventions** - kebab-case, descriptive names
4. **Include references/** - Add workflow documentation
5. **Include scripts/** - Add executable automation
