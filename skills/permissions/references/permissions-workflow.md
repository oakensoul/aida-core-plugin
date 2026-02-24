---
type: reference
title: Permissions Workflow
description: Step-by-step guide for interactive permission management
---

# Permissions Workflow

End-to-end workflow for managing Claude Code permissions through
the AIDA plugin system.

## Quick Start

Two-phase interactive flow:

1. Get questions and inferred data from plugin scan
2. Execute with user responses to apply permissions

---

## CLI Reference

### Phase 1: Get Questions

```bash
python3 {base_directory}/scripts/permissions.py \
  --get-questions \
  --context '{"operation": "setup"}'
```

The `--get-questions` flag triggers plugin scanning, aggregation,
and question generation. The `--context` argument accepts a JSON
string or a path to a JSON file.

Context JSON:

```json
{
  "operation": "setup"
}
```

Returns:

```json
{
  "questions": [
    {
      "id": "preset",
      "type": "choice",
      "prompt": "Select a permissions preset",
      "choices": [
        {"value": "developer-workstation", "label": "Developer Workstation"},
        {"value": "ci-safe", "label": "CI Safe"},
        {"value": "locked-down", "label": "Locked Down"},
        {"value": "custom", "label": "Custom"}
      ],
      "default": "developer-workstation"
    },
    {
      "id": "category_file-edit",
      "type": "choice",
      "prompt": "Permission for: File Edit",
      "choices": [
        {"value": "allow", "label": "Allow"},
        {"value": "ask", "label": "Ask"},
        {"value": "deny", "label": "Deny"}
      ],
      "condition": {"preset": "custom"}
    },
    {
      "id": "scope",
      "type": "choice",
      "prompt": "Where should permissions be saved?",
      "choices": [
        {"value": "user", "label": "User (~/.claude/settings.json)"},
        {"value": "project", "label": "Project (.claude/settings.json)"},
        {"value": "local", "label": "Local (.claude/settings.local.json)"}
      ],
      "default": "user"
    }
  ],
  "inferred": {
    "categories": {"file-edit": {"label": "File Edit", "rules": ["Edit"], "suggested": "allow"}},
    "current_permissions": {"user": {"allow": [], "ask": [], "deny": []}},
    "conflicts": [],
    "plugin_count": 3
  }
}
```

### Phase 2: Execute

```bash
python3 {base_directory}/scripts/permissions.py \
  --execute '{"preset": "developer-workstation", "scope": "user"}' \
  --context '{"categories": {"file-edit": {"label": "File Edit", "rules": ["Edit"], "suggested": "allow"}}}'
```

The `--execute` argument takes a JSON string (or file path) of
user responses keyed by question `id`. The `--context` argument
provides the `inferred` data from Phase 1.

Responses JSON (preset mode):

```json
{
  "preset": "developer-workstation",
  "scope": "user"
}
```

Responses JSON (custom mode):

```json
{
  "preset": "custom",
  "category_file-edit": "allow",
  "category_file-read": "allow",
  "category_git": "allow",
  "category_terminal": "allow",
  "category_docker": "deny",
  "category_mcp": "ask",
  "category_network": "ask",
  "category_dangerous": "deny",
  "scope": "project"
}
```

Context JSON (pass `inferred` from Phase 1):

```json
{
  "categories": {
    "file-edit": {
      "label": "File Edit",
      "rules": ["Edit"],
      "suggested": "allow",
      "sources": ["core-plugin"]
    },
    "terminal": {
      "label": "Terminal",
      "rules": ["Bash(*)"],
      "suggested": "allow",
      "sources": ["core-plugin"]
    }
  }
}
```

Returns:

```json
{
  "success": true,
  "files_modified": ["/Users/username/.claude/settings.json"],
  "rules_count": 12,
  "message": "Wrote 12 permission rules to /Users/username/.claude/settings.json"
}
```

### Audit Mode

```bash
python3 {base_directory}/scripts/permissions.py \
  --audit \
  --context '{"operation": "audit"}'
```

The `--audit` flag skips Phase 2 and produces a coverage report
comparing recommended rules against current configuration.

Returns:

```json
{
  "coverage": {
    "total_recommended": 15,
    "total_configured": 12,
    "covered": 12,
    "percentage": 80.0
  },
  "gaps": ["WebFetch(*)", "NotebookEdit"],
  "conflicts": [],
  "summary": "12/15 recommended rules configured (80% coverage). 3 gaps, 0 conflicts."
}
```

---

## Workflow Details

### Overview

The permissions skill uses a two-phase interactive pattern to
scan plugin recommendations, present categorized choices, and
write the final configuration.

### Phase 1: Discovery and Questions

#### Step 1: Scan Plugins

The scanner examines all installed plugins in the cache directory
for `recommendedPermissions` declarations in `aida-config.json`.

#### Step 2: Aggregate and Deduplicate

The aggregator merges categories across all plugins:

- Deduplicates identical rules
- Applies wildcard subsumption
- Tracks which plugins contributed each rule
- Preserves the most permissive suggestion per category

#### Step 3: Read Current State

The settings manager reads existing permissions from all three
scopes (user, project, local) to detect conflicts.

#### Step 4: Build Questions

The system generates questions:

1. **Preset selection** - Quick configuration profiles
2. **Per-category choices** - Only shown for "custom" preset
3. **Scope selection** - Where to save the configuration

### Phase 2: Apply Configuration

#### Step 5: Resolve Choices

Based on responses, map categories to actions using either the
selected preset or individual custom choices.

#### Step 6: Build Rules

Assemble the final rules dictionary with `allow`, `ask`, and
`deny` lists.

#### Step 7: Write Settings

Write the rules to the selected scope's settings.json using
an atomic write operation with merge strategy.

---

## Presets

Available preset configurations:

| Preset | file-edit | file-read | git | terminal | docker | mcp | network | dangerous |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| developer-workstation | allow | allow | allow | allow | ask | allow | allow | ask |
| ci-safe | ask | allow | ask | ask | deny | ask | ask | deny |
| locked-down | ask | ask | ask | ask | ask | ask | ask | ask |

---

## Error Handling

If `--execute` fails to write permissions:

```json
{
  "success": false,
  "files_modified": [],
  "rules_count": 0,
  "message": "Failed to write permissions: <error details>"
}
```

If `--execute` is called without `--context`, the script
automatically runs Phase 1 internally to obtain category data
before applying the responses.

## JSON Input Options

Both `--execute` and `--context` accept either:

- **Inline JSON string**: Pass the JSON directly as a CLI argument
- **File path**: Pass a path to a `.json` file on disk

The script detects file paths automatically. File size is limited
to 1 MB and symlinks are rejected for security.
