---
type: reference
title: Claude Code Expert Knowledge Index
description: Catalog of knowledge documents for the claude-code-expert agent
---

# Knowledge Index

This directory contains reference documentation for the claude-code-expert
agent. Use this index to find the right document for your needs.

## Documents

### framework-design-principles.md

**When to use:** For architectural decisions and quality standards

Contains:

- The WHO/WHAT/HOW/CONTEXT framework
- Quality standards for all extension types
- The Consultant Rule (how agents should work)
- What belongs vs doesn't belong in each type

This is the **authoritative reference** for extension architecture.

### extension-types.md

**When to use:** When deciding which type of extension to create

Contains:

- Decision tree for choosing between agent, command, skill, and plugin
- Characteristics of each extension type
- Example use cases for each type

### design-patterns.md

**When to use:** When designing the structure of an extension

Contains:

- Common architectural patterns
- Best practices for each extension type
- Template customization guidelines
- Plugin organization patterns

### plugin-development.md

**When to use:** When creating or distributing plugins

Contains:

- Plugin structure and required files
- plugin.json schema (all fields)
- marketplace.json for publishing
- Versioning and dependencies
- Installation and management

### claude-md-files.md

**When to use:** When creating or maintaining CLAUDE.md memory files

Contains:

- Memory vs Settings distinction
- Memory file hierarchy (Enterprise, Project, User, Parent)
- Import system (`@path/to/file` syntax)
- `/memory` command usage
- Content guidelines and best practices
- Multi-file organization patterns

### settings.md

**When to use:** When configuring Claude Code behavior via settings.json

Contains:

- Settings file locations and precedence
- Core settings (model, env, permissions, hooks)
- Advanced settings (status line, sandbox, plugins)
- Authentication configuration
- Environment variables reference
- Example configurations for different scenarios

### hooks.md

**When to use:** When implementing deterministic automation via hooks

Contains:

- Hook lifecycle events (PreToolUse, PostToolUse, etc.)
- Configuration structure and matcher patterns
- Hook execution model (stdin JSON, exit codes)
- Security considerations
- Common patterns (formatting, logging, blocking)
- Hooks vs other extension types comparison

## Quick Reference

| Question                                | Document                       |
| --------------------------------------- | ------------------------------ |
| "What's the architecture framework?"    | framework-design-principles.md |
| "What belongs in an agent vs skill?"    | framework-design-principles.md |
| "What does 'excellent' look like?"      | framework-design-principles.md |
| "Should I create an agent or skill?"    | extension-types.md             |
| "What's the difference between types?"  | extension-types.md             |
| "How should I structure my agent?"      | design-patterns.md             |
| "What are best practices?"              | design-patterns.md             |
| "How do I organize a plugin?"           | design-patterns.md             |
| "What goes in plugin.json?"             | plugin-development.md          |
| "How do I publish a plugin?"            | plugin-development.md          |
| "How do plugins work?"                  | plugin-development.md          |
| "What should CLAUDE.md contain?"        | claude-md-files.md             |
| "Where do CLAUDE.md files go?"          | claude-md-files.md             |
| "How do I write project instructions?"  | claude-md-files.md             |
| "How do memory files work?"             | claude-md-files.md             |
| "How do I import files in CLAUDE.md?"   | claude-md-files.md             |
| "What goes in settings.json?"           | settings.md                    |
| "How do I configure permissions?"       | settings.md                    |
| "Memory vs settings - when to use?"     | settings.md, claude-md-files.md|
| "How do hooks work?"                    | hooks.md                       |
| "How do I auto-format code?"            | hooks.md                       |
| "How do I block dangerous operations?"  | hooks.md                       |
| "What lifecycle events exist?"          | hooks.md                       |

## External Resources

For edge cases or latest features not covered here, fetch the official
Claude Code documentation:

- Claude Code Docs: <https://docs.anthropic.com/en/docs/claude-code>
- Agent SDK: <https://github.com/anthropics/claude-code/tree/main/sdk>

Use WebFetch tool to retrieve current documentation when:

- User asks about features not covered in knowledge/
- Schema or API has potentially changed
- Best practices need verification against latest docs
