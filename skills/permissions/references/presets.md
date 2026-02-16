---
type: reference
title: Permission Presets
description: Pre-configured permission profiles for common use cases
---

# Permission Presets

Presets provide quick permission configuration for common
development scenarios.

## Developer Workstation

**Use case**: Local development with full tool access.

| Category | Action |
| --- | --- |
| File Editing | allow |
| File Reading | allow |
| Git Operations | allow |
| Terminal Commands | allow |
| Docker Operations | ask |
| MCP Servers | allow |
| Network Access | allow |
| Dangerous Operations | ask |

## CI Safe

**Use case**: Continuous integration or shared environments.

| Category | Action |
| --- | --- |
| File Editing | ask |
| File Reading | allow |
| Git Operations | ask |
| Terminal Commands | ask |
| Docker Operations | deny |
| MCP Servers | ask |
| Network Access | ask |
| Dangerous Operations | deny |

## Locked Down

**Use case**: Maximum oversight. Every operation requires
explicit approval.

| Category | Action |
| --- | --- |
| File Editing | ask |
| File Reading | ask |
| Git Operations | ask |
| Terminal Commands | ask |
| Docker Operations | ask |
| MCP Servers | ask |
| Network Access | ask |
| Dangerous Operations | ask |

## Custom Configuration

When "Custom" is selected, the system presents per-category
choices allowing fine-grained control. Each category can be
independently set to allow, ask, or deny.
