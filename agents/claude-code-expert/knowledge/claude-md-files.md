---
type: reference
title: CLAUDE.md Memory Files Guide
description: Understanding Claude Code memory files for persistent context and instructions
---

# CLAUDE.md Memory Files

CLAUDE.md files are **memory files** - persistent context that Claude loads at
startup. They provide instructions, conventions, and context that shape Claude's
behavior for a project or user.

## Memory vs Settings

Claude Code has two configuration systems:

| Aspect | CLAUDE.md (Memory) | settings.json (Settings) |
| ------ | ------------------ | ------------------------ |
| **Format** | Markdown | JSON |
| **Purpose** | Instructions & context | Behavior configuration |
| **Contains** | Conventions, patterns, workflows | Permissions, hooks, model |
| **Analogy** | Onboarding docs | App preferences |

**Use CLAUDE.md for:** What Claude SHOULD do (conventions, patterns, context)
**Use settings.json for:** What Claude CAN do (permissions, tools, model)

See: `settings.md` for settings.json configuration.

## Memory File Hierarchy

Claude Code loads memory from four hierarchical levels:

```text
Priority (highest to lowest):
1. Enterprise Policy     # Organization-wide (managed)
2. Project Memory        # Team-shared (.claude/CLAUDE.md or ./CLAUDE.md)
3. User Memory           # Personal (~/.claude/CLAUDE.md)
4. Parent Directories    # Recursively discovered upward
```

### Location Details

| Level | Location | Scope |
| ----- | -------- | ----- |
| Enterprise | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Organization |
| Enterprise | `/etc/claude-code/CLAUDE.md` (Linux) | Organization |
| Enterprise | `C:\ProgramData\ClaudeCode\CLAUDE.md` (Windows) | Organization |
| Project | `./.claude/CLAUDE.md` or `./CLAUDE.md` | Team/Project |
| User | `~/.claude/CLAUDE.md` | Personal global |

### How Memory Loads

Claude automatically discovers memory files by:

1. Recursing **upward** from the current working directory
2. Recursing **downward** through subtrees
3. Merging all discovered files with hierarchy precedence

Use `/memory` command to see all loaded memory files.

## Working with Memory

### Viewing Memory

The `/memory` command shows all loaded memory files:

```text
/memory
```

Output shows:

```text
Memory files · /memory
└ User (~/.claude/CLAUDE.md): 43 tokens
└ Project (./CLAUDE.md): 282 tokens
```

### Editing Memory

Open any memory file in your system editor:

```text
/memory
```

Then select which file to edit.

### Quick Addition

Start your input with `#` to quickly add to memory:

```text
# Always use TypeScript strict mode
```

Claude will prompt you to select which memory file to store it in.

## Import System

Memory files support imports using `@path/to/file` syntax:

```markdown
# Project Memory

## Shared Context
@docs/architecture.md
@docs/conventions.md

## Team Standards
- Use TypeScript
- Follow ESLint rules
```

### Import Rules

- Imports are evaluated recursively (max depth: 5)
- Paths are relative to the memory file location
- Imports inside code blocks are ignored (prevents collisions)
- Circular imports are detected and prevented

### Import Use Cases

**Split large memory into modules:**

```markdown
# CLAUDE.md
@.claude/architecture.md
@.claude/conventions.md
@.claude/workflows.md
```

**Include documentation as context:**

```markdown
# CLAUDE.md
## API Reference
@docs/api/endpoints.md
```

## Content Guidelines

### What to Include

**Project Context:**

```markdown
# ProjectName

Brief description of what this project does.

## Tech Stack
- Language: TypeScript
- Framework: Next.js 14
- Database: PostgreSQL
```

**Coding Conventions:**

```markdown
## Code Style
- Use functional components with hooks
- Prefer named exports over default exports
- Use absolute imports from `@/`
```

**Workflow Preferences:**

```markdown
## Development
- Run `npm run dev` for development
- Run `npm test` before committing
- Use conventional commits
```

**Frequently Used Commands:**

```markdown
## Commands
- `make lint` - Run all linters
- `make test` - Run tests
- `make build` - Production build
```

### What NOT to Include

- **Secrets/credentials** - Use environment variables
- **Absolute user paths** - Use `~` or relative paths
- **Temporary notes** - Keep memory clean
- **Excessive detail** - Be concise, link to docs

### Structure Best Practices

- Use bullet points under descriptive markdown headings
- Be specific rather than generic
- Review periodically as projects evolve
- Keep files focused and organized

## Examples

### Minimal Project Memory

```markdown
# MyProject

TypeScript/React app for task management.

## Commands
- `pnpm dev` - Development server
- `pnpm test` - Run tests
- `pnpm build` - Production build

## Conventions
- Functional components with hooks
- Use `@/` for absolute imports
- Tests colocated with components
```

### User Memory (Global Preferences)

```markdown
# My Preferences

## Coding Style
- Always use TypeScript strict mode
- Prefer explicit types over inference
- Use early returns to reduce nesting

## Communication
- Be concise in explanations
- Show code examples when explaining
- Ask before making large changes

## Tools
- Use pnpm over npm/yarn
- Prefer make targets over npm scripts
```

### Enterprise Memory

```markdown
# Company Standards

## Security
- Never commit secrets
- All APIs require authentication
- Input validation required

## Code Review
- All changes require PR review
- Tests required for new features
- Documentation required for APIs

## Compliance
- PII must be encrypted
- Audit logging required
- Follow data retention policies
```

## Multi-File Organization

For complex projects, split memory into focused files:

```text
.claude/
├── CLAUDE.md           # Main memory (imports others)
├── architecture.md     # System architecture
├── conventions.md      # Coding standards
├── workflows.md        # Development workflows
└── team.md             # Team practices
```

**Main CLAUDE.md:**

```markdown
# ProjectName

@.claude/architecture.md
@.claude/conventions.md
@.claude/workflows.md
```

## Troubleshooting

### Memory Not Loading

**Check location:** Use `/memory` to see what's loaded.

**Check syntax:** Ensure valid markdown.

**Check imports:** Verify import paths exist.

### Conflicting Instructions

**Higher precedence wins:** Enterprise > Project > User

**Be specific:** More specific instructions override general ones.

**Separate concerns:**

- User memory: Personal preferences
- Project memory: Team conventions

### Memory Too Large

**Symptoms:** Slow startup, context overflow

**Solutions:**

- Split into imported modules
- Remove outdated content
- Link to external docs instead of including
- Focus on essentials

### Instructions Ignored

**Be specific:** "Use TypeScript" is better than "Follow best practices"

**Use examples:**

```markdown
## Import Style

GOOD:
import { useState } from 'react';

BAD:
import React from 'react';
const { useState } = React;
```

## Integration with Context Layering

Memory files (CLAUDE.md) are part of the broader context system:

```text
┌─────────────────────────────────────────────────────┐
│  5. Conversation Context                            │
│     Current task & discussion                       │
├─────────────────────────────────────────────────────┤
│  4. Extension Context                               │
│     Active skill/subagent + knowledge                │
├─────────────────────────────────────────────────────┤
│  3. Project Memory  ─┐                              │
│     ./CLAUDE.md      │ "Memory files"               │
├──────────────────────┤ Always loaded                │
│  2. User Memory     ─┘                              │
│     ~/.claude/CLAUDE.md                             │
├─────────────────────────────────────────────────────┤
│  1. Base Claude                                     │
│     Core capabilities                               │
└─────────────────────────────────────────────────────┘
```

See: `framework-design-principles.md` for complete context layering details.
