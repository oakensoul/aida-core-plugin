---
type: spec
title: "Marketplace Sync: Dependency Resolution and Version Drift Detection"
created: "2026-04-21"
status: draft
issue: marketplace-sync
---

# Marketplace Sync Design Spec

## Problem

When plugins are updated in the marketplace, there is no consumer-side
tooling to:

1. Detect version drift between installed and available versions
2. Resolve plugin dependency trees (including transitive dependencies)
3. Install missing or update outdated dependencies

This surfaced when aida-core v1.4.0 (expert registry + panels) was on
`main` but the installed plugin was still at v1.2.0. The entire feature
was invisible because no tooling detected or reported the gap.

## Solution

A new `marketplace-sync` skill that reads dependency declarations from
each plugin's `plugin.json`, builds a full transitive dependency graph,
compares installed versions against marketplace availability, and offers
to install or update plugins to resolve drift.

## Design Decisions

### Dependency Declaration Format

Use the existing `dependencies` field already documented in the
`plugin.json` schema (see `skills/plugin-manager/references/schemas.md`
and `agents/claude-code-expert/knowledge/plugin-development.md`). No new
schema needed — we are implementing what was already designed.

```json
{
  "name": "splash-prd-manager",
  "version": "0.4.0",
  "dependencies": {
    "aida-core": ">=1.4.0",
    "splash-engineering": "^1.0.0"
  }
}
```

**Version operators** (already documented):

| Operator | Meaning             | Example                      |
|----------|---------------------|------------------------------|
| `^`      | Compatible (semver) | `^1.2.3` = `>=1.2.3 <2.0.0` |
| `~`      | Patch updates only  | `~1.2.3` = `>=1.2.3 <1.3.0` |
| `>=`     | Minimum version     | `>=1.0.0`                    |
| `=`      | Exact match         | `=1.2.3`                     |

### Two-Layer Resolution (Approach C)

Plugins declare dependencies in their own `plugin.json` (source of
truth, versioned with the code). The marketplace manifest can optionally
mirror these for pre-install discovery. The sync skill reads from cached
plugin `plugin.json` files first, falls back to the marketplace for
plugins not yet installed.

### Read-First, Update-Second

The skill always produces a report first. Updates require explicit
`--apply` flag. This follows the pattern of the marketplace repo's own
`npm run check` vs `npm run update` separation.

## Architecture

### Data Flow

```text
installed_plugins.json --> list installed plugins + versions
        |
        v
each plugin's plugin.json --> read dependencies field
        |
        v
build dependency graph (topological sort, cycle detection)
        |
        v
marketplace.json --> check available versions
        |
        v
compare: installed vs required vs available
        |
        v
report table + offer updates
```

### Data Sources

| Source                                          | Provides                        |
|-------------------------------------------------|---------------------------------|
| `~/.claude/plugins/installed_plugins.json`      | Installed plugins, versions,    |
|                                                 | SHAs, install paths             |
| `{cache_path}/.claude-plugin/plugin.json`       | Plugin metadata + dependencies  |
| `~/.claude/plugins/marketplaces/{id}/.claude-plugin/marketplace.json` | Available versions, refs        |
| `~/.claude/plugins/known_marketplaces.json`     | Marketplace registry            |
| `~/.claude/plugins/data/`                       | Inline/local plugins            |

## Components

### 1. Dependency Graph Resolver (`marketplace_ops/resolver.py`)

Core logic that builds and traverses the dependency tree:

- **Semver range parsing** -- expand `^1.0.0` to `>=1.0.0 <2.0.0`,
  `~1.2.3` to `>=1.2.3 <1.3.0`, etc.
- **Version satisfaction** -- check if an installed version satisfies a
  declared range
- **Graph construction** -- build adjacency graph from `plugin.json`
  `dependencies` fields across all installed plugins
- **Topological sort** -- determine install/update order so
  dependencies are processed before dependents
- **Cycle detection** -- error if circular dependencies exist
  (A requires B requires A)
- **Transitive resolution** -- if A needs B and B needs C, report A
  transitively needs C

### 2. Plugin Scanner (`marketplace_ops/scanner.py`)

Reads the current state:

- Installed plugins from `installed_plugins.json`
- Each cached plugin's `plugin.json` for version and dependencies
- Marketplace manifests from all known marketplaces
- Inline/local plugins from `~/.claude/plugins/data/`

Returns a unified view: what's installed, what's available, what's
declared as needed.

### 3. Report Generator (`marketplace_ops/report.py`)

Builds the drift report:

- **Table columns**: plugin, installed version, latest available,
  status, dependency issues
- **Status values**: `up-to-date`, `outdated`, `missing`,
  `unresolved` (dependency not in any marketplace)
- **Dependency tree view** showing transitive chains with indentation
- **Summary line**: total plugins, outdated count, missing deps count

Example output:

```text
Marketplace Sync Report
=======================

Installed Plugins:
  Plugin                   Installed  Available  Status
  aida-core                1.2.0      1.4.0      outdated
  splash-engineering       1.2.0      1.2.0      up-to-date
  splash-prd-manager       0.4.0      0.4.0      up-to-date
  splash-brand-design      0.2.0      0.2.0      up-to-date

Dependency Issues:
  splash-prd-manager requires aida-core >=1.4.0
    -> installed: 1.2.0 (NOT SATISFIED)

Dependency Tree:
  splash-prd-manager@0.4.0
    -> aida-core@>=1.4.0 (installed: 1.2.0, available: 1.4.0)
    -> splash-engineering@^1.0.0 (installed: 1.2.0, satisfied)

Summary: 4 plugins, 1 outdated, 1 dependency unsatisfied
Run /aida marketplace sync --apply to update
```

### 4. Updater (`marketplace_ops/updater.py`)

Acts on the report when `--apply` is passed:

- Computes install/update order from topological sort (dependencies
  first)
- For missing plugins: instruct Claude Code to install from marketplace
- For outdated plugins: update cache to latest marketplace ref
- Updates `installed_plugins.json` entries
- Reports results per plugin (success/failure)

### 5. Entry Point (`scripts/manage.py`)

Two-phase API following established pattern:

- `--get-questions` phase: scan and build report, return as JSON
- `--execute` phase: apply updates if requested

### 6. SKILL.md

Frontmatter and routing definition for the skill. Operations:

- `sync` -- full report (default, read-only)
- `sync --apply` -- report then update
- `status` -- quick summary count

## Routing

Add to `/aida` skill dispatcher:

```text
/aida marketplace sync          -> marketplace-sync skill (report)
/aida marketplace sync --apply  -> marketplace-sync skill (update)
/aida marketplace status        -> marketplace-sync skill (summary)
```

Wire into `/aida doctor` as an optional diagnostic:

```text
* Marketplace drift: 1 plugin outdated, 1 dependency unsatisfied
  -> Run /aida marketplace sync for details
```

## Error Handling

### Dependency Resolution

- **Circular dependencies** -- detect during graph build, report as
  error, do not attempt to resolve
- **Unresolvable deps** -- dependency names a plugin not in any
  marketplace, status `unresolved` with suggestion to check marketplace
- **Version conflicts** -- A needs `core@>=2.0.0` but B needs
  `core@^1.0.0`, report the conflict without picking a winner
- **Missing dependencies field** -- treat as no dependencies (empty
  object), most plugins won't have it initially

### Plugin Sources

- **Multi-marketplace** -- scanner reads all known marketplaces,
  matches by plugin name, prefers marketplace where plugin is
  currently installed
- **Inline/local plugins** -- plugins in `~/.claude/plugins/data/`
  have no marketplace version, report as `local` status, skip update
- **Unknown versions** -- some official plugins cache as "unknown",
  report honestly, skip version comparison

### Update Safety

- **Dry-run default** -- always show report first, require `--apply`
- **Install order** -- topological sort ensures deps before dependents
- **Partial failure** -- if one plugin fails, continue with others,
  report failures at end
- **No destructive cache ops** -- install new version alongside
  existing, let Claude Code pick up the new one

### Network

- **Offline mode** -- if marketplace clone is stale or `gh` is not
  available, work from cached marketplace data with freshness warning
- **Marketplace refresh** -- pull latest marketplace before comparing,
  skippable with `--offline`

## File Structure

```text
skills/marketplace-sync/
+-- SKILL.md
+-- scripts/
|   +-- _paths.py
|   +-- manage.py
|   +-- marketplace_ops/
|       +-- __init__.py
|       +-- resolver.py
|       +-- scanner.py
|       +-- report.py
|       +-- updater.py
+-- references/
    +-- schemas.md
```

## Testing Strategy

### Unit Tests (`tests/unit/test_marketplace_sync.py`)

- Semver range parsing (all four operators)
- Version satisfaction checking
- Dependency graph building from mock plugin.json data
- Topological sort correctness
- Cycle detection
- Version conflict detection
- Report generation with various plugin states (up-to-date, outdated,
  missing, unresolved, local)

### Integration Tests (`tests/integration/test_marketplace_sync_integration.py`)

- Full pipeline: mock installed_plugins.json + mock plugin cache +
  mock marketplace manifest -> report
- Transitive dependency resolution across 3+ levels
- Multi-marketplace resolution
- Inline/local plugin handling
- Partial dependency graphs (some plugins have deps, some don't)
- Update ordering respects topological sort

All tests use tmpdir fixtures with mock data. No live network calls.

## Migration

Existing plugins need `dependencies` populated in their `plugin.json`.
This can happen incrementally -- the sync skill treats missing
`dependencies` as an empty object. As plugins add dependency
declarations, the sync report becomes more useful.

### Initial Population

The following known dependencies should be declared:

| Plugin                | Dependencies                              |
|-----------------------|-------------------------------------------|
| `aida-core`           | none (foundation)                         |
| `splash-engineering`  | `{"aida-core": ">=1.0.0"}`               |
| `splash-prd-manager`  | `{"aida-core": ">=1.4.0",`               |
|                       |  `"splash-engineering": ">=1.0.0"}`       |
| `splash-uber-architect` | `{"aida-core": ">=1.0.0",`             |
|                       |  `"splash-engineering": ">=1.0.0"}`       |
| `splash-brand-design` | `{"aida-core": ">=1.0.0"}`               |
| `splash-admin-playbook` | `{"aida-core": ">=1.0.0",`             |
|                       |  `"splash-engineering": ">=1.0.0"}`       |
| `splash-contests-playbook` | `{"aida-core": ">=1.0.0",`           |
|                       |  `"splash-engineering": ">=1.0.0"}`       |
| `splash-onboarding-plugin` | `{"aida-core": ">=1.0.0"}`           |
| `splashsql`           | `{"aida-core": ">=1.0.0"}`               |

## Open Questions

- Should the scaffold templates (`plugin.json.jinja2`) be updated to
  include `dependencies: {}` so new plugins get the field from day one?
- Should the `validate` operation in plugin-manager enforce that
  declared dependencies exist in the marketplace?
- Should `/aida marketplace sync --apply` use `gh` to clone repos
  directly, or shell out to Claude Code's plugin install mechanism?
