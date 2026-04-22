---
type: reference
name: marketplace-sync-schemas
description: >-
  Schema documentation for marketplace sync data model and
  plugin.json dependencies field.
version: 0.1.0
---

# Marketplace Sync Schemas

## plugin.json Dependencies Field

Plugins declare dependencies in their `plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "dependencies": {
    "aida-core": ">=1.4.0",
    "splash-engineering": "^1.0.0"
  }
}
```

### Version Operators

| Operator | Meaning | Example |
|---|---|---|
| `^` | Compatible (semver) | `^1.2.3` = `>=1.2.3 <2.0.0` |
| `~` | Patch updates only | `~1.2.3` = `>=1.2.3 <1.3.0` |
| `>=` | Minimum version | `>=1.0.0` |
| `=` | Exact match | `=1.2.3` |

Bare versions without an operator are treated as exact match.

### Zero-Major Special Cases

| Range | Expands to |
|---|---|
| `^0.2.3` | `>=0.2.3 <0.3.0` |
| `^0.0.3` | `>=0.0.3 <0.0.4` |

### Validation Rules

- Dependency names: `^[a-z][a-z0-9-]{0,49}$`
- Version strings: `^\d+\.\d+\.\d+$` (no pre-release)
- Constraint strings: max 64 characters
- Max 50 dependencies per plugin

## Data Model

### PluginState

Unified view of a plugin from the scanner.

| Field | Type | Description |
|---|---|---|
| `name` | str | Plugin name |
| `installed_version` | str or None | Currently installed version |
| `available_version` | str or None | Latest version in marketplace |
| `dependencies` | dict | Map of dependency name to constraint |
| `source` | str | "marketplace", "local", or "unknown" |
| `install_path` | str or None | Cache path |
| `marketplace_id` | str or None | Marketplace identifier |

### DependencyEdge

A single dependency relationship in the graph.

| Field | Type | Description |
|---|---|---|
| `dependent` | str | Plugin that requires |
| `dependency` | str | Plugin that is required |
| `constraint` | str | Raw constraint string |
| `satisfied` | bool | Is installed version in range? |
| `installed` | str or None | Installed version of dependency |

### ResolutionResult

Output from the dependency graph resolver.

| Field | Type | Description |
|---|---|---|
| `graph` | dict | Adjacency list of DependencyEdge lists |
| `install_order` | list | Topologically sorted plugin names |
| `cycles` | list | Detected circular dependencies |
| `conflicts` | list | Incompatible version constraints |
| `unresolved` | list | Dependencies not in any marketplace |
| `warnings` | list | Non-fatal issues |
