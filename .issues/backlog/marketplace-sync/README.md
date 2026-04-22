---
type: issue
title: "Marketplace sync: detect version drift and update installed plugins"
status: "Backlog"
created: "2026-04-21"
estimated_effort: 8
labels: ["enhancement", "marketplace"]
---

# Marketplace Sync

**Status**: Backlog
**Labels**: enhancement, marketplace

## Problem

When plugins are updated in the marketplace (e.g., aida-core v1.2.0 to
v1.4.0), there is no tooling to:

1. **Detect version drift** -- compare installed plugin versions
   (`~/.claude/plugins/cache/`) against the marketplace manifest
2. **Update installed plugins** -- pull the latest versions from
   the marketplace
3. **Resolve dependencies** -- ensure inter-plugin compatibility
   when updating

Today, plugin updates require manually discovering that a new version
exists, then waiting for Claude Code's auto-update to pick up the
marketplace change. There's no way to proactively check or force a sync.

## Current State

- `/aida upgrade` only checks aida-core itself against GitHub releases
- `/aida status` shows installed versions but doesn't compare to
  marketplace
- `/aida plugin update` migrates scaffold standards, not marketplace
  versions
- The marketplace repo has `npm run check`/`npm run update` for
  maintaining the manifest, but nothing consumer-facing

## Proposed Solution

A `/aida marketplace sync` (or similar) skill that:

1. **Reads the marketplace manifest** from the configured marketplace
   source
2. **Compares installed versions** in `~/.claude/plugins/cache/`
   against marketplace versions
3. **Reports drift** with a clear table (plugin, installed, available,
   status)
4. **Optionally triggers update** -- either by clearing the cache entry
   so Claude Code re-fetches, or by directly pulling the new version

### Stretch Goals

- Inter-plugin dependency declaration and resolution (per ADR-008)
- Compatibility matrix validation before updating
- Rollback support if an update breaks something

## Context

This came up when aida-core v1.4.0 (expert registry and panels) was
merged to main but the installed plugin was still at v1.2.0. The entire
expert registry feature was invisible because the marketplace hadn't
been updated and there was no way to detect or fix this from the
consumer side.

## Open Questions

- Should this be a skill under `/aida marketplace` or extend
  `/aida upgrade`?
- How does Claude Code's built-in plugin cache invalidation work?
  Can we trigger it, or do we need to work around it?
- Should drift detection run automatically on `/aida status` or
  `/aida doctor`?
