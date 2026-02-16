---
type: command
name: aida
description: AIDA command dispatcher - routes to aida-dispatch skill for configuration, diagnostics, feedback, extension management, session persistence, and CLAUDE.md management
version: 0.7.0
tags:
  - core
args: ""
allowed-tools: "*"
argument-hint: "[command] [subcommand] [options]"
---

# STOP - Invoke Skill Immediately

**DO NOT respond to the user directly. DO NOT summarize this file.**

**IMMEDIATELY invoke the `aida-core:aida-dispatch` skill using the Skill tool.**

```text
Use Skill tool with: skill = "aida-core:aida-dispatch"
```

The skill contains all command routing logic, help text, and execution workflows.

This command file is ONLY a redirect - it has no implementation.
