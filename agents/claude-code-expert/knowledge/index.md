---
type: reference
title: Claude Code Expert Knowledge Index
description: Catalog of knowledge documents for the claude-code-expert agent
---

# Knowledge Index

This directory contains reference documentation for the claude-code-expert
agent. Use this index to find the right document for your needs.

## Documents

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

## Quick Reference

| Question                                | Document           |
| --------------------------------------- | ------------------ |
| "Should I create an agent or skill?"    | extension-types.md |
| "What's the difference between types?"  | extension-types.md |
| "How should I structure my agent?"      | design-patterns.md |
| "What are best practices?"              | design-patterns.md |
| "How do I organize a plugin?"           | design-patterns.md |

## External Resources

For edge cases or latest features not covered here, fetch the official
Claude Code documentation:

- Claude Code Docs: <https://docs.anthropic.com/en/docs/claude-code>
- Agent SDK: <https://github.com/anthropics/claude-code/tree/main/sdk>

Use WebFetch tool to retrieve current documentation when:

- User asks about features not covered in knowledge/
- Schema or API has potentially changed
- Best practices need verification against latest docs
