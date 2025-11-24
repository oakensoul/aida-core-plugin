---
name: project-context
description: Provides current project state, architecture overview, and structured metadata
version: 0.1.0
author: aida-core
tags:
  - project
  - context
  - architecture
  - metadata
---

# Project Context Skill

This skill provides comprehensive context about the current project, including its state, architecture, recent decisions, and structured metadata for programmatic access.

## When to Use

This skill should be invoked when you need to:

- Understand the current state of the project (what's being worked on, recent decisions)
- Review the project's architecture and technical stack
- Access structured metadata about the project (commands, tools, framework)
- Get context about the project's focus areas and active development
- Reference project-specific conventions or patterns

The skill uses progressive disclosure - supporting files are only loaded when the skill is invoked, keeping token usage efficient.

## Supporting Files

### context.md
Current state of the project:
- Project description and purpose
- Current focus and active work
- Recent decisions with rationale
- Active development areas
- Updated dynamically as the project evolves

### architecture.md
Technical architecture overview:
- Technology stack (languages, frameworks, tools)
- Architecture patterns and principles
- Key components and their relationships
- Dependencies and integrations
- Infrastructure and deployment notes

### metadata.json
Structured data for programmatic access:
- Project type and classification
- Primary language and framework
- Available commands (build, test, dev, lint, etc.)
- Tool ecosystem
- Documentation locations
- AIDA configuration metadata

## Examples

### Getting Project Overview
```
User: "What's this project about and what are we currently working on?"

Claude: *Invokes project-context skill, reads context.md*
"This is a [project description]. We're currently focused on [current focus].
Recent decisions include [decisions]..."
```

### Understanding Architecture
```
User: "How is this application structured?"

Claude: *Invokes project-context skill, reads architecture.md*
"The application uses [framework] with [language]. The architecture follows [patterns]..."
```

### Accessing Commands Programmatically
```
User: "How do I run the tests?"

Claude: *Invokes project-context skill, reads metadata.json*
"Run: npm test"
```

## Progressive Disclosure

This skill's SKILL.md is always available (small token footprint), but supporting files (context.md, architecture.md, metadata.json) are only loaded when Claude determines the skill is relevant to the current conversation.

This ensures:
- Efficient token usage across multiple projects
- Context is available when needed
- No token budget explosion
- Scales to many projects

## Maintenance

Team members should update these files as the project evolves:
- **context.md** - Update current focus and decisions regularly
- **architecture.md** - Update when architecture changes
- **metadata.json** - Update when commands or tools change

Files are committed to version control and shared across the team.
