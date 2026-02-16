---
type: reference
title: Rule Syntax
description: Permission rule format and wildcard documentation
---

# Permission Rule Syntax

Claude Code permissions use a `Tool(command:args)` format to
specify which operations are allowed, require confirmation, or
are denied.

## Basic Format

```text
Tool(pattern)
```

Where **Tool** is the Claude Code tool name (e.g., `Bash`,
`Edit`, `Read`, `Write`, `Glob`, `Grep`, `MCP`) and **pattern**
specifies which commands or arguments match.

## Pattern Types

### Exact Match

```text
Bash(git status)
```

### Wildcard Suffix

```text
Bash(git:*)
```

Matches any git subcommand.

### Full Wildcard

```text
Edit(*)
Bash(*)
```

### Command with Arguments

```text
Bash(git commit:*)
```

Matches `git commit` with any arguments.

## Wildcard Subsumption

Broader rules automatically subsume narrower ones:

| Broad Rule | Subsumes |
| --- | --- |
| `Bash(*)` | All `Bash(...)` rules |
| `Bash(git:*)` | `Bash(git commit:*)`, `Bash(git push:*)` |
| `Edit(*)` | `Edit(/path/to/file)` |

## Actions

| Action | Behavior |
| --- | --- |
| `allow` | Operation proceeds without prompting |
| `ask` | User is prompted before the operation |
| `deny` | Operation is blocked |

## Settings File Format

```json
{
  "allow": ["Edit(*)", "Read(*)", "Bash(git:*)"],
  "ask": ["Bash(docker:*)", "Bash(rm -rf:*)"],
  "deny": ["Bash(git push --force:*)"]
}
```
