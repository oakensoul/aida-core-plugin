---
type: skill
name: marketplace-sync
description: >-
  Detect plugin version drift, resolve transitive dependency trees,
  and update outdated plugins from configured marketplaces.
version: 0.1.0
user-invocable: true
argument-hint: "[sync|sync --apply|status]"
tags:
  - core
  - marketplace
  - dependencies
  - sync
---

# Marketplace Sync

Detects plugin version drift, resolves transitive dependency trees,
and updates outdated plugins from configured marketplaces.

## Activation

This skill activates when:

- User invokes `/aida marketplace sync`
- User invokes `/aida marketplace status`
- Plugin dependency resolution is needed

## Command Routing

When this skill activates, parse the command to determine:

1. **Operation**: `sync` or `status`
2. **Flags**: `--apply`, `--offline`

### Sync Operation (default)

For `sync` without `--apply`:

1. Run Phase 1 (`--get-questions`) with
   `{"operation": "sync"}`
2. The script scans installed plugins, reads dependency declarations,
   resolves the full transitive graph, and compares against marketplace
   versions
3. Present the report to the user (no questions asked)

For `sync --apply`:

1. Run Phase 1 with `{"operation": "sync", "apply": true}`
2. Present the report and ask for confirmation
3. On confirmation, run Phase 2 (`--execute`) to apply updates

### Status Operation

For `status`:

1. Run Phase 1 with `{"operation": "status"}`
2. Returns summary counts (total, outdated, missing, etc.)
3. No questions asked

## Path Resolution

**Base Directory:** Provided when skill loads.

**Script Execution:**

```text
{base_directory}/scripts/manage.py
```

## Two-Phase API

### Phase 1: Get Questions

```bash
~/.aida/venv/bin/python3 {base_directory}/scripts/manage.py \
    --get-questions --context='{"operation": "sync"}'
```

Returns JSON with:

- `report`: full sync report with plugin table, dependency issues,
  and summary
- `questions`: empty for read-only sync, confirmation question for
  `--apply`
- `summary`: counts dict for status operation

### Phase 2: Execute

```bash
~/.aida/venv/bin/python3 {base_directory}/scripts/manage.py \
    --execute \
    --context='{"operation": "sync", "apply": true}' \
    --responses='{"confirm": true}'
```

Applies updates in topological order (dependencies first).

## Example Workflows

### Check Plugin Drift

```text
User: /aida marketplace sync

1. Parse: operation=sync
2. Run Phase 1: scan, resolve, report
3. Present table: plugin versions, dependency satisfaction
4. No further action needed
```

### Update Outdated Plugins

```text
User: /aida marketplace sync --apply

1. Parse: operation=sync, apply=true
2. Run Phase 1: scan, resolve, report + confirmation question
3. User confirms
4. Run Phase 2: update in topological order
5. Report results
```

### Quick Status Check

```text
User: /aida marketplace status

1. Parse: operation=status
2. Run Phase 1: scan, resolve, summary counts
3. Present: "4 plugins, 1 outdated, 1 dependency unsatisfied"
```
