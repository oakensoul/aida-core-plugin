---
type: reference
title: CLAUDE.md Files Guide
description: Understanding and creating effective CLAUDE.md project instructions
---

# CLAUDE.md Files

CLAUDE.md files provide project-specific instructions to Claude Code. They
customize Claude's behavior for a particular project or user environment.

## What is CLAUDE.md?

A CLAUDE.md file is a **project instruction file** that tells Claude:

- How this project is structured
- What conventions to follow
- What tools and commands to prefer
- What patterns and practices to use

Think of it as onboarding documentation for Claude - everything an AI assistant
needs to know to work effectively in this codebase.

## Location Hierarchy

CLAUDE.md files are loaded from multiple locations with layered precedence:

```text
Priority (highest to lowest):
1. .claude/CLAUDE.md         # Project-specific (current directory)
2. CLAUDE.md                 # Project root (current directory)
3. ~/.claude/CLAUDE.md       # User global preferences
4. ~/CLAUDE.md               # User home directory
```

Lower priority files are loaded first, higher priority files override them.

### When to Use Each Location

| Location | Use Case |
|----------|----------|
| `./CLAUDE.md` | Project instructions, checked into repo |
| `./.claude/CLAUDE.md` | Project instructions, may be gitignored |
| `~/.claude/CLAUDE.md` | Personal global preferences |
| `~/CLAUDE.md` | User-wide defaults |

## Content Guidelines

### What to Include

#### Project Context

```markdown
# Project Name

Brief description of what this project does.

## Tech Stack
- Language: TypeScript
- Framework: Next.js 14
- Database: PostgreSQL
- Testing: Jest + React Testing Library
```

#### Coding Conventions

```markdown
## Code Style

- Use functional components with hooks
- Prefer named exports over default exports
- Use absolute imports from `@/`
- Keep components under 200 lines
```

#### File Structure

```markdown
## Project Structure

- `src/components/` - React components
- `src/lib/` - Utility functions
- `src/api/` - API route handlers
- `src/types/` - TypeScript type definitions
```

#### Workflow Preferences

```markdown
## Development Workflow

- Run `npm run dev` for development server
- Run `npm test` before committing
- Use conventional commits (feat:, fix:, docs:)
```

#### Tool Preferences

```markdown
## Tools

- Use pnpm (not npm or yarn)
- Format with Prettier (`.prettierrc` in root)
- Lint with ESLint (`npm run lint`)
```

### What NOT to Include

#### Secrets and Credentials

```markdown
# BAD - Never include secrets
API_KEY=sk-abc123
DATABASE_URL=postgres://user:pass@host/db
```

#### User-Specific Paths

```markdown
# BAD - Hardcoded user paths
Project is at /Users/john/projects/my-app

# GOOD - Use relative paths or ~ expansion
Project root: ./ or ~/projects/my-app
```

#### Temporary Notes

```markdown
# BAD - Temporary debugging notes
TODO: Fix the bug in auth.js line 42
Remember to revert the console.log on line 15
```

#### Excessive Detail

```markdown
# BAD - Too much detail
Every function should have JSDoc comments with:
- @param for each parameter with type and description
- @returns with type and description
- @example with at least 2 examples
- @throws for any possible exceptions
- @see for related functions
[... 50 more lines of excessive requirements ...]
```

## Effective CLAUDE.md Patterns

### Minimal but Complete

Start with essentials, add as needed:

```markdown
# MyProject

TypeScript/React app for [purpose].

## Key Commands
- `npm run dev` - Development
- `npm test` - Tests
- `npm run build` - Production build

## Conventions
- Functional components with hooks
- Use `@/` for absolute imports
- Tests colocated with components (`Component.test.tsx`)
```

### Organized by Topic

Group related instructions:

```markdown
# Project Name

## Overview
[Brief description]

## Development
[How to run, test, build]

## Code Style
[Conventions and patterns]

## Architecture
[Structure and patterns]

## Common Tasks
[Frequent operations]
```

### Progressive Complexity

Start simple, expand as project grows:

```markdown
# Phase 1: Basic
- Tech stack
- Key commands
- File structure

# Phase 2: Growing
- Coding conventions
- Testing approach
- PR process

# Phase 3: Mature
- Architecture decisions
- Performance guidelines
- Security considerations
```

## Examples

### Simple Web App

```markdown
# MyBlog

Personal blog built with Next.js and MDX.

## Commands
- `pnpm dev` - Start dev server
- `pnpm build` - Build for production
- `pnpm test` - Run tests

## Structure
- `posts/` - MDX blog posts
- `src/components/` - React components
- `src/lib/` - Utilities

## Style
- Use Tailwind for styling
- Components in PascalCase
- Keep posts metadata in frontmatter
```

### API Service

```markdown
# PaymentAPI

REST API for payment processing.

## Tech
- Node.js + Express
- PostgreSQL + Prisma
- Jest for testing

## Development
- `npm run dev` - Start with hot reload
- `npm run db:migrate` - Run migrations
- `npm run db:seed` - Seed test data

## Conventions
- Controllers in `src/controllers/`
- Services in `src/services/`
- Validation with Zod schemas
- Error responses follow RFC 7807

## Security
- All endpoints require authentication
- Input validation required
- SQL injection prevention via Prisma
```

### Monorepo

```markdown
# MyMonorepo

Turborepo monorepo with multiple packages.

## Packages
- `apps/web` - Next.js frontend
- `apps/api` - Express backend
- `packages/ui` - Shared components
- `packages/utils` - Shared utilities

## Commands
- `pnpm dev` - Run all apps
- `pnpm build` - Build all packages
- `pnpm test` - Test all packages
- `pnpm --filter web dev` - Run specific app

## Conventions
- Changes to `packages/` require updating dependents
- Use workspace protocol for internal deps
- Keep package versions in sync
```

## Maintenance

### When to Update

Update CLAUDE.md when:

- Tech stack changes (new framework, new tool)
- Conventions evolve (new patterns adopted)
- Structure changes (refactored directories)
- New team members struggle (add missing context)

### Review Checklist

Periodically verify:

- [ ] Commands still work
- [ ] File paths are accurate
- [ ] Conventions match reality
- [ ] No stale information
- [ ] No secrets leaked

### Version Control

- Check CLAUDE.md into version control
- Review changes in PRs
- Keep history of convention changes
- Use blame to understand evolution

## Troubleshooting

### Claude Ignores Instructions

**Possible causes:**

1. File not in expected location
2. Syntax errors in markdown
3. Instructions too vague
4. Conflicting instructions from multiple files

**Solution:** Check file location, validate markdown, be specific.

### Instructions Too Long

**Problem:** CLAUDE.md is thousands of lines.

**Solution:**

- Focus on essentials
- Link to external docs for details
- Use bullet points, not paragraphs
- Remove outdated information

### Conflicting Files

**Problem:** User and project CLAUDE.md conflict.

**Solution:**

- Project file wins for project-specific settings
- User file for personal preferences
- Keep them non-overlapping where possible

