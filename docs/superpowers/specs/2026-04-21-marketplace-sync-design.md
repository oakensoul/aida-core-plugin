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
schema needed -- we are implementing what was already designed.

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

**Zero-major special cases** (per npm/semver convention):

| Range     | Expands to              |
|-----------|-------------------------|
| `^0.2.3`  | `>=0.2.3 <0.3.0`       |
| `^0.0.3`  | `>=0.0.3 <0.0.4`       |
| `~0.2.3`  | `>=0.2.3 <0.3.0`       |

**Bare versions** (no operator): treated as exact match (`1.4.0` =
`=1.4.0`).

**Pre-release versions**: not supported in v1. Version strings must
match `^\d+\.\d+\.\d+$`. Pre-release suffixes are rejected during
validation.

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

| Source | Provides |
|---|---|
| `~/.claude/plugins/installed_plugins.json` | Installed plugins, versions, SHAs, install paths |
| `{cache_path}/.claude-plugin/plugin.json` | Plugin metadata + dependencies |
| `~/.claude/plugins/marketplaces/{id}/.claude-plugin/marketplace.json` | Available versions, refs |
| `~/.claude/plugins/known_marketplaces.json` | Marketplace registry |
| `~/.claude/plugins/data/` | Inline/local plugins |

### Data Model

```python
@dataclass
class PluginState:
    """Unified view of a plugin from scanner."""
    name: str
    installed_version: str | None   # None if not installed
    available_version: str | None   # None if not in marketplace
    dependencies: dict[str, str]    # name -> version constraint
    source: str                     # "marketplace", "local", "unknown"
    install_path: str | None
    marketplace_id: str | None


@dataclass
class DependencyEdge:
    """A single dependency relationship."""
    dependent: str         # plugin that requires
    dependency: str        # plugin that is required
    constraint: str        # raw constraint string (e.g., ">=1.4.0")
    satisfied: bool        # is installed version in range?
    installed: str | None  # installed version of dependency


@dataclass
class ResolutionResult:
    """Output from the dependency graph resolver."""
    graph: dict[str, list[DependencyEdge]]  # adjacency list
    install_order: list[str]                 # topological order
    cycles: list[list[str]]                  # detected cycles
    conflicts: list[tuple[str, str, str]]    # (dep, constraint1, constraint2)
    unresolved: list[str]                    # deps not in any marketplace
```

Scanner returns `list[PluginState]`. Resolver takes that list and
returns `ResolutionResult`. Report takes both. Updater takes
`ResolutionResult.install_order` and `list[PluginState]`.

## Components

### 1. Version Range (`scripts/shared/version.py`)

Thin wrapper around `packaging.version.Version` (already available in
the venv as a pip transitive dependency):

- **`VersionRange` class** -- expands `^`/`~`/`>=`/`=` into a
  `(lower_bound, upper_bound)` pair using `packaging.version.Version`
  objects
- **`satisfies(version, constraint)` function** -- check if a version
  string falls within a range
- **Validation** -- rejects strings that don't match
  `^\d+\.\d+\.\d+$`, enforces 64-char max length on constraint strings

This module lives in `scripts/shared/` for reuse by plugin-manager
validate and upgrade.py. Replaces the existing hand-rolled
`compare_versions()` in `upgrade.py`.

### 2. Dependency Graph Resolver (`sync_ops/resolver.py`)

Builds and traverses the dependency tree using `VersionRange` from
shared:

- **Graph construction** -- build adjacency graph from `plugin.json`
  `dependencies` fields across all installed plugins
- **Topological sort** (Kahn's algorithm) -- determine install/update
  order so dependencies are processed before dependents
- **Cycle detection** -- error if circular dependencies exist
  (A requires B requires A)
- **Transitive resolution** -- if A needs B and B needs C, report A
  transitively needs C
- **Conflict detection** -- A needs `core@>=2.0.0` but B needs
  `core@^1.0.0`, report the conflict without picking a winner

### 3. Plugin Scanner (`sync_ops/scanner.py`)

Reads the current state:

- Installed plugins from `installed_plugins.json`
- Each cached plugin's `plugin.json` for version and dependencies
- Marketplace manifests from all known marketplaces
- Inline/local plugins from `~/.claude/plugins/data/`

Returns `list[PluginState]` -- a unified view of what's installed,
what's available, and what's declared as needed.

Accepts an injectable `home_dir` parameter (defaulting to
`get_home_dir()`) for testability.

**Unreadable plugin.json handling**: if a plugin's `plugin.json` is
missing, corrupt, or unreadable, the scanner logs a warning, sets
`dependencies` to `{}` and `installed_version` to `"unknown"`, and
continues scanning.

### 4. Report Generator (`sync_ops/report.py`)

Builds the drift report:

- **Table columns**: plugin, installed version, latest available,
  status, dependency issues
- **Status values**: `up-to-date`, `outdated`, `missing`,
  `unresolved` (dependency not in any marketplace), `local` (inline
  plugin), `ahead` (installed newer than marketplace)
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

### 5. Updater (`sync_ops/updater.py`)

Acts on the report when `--apply` is passed:

- Computes install/update order from topological sort (dependencies
  first)
- For missing plugins: instruct Claude Code to install from marketplace
- For outdated plugins: update cache to latest marketplace ref
- Updates `installed_plugins.json` entries using `update_json()` with
  file locking for atomicity
- Reports results per plugin (success/failure)

Defines an injectable interface for marketplace operations
(`clone_plugin`, `install_plugin`) that can be stubbed in tests.

### 6. Entry Point (`scripts/manage.py`)

Two-phase API following established pattern:

- **`sync` operation** (report-only): execute-only, no questions phase.
  Same pattern as `list` in expert-registry. Returns the full report
  as JSON.
- **`sync --apply` operation**: `--get-questions` phase presents the
  drift report as inferred context and returns a confirmation question.
  `--execute` phase applies the updates.
- **`status` operation**: execute-only, returns summary counts.

### 7. SKILL.md

```yaml
---
type: skill
name: marketplace-sync
description: >-
  Detect plugin version drift, resolve transitive dependency trees,
  and update outdated plugins from configured marketplaces.
version: 0.1.0
user-invocable: true
argument-hint: "[sync|sync --apply|status]"
tags: [core, marketplace, dependencies, sync]
---
```

## Routing

Add to `/aida` skill dispatcher in `skills/aida/SKILL.md`:

### Marketplace Commands

For `marketplace` commands:

- **Invoke the `marketplace-sync` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles sync (report), sync --apply (update), and status

**Process:**

1. Parse the command to extract:
   - Operation: `sync`, `status`
   - Flags: `--apply`, `--offline`

2. Invoke `marketplace-sync` skill with the parsed context

**Examples:**

```text
/aida marketplace sync            -> marketplace-sync skill (report)
/aida marketplace sync --apply    -> marketplace-sync skill (update)
/aida marketplace status          -> marketplace-sync skill (summary)
```

### Help Text Addition

Add under "Extension Management" in the help block:

```text
### Marketplace
- `/aida marketplace sync` - Report plugin versions and dependency status
- `/aida marketplace sync --apply` - Update outdated plugins
- `/aida marketplace status` - Quick summary of plugin drift
```

### Doctor Integration

Wire into `/aida doctor` as an optional check:

```text
* Marketplace drift: 1 plugin outdated, 1 dependency unsatisfied
  -> Run /aida marketplace sync for details
```

## Security Requirements

All file operations must reuse the established security patterns from
`skills/aida/scripts/utils/`.

### Path Validation

- All paths derived from `installed_plugins.json` entries must be
  validated with `resolve_path(path, allowed_base=cache_root)` from
  `utils/paths.py`
- All file reads must use `_safe_read_file()` from `utils/plugins.py`
  with `O_NOFOLLOW` to atomically reject symlinks (no
  check-then-open TOCTOU patterns)
- Scanner must verify resolved paths stay within
  `~/.claude/plugins/` before reading

### Input Validation

- **Dependency names**: validate against `^[a-z][a-z0-9-]{1,49}$`
  before processing. Reject names that could be path traversal
  attempts.
- **Version constraint strings**: max 64 characters, allowed character
  set `[0-9.^~>=< ]`. Reject before parsing.
- **Version strings**: must match `^\d+\.\d+\.\d+$` strictly. No
  pre-release, no build metadata.
- **Dependencies per plugin**: max 50. Reject plugins declaring more.

### Graph Limits

- **`MAX_DEPENDENCY_DEPTH = 20`**: fail gracefully if transitive
  chains exceed this depth
- **`MAX_TOTAL_PLUGINS = 200`**: upper bound on total graph nodes

### Write Safety

- All writes to `installed_plugins.json` must use `update_json()`
  from `utils/files.py` with file locking via `fcntl`
- New plugin cache entries are installed alongside existing ones (no
  destructive overwrites)

### Network Safety

- All `subprocess.run()` calls to `gh` must use `timeout=15`
- Dependencies may only be resolved from marketplaces listed in
  `known_marketplaces.json`. The resolver must never attempt to
  install a plugin from an unregistered source.

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
- **Unreadable plugin.json** -- skip with warning, set dependencies
  to empty, set version to "unknown", continue scanning

### Update Safety

- **Dry-run default** -- always show report first, require `--apply`
- **Install order** -- topological sort ensures deps before dependents
- **Partial failure** -- if one plugin fails, continue with others,
  report failures at end
- **No destructive cache ops** -- install new version alongside
  existing, let Claude Code pick up the new one
- **Idempotency** -- running `sync --apply` twice is safe. Second
  run detects everything is up-to-date and is a no-op.

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
|   +-- sync_ops/
|       +-- __init__.py
|       +-- resolver.py
|       +-- scanner.py
|       +-- report.py
|       +-- updater.py
+-- references/
    +-- schemas.md

scripts/shared/
+-- version.py          (NEW -- shared VersionRange, replaces
                         hand-rolled comparisons in upgrade.py)
```

## Testing Strategy

### Unit Tests

**`tests/unit/test_version.py`** (shared VersionRange module):

- All four operators: `^`, `~`, `>=`, `=`
- Zero-major caret: `^0.2.3` -> `>=0.2.3 <0.3.0`
- Zero-minor caret: `^0.0.3` -> `>=0.0.3 <0.0.4`
- Bare version without operator (treated as exact match)
- Invalid/malformed strings: `>=abc`, `^`, `""`, `>=1.0`
- Whitespace in ranges: `>= 1.0.0`
- Version string length over 64 chars (rejected)
- Pre-release strings (rejected)

**`tests/unit/test_resolver.py`** (dependency graph):

- Graph build from mock plugin data
- Topological sort correctness
- Cycle detection (length 2 and length 3+)
- Self-dependency (A depends on A)
- Diamond dependency (A->B, A->C, B->D, C->D)
- Empty graph (zero plugins)
- Conflict detection (incompatible constraints on same dep)
- Transitive resolution across 3+ levels
- Depth limit exceeded (>20 levels)
- Node limit exceeded (>200 plugins)

**`tests/unit/test_scanner.py`** (plugin scanner):

- Normal scan with mock installed_plugins.json and plugin cache
- Corrupt or missing installed_plugins.json
- Plugin cached without plugin.json
- Marketplace manifest with no plugin list
- Empty known_marketplaces.json
- Inline/local plugins in data/ directory
- Plugin in multiple marketplaces (prefers current)
- Plugin with "unknown" version
- Dependencies field is non-object (string, list) -- treated as empty

**`tests/unit/test_report.py`** (report generator):

- All statuses: up-to-date, outdated, missing, unresolved, local, ahead
- Empty plugin set (zero installed)
- All plugins up-to-date (clean report)
- Deep dependency tree indentation
- Plugin with unknown version

**`tests/unit/test_updater.py`** (updater):

- Topological install ordering correctness
- Partial failure (one plugin fails, others continue)
- Dry-run flag preventing any writes
- Idempotent apply (already up-to-date = no-op)
- Atomic write to installed_plugins.json (mocked update_json)
- Injectable marketplace interface (stubbed clone/install)

### Integration Tests

**`tests/integration/test_marketplace_sync_integration.py`**:

- Full pipeline: mock ecosystem -> scan -> resolve -> report
- Transitive dependency resolution across 3+ levels
- Multi-marketplace resolution
- Inline/local plugin handling
- Partial dependency graphs (some plugins have deps, some don't)
- Update ordering respects topological sort
- Error recovery: simulated failure mid-apply, others continue
- Idempotent apply: second run is a no-op
- Offline mode: stale marketplace with freshness warning

All tests use `tempfile.TemporaryDirectory` fixtures with mock data.
No live network calls. Scanner accepts injectable `home_dir` for test
isolation. Updater uses injectable marketplace interface. New
`sync_ops` package needs `_ops_snapshot` module isolation in conftest
(same pattern as `test_update_scanner.py`).

Use `@pytest.mark.parametrize` for semver range parsing tests.

## Migration

Existing plugins need `dependencies` populated in their `plugin.json`.
This can happen incrementally -- the sync skill treats missing
`dependencies` as an empty object. As plugins add dependency
declarations, the sync report becomes more useful.

### Initial Population

The following known dependencies should be declared:

| Plugin | Dependencies |
|---|---|
| `aida-core` | none (foundation) |
| `splash-engineering` | `{"aida-core": ">=1.0.0"}` |
| `splash-prd-manager` | `{"aida-core": ">=1.4.0", "splash-engineering": ">=1.0.0"}` |
| `splash-uber-architect` | `{"aida-core": ">=1.0.0", "splash-engineering": ">=1.0.0"}` |
| `splash-brand-design` | `{"aida-core": ">=1.0.0"}` |
| `splash-admin-playbook` | `{"aida-core": ">=1.0.0", "splash-engineering": ">=1.0.0"}` |
| `splash-contests-playbook` | `{"aida-core": ">=1.0.0", "splash-engineering": ">=1.0.0"}` |
| `splash-onboarding-plugin` | `{"aida-core": ">=1.0.0"}` |
| `splashsql` | `{"aida-core": ">=1.0.0"}` |

### Scaffold Template Update

Update `skills/plugin-manager/templates/scaffold/shared/plugin.json.jinja2`
to include `"dependencies": {}` so new plugins get the field from day one.

## Open Questions

- Should `/aida marketplace sync --apply` use `gh` to clone repos
  directly, or shell out to Claude Code's plugin install mechanism?
  (Investigate Claude Code's cache invalidation during implementation.)
- Should the `validate` operation in plugin-manager enforce that
  declared dependencies exist in the marketplace? (Likely yes, as a
  warning not a blocker.)
