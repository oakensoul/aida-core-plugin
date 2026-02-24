---
type: reference
name: claude-md-workflow
title: Claude MD Workflow
description: >-
  Step-by-step process for creating, optimizing, and
  validating CLAUDE.md files
version: 0.1.0
---

# Claude MD Workflow

This document describes the workflow for managing
CLAUDE.md files via the claude-md-manager skill.

## Overview

CLAUDE.md files provide project-specific guidance to
Claude Code. They exist at multiple levels in a hierarchy:
project, user, and plugin.

## Create Workflow

### Phase 1: Get Questions

**Input Context:**

```json
{
  "operation": "create",
  "scope": "project|user|plugin"
}
```

**Process:**

1. **Determine scope** - Project, user, or plugin level
2. **Detect project context** using inference utilities:
   - Languages (Python, JavaScript, etc.)
   - Tools (Git, Docker, pytest, etc.)
   - Build tool and commands
   - Project type and structure
3. **Extract additional context**:
   - Parse README.md for project description
   - Extract commands from Makefile/package.json
4. **Check for existing CLAUDE.md** at target location
5. **Return questions** for missing required fields

**Output:**

```json
{
  "questions": [],
  "inferred": {
    "name": "my-project",
    "description": "Project description from README",
    "languages": ["Python", "JavaScript"],
    "tools": ["Git", "Docker", "pytest"],
    "commands": [
      {
        "command": "make dev",
        "description": "Start development server"
      },
      {
        "command": "make test",
        "description": "Run tests"
      }
    ],
    "project_type": "Web application (backend)"
  },
  "existing": null
}
```

### Phase 2: Execute Create

**Input:**

```json
{
  "operation": "create",
  "scope": "project",
  "name": "my-project",
  "description": "Project description",
  "languages": ["Python"],
  "tools": ["Git", "pytest"],
  "commands": [],
  "sections": ["overview", "commands", "architecture"]
}
```

**Process:**

1. Ensure target directory exists
2. Check for conflicts (existing file)
3. Select appropriate template based on scope
4. Render template with provided data
5. Write to target location
6. Return success with path

**Output:**

```json
{
  "success": true,
  "message": "Created CLAUDE.md for project 'my-project'",
  "path": "./CLAUDE.md"
}
```

## Optimize Workflow

### Phase 1: Audit Analysis

**Input Context:**

```json
{
  "operation": "optimize",
  "scope": "project|user|all"
}
```

**Process:**

1. **Find existing CLAUDE.md** at specified scope(s)
2. **Parse content** and frontmatter
3. **Run validation checks**:
   - Structure: Required sections present
   - Consistency: Commands work, paths exist
   - Best practices: Length, clarity, formatting
   - Alignment: Matches detected project facts
4. **Generate findings** categorized by priority
5. **Calculate score** (0-100)

**Output:**

```json
{
  "questions": [
    {
      "id": "fix_mode",
      "question": "How would you like to fix issues?",
      "type": "choice",
      "options": [
        "Fix all",
        "Fix critical only",
        "Interactive"
      ]
    }
  ],
  "audit": {
    "score": 65,
    "findings": [
      {
        "id": "missing-commands",
        "category": "critical",
        "title": "Missing Key Commands section",
        "impact": "Users won't know how to work",
        "fix": {
          "type": "add_section",
          "content": "## Key Commands\n\n```bash\n...\n```"
        }
      }
    ]
  },
  "existing": {
    "path": "./CLAUDE.md",
    "content": "...",
    "sections": ["overview"]
  }
}
```

### Phase 2: Apply Fixes

**Input:**

```json
{
  "operation": "optimize",
  "scope": "project",
  "fixes": ["missing-commands", "outdated-path"]
}
```

**Process:**

1. Load current CLAUDE.md
2. Apply each selected fix:
   - Add missing sections
   - Update outdated content
   - Fix paths and references
3. Preserve user customizations
4. Write updated file
5. Return summary of changes

**Output:**

```json
{
  "success": true,
  "message": "Applied 2 fixes to CLAUDE.md",
  "changes": [
    "Added Key Commands section",
    "Fixed path reference (src/api/ -> api/)"
  ],
  "new_score": 85
}
```

## Validate Workflow

**Input:**

```json
{
  "operation": "validate",
  "scope": "project|user|all"
}
```

**Process:**

1. Find CLAUDE.md at specified scope(s)
2. Run validation checks:
   - **Structure**: Frontmatter, required sections
   - **Consistency**: Commands exist, paths valid
   - **Best Practices**: File size, no sensitive data
   - **Alignment**: Matches detected technologies
3. Return results without modifications

**Output:**

```json
{
  "success": true,
  "valid": false,
  "checks": {
    "structure": {
      "pass": true,
      "details": "All required sections present"
    },
    "consistency": {
      "pass": false,
      "details": "Path reference error (line 45)"
    },
    "best_practices": {
      "pass": true,
      "details": "Under recommended length"
    },
    "alignment": {
      "pass": true,
      "warnings": ["Missing Docker mention"]
    }
  },
  "errors": 1,
  "warnings": 1
}
```

## List Workflow

**Input:**

```json
{
  "operation": "list"
}
```

**Process:**

1. Scan all hierarchy levels:
   - Project: `./CLAUDE.md` or `./.claude/CLAUDE.md`
   - User: `~/.claude/CLAUDE.md`
   - Plugin: `<plugin>/.claude-plugin/CLAUDE.md`
2. Parse frontmatter of each found file
3. Validate each file
4. Return formatted list with status

**Output:**

```json
{
  "success": true,
  "files": [
    {
      "scope": "project",
      "path": "./CLAUDE.md",
      "valid": true,
      "updated": "2025-01-15T10:00:00Z"
    },
    {
      "scope": "user",
      "path": "~/.claude/CLAUDE.md",
      "valid": true,
      "updated": "2025-01-10T14:00:00Z"
    }
  ],
  "count": 2
}
```

## Error Handling

| Error | Cause | Resolution |
| --- | --- | --- |
| File not found | No CLAUDE.md at scope | Offer to create one |
| Permission denied | Can't write to location | Check file permissions |
| Invalid format | Malformed frontmatter | Show specific error |
| Scope conflict | File exists at target | Ask to overwrite |

## Template Variables

| Variable | Type | Description |
| --- | --- | --- |
| `name` | string | Project or config name |
| `description` | string | Brief description |
| `languages` | array | Detected languages |
| `tools` | array | Detected dev tools |
| `commands` | array | Build/dev commands |
| `project_type` | string | Type of project |
| `architecture` | string | Architecture notes |
| `conventions` | string | Coding conventions |
| `constraints` | string | Important constraints |
