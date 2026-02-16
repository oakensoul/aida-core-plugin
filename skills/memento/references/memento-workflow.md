---
type: reference
title: Memento Workflow
description: Step-by-step process for creating and managing mementos
---

# Memento Workflow

This document describes the workflow for creating, updating, and managing
mementos in the AIDA system.

## Overview

Mementos are persistent context snapshots stored in `~/.claude/memento/` that
help Claude resume work after `/clear`, `/compact`, or in new conversations.

## Create Workflow

### Phase 1: Get Questions

**Input Context:**

```json
{
  "operation": "create",
  "description": "User-provided description",
  "source": "manual|from-pr|from-changes"
}
```

**Process:**

1. **Infer slug** - Convert description to kebab-case
2. **Detect source** - Manual, from-pr, or from-changes
3. **For from-pr**:
   - Run `gh pr view --json title,body,files`
   - Extract PR context
4. **For from-changes**:
   - Run `git status` and `git diff --stat`
   - Summarize changes
5. **Return questions** for missing required fields

**Output:**

```json
{
  "questions": [
    {
      "id": "problem",
      "question": "What's the core problem you're solving?",
      "type": "text",
      "required": true
    }
  ],
  "inferred": {
    "slug": "fix-auth-bug",
    "project": "my-project",
    "description": "Fix auth bug",
    "source": "manual",
    "tags": []
  }
}
```

### Phase 2: Execute Create

**Input:**

```json
{
  "operation": "create",
  "slug": "fix-auth-bug",
  "description": "Fix auth bug",
  "source": "manual",
  "problem": "User response to problem question",
  "approach": "Optional approach",
  "tags": ["auth", "bug"],
  "files": ["src/auth.ts"]
}
```

**Process:**

1. Ensure `~/.claude/memento/` exists
2. Check for slug conflicts
3. Render template with provided data
4. Write to `~/.claude/memento/{project}--{slug}.md`
5. Return success with path

**Output:**

```json
{
  "success": true,
  "message": "Created memento 'fix-auth-bug'",
  "project": "my-project",
  "path": "~/.claude/memento/my-project--fix-auth-bug.md"
}
```

## Read Workflow

**Input:**

```json
{
  "operation": "read",
  "slug": "fix-auth-bug"
}
```

**Process:**

1. Find memento in `~/.claude/memento/`
2. Parse YAML frontmatter
3. Return full content + parsed frontmatter

**Output:**

```json
{
  "success": true,
  "slug": "fix-auth-bug",
  "project": "my-project",
  "content": "Full markdown content...",
  "frontmatter": {
    "type": "memento",
    "slug": "fix-auth-bug",
    "description": "Fix auth bug",
    "status": "active",
    "created": "2025-01-15T10:00:00Z",
    "updated": "2025-01-15T14:00:00Z"
  }
}
```

## List Workflow

**Input:**

```json
{
  "operation": "list",
  "filter": "active|completed|all",
  "project_filter": "optional-project-name",
  "all_projects": false
}
```

**Process:**

1. Scan `~/.claude/memento/` for `.md` files
2. Also scan `.completed/` if filter includes completed
3. Parse frontmatter of each file
4. Filter by status
5. Sort by updated date (most recent first)

**Output:**

```json
{
  "success": true,
  "mementos": [
    {
      "slug": "fix-auth-bug",
      "project": "my-project",
      "description": "Fix auth bug",
      "status": "active",
      "created": "2025-01-15T10:00:00Z",
      "updated": "2025-01-15T14:00:00Z",
      "path": "~/.claude/memento/my-project--fix-auth-bug.md"
    }
  ],
  "count": 1
}
```

## Update Workflow

### Phase 1: Get Section Options

**Input:**

```json
{
  "operation": "update",
  "slug": "fix-auth-bug"
}
```

**Output:**

```json
{
  "questions": [
    {
      "id": "section",
      "question": "Which section would you like to update?",
      "type": "choice",
      "options": ["progress", "decisions", "next_step", "approach", "files"]
    },
    {
      "id": "content",
      "question": "What would you like to add?",
      "type": "text"
    }
  ],
  "current": {
    "slug": "fix-auth-bug",
    "description": "Fix auth bug",
    "progress": "- Started implementation"
  }
}
```

### Phase 2: Execute Update

**Input:**

```json
{
  "operation": "update",
  "slug": "fix-auth-bug",
  "section": "progress",
  "content": "- Completed token refresh logic\n- Added error handling"
}
```

**Process:**

1. Load current memento
2. Update specified section (append or replace)
3. Update `updated` timestamp
4. Write back to file

**Output:**

```json
{
  "success": true,
  "message": "Updated progress section",
  "path": "~/.claude/memento/my-project--fix-auth-bug.md"
}
```

## Complete Workflow

**Input:**

```json
{
  "operation": "complete",
  "slug": "fix-auth-bug"
}
```

**Process:**

1. Load memento
2. Set `status: completed`
3. Ensure `.completed/` directory exists
4. Move to `~/.claude/memento/.completed/{project}--{slug}.md`
5. Return success

**Output:**

```json
{
  "success": true,
  "message": "Completed and archived memento 'fix-auth-bug'",
  "path": "~/.claude/memento/.completed/my-project--fix-auth-bug.md"
}
```

## Remove Workflow

**Input:**

```json
{
  "operation": "remove",
  "slug": "fix-auth-bug"
}
```

**Process:**

1. Find memento
2. Delete file
3. Return success

**Output:**

```json
{
  "success": true,
  "message": "Removed memento 'fix-auth-bug'"
}
```

## Error Handling

| Error              | Cause                    | Resolution                   |
| ------------------ | ------------------------ | ---------------------------- |
| Memento not found  | Slug doesn't exist       | List available mementos      |
| Slug conflict      | Name already exists      | Use different slug or update |
| Invalid slug       | Name contains bad chars  | Use kebab-case format        |
| Permission error   | Can't write to directory | Check directory permissions  |

## Template Variables

| Variable         | Type   | Description                      |
| ---------------- | ------ | -------------------------------- |
| `slug`           | string | Unique identifier (kebab-case)   |
| `description`    | string | Brief description of the memento |
| `status`         | string | active, completed, or archived   |
| `created`        | string | ISO timestamp of creation        |
| `updated`        | string | ISO timestamp of last update     |
| `source`         | string | manual, from-pr, or from-changes |
| `tags`           | array  | Classification tags              |
| `files`          | array  | Related file paths               |
| `problem`        | string | Problem statement                |
| `approach`       | string | Solution approach                |
| `completed`      | string | Completed items                  |
| `in_progress`    | string | Current work                     |
| `pending`        | string | Future work                      |
| `decisions`      | string | Key decisions made               |
| `files_detail`   | string | Detailed file descriptions       |
| `next_step`      | string | Clear next action                |
| `project_name`   | string | Project name (auto-detected)     |
| `project_path`   | string | Project root path                |
| `project_repo`   | string | Git remote URL                   |
| `project_branch` | string | Current git branch               |
