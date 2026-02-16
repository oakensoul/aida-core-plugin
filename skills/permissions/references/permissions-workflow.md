---
type: reference
title: Permissions Workflow
description: Step-by-step guide for interactive permission management
---

# Permissions Workflow

End-to-end workflow for managing Claude Code permissions through
the AIDA plugin system.

## Overview

The permissions skill uses a two-phase interactive pattern to
scan plugin recommendations, present categorized choices, and
write the final configuration.

## Phase 1: Discovery and Questions

### Step 1: Scan Plugins

The scanner examines all installed plugins in the cache directory
for `recommendedPermissions` declarations.

### Step 2: Aggregate and Deduplicate

The aggregator merges categories across all plugins:

- Deduplicates identical rules
- Applies wildcard subsumption
- Tracks which plugins contributed each rule
- Preserves the most permissive suggestion per category

### Step 3: Read Current State

The settings manager reads existing permissions from all three
scopes (user, project, local) to detect conflicts.

### Step 4: Build Questions

The system generates questions:

1. **Preset selection** - Quick configuration profiles
2. **Per-category choices** - Only shown for "custom" preset
3. **Scope selection** - Where to save the configuration

## Phase 2: Apply Configuration

### Step 5: Resolve Choices

Based on responses, map categories to actions using either the
selected preset or individual custom choices.

### Step 6: Build Rules

Assemble the final rules dictionary with `allow`, `ask`, and
`deny` lists.

### Step 7: Write Settings

Write the rules to the selected scope's settings.json using
an atomic write operation with merge strategy.

## Audit Mode

When `--audit` is passed, the workflow skips Phase 2 and reports:

1. Coverage percentage (recommended vs configured)
2. Unconfigured rules (gaps)
3. Conflicting assignments across scopes
