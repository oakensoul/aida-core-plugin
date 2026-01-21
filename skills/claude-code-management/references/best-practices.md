---
type: reference
title: CLAUDE.md Best Practices
description: Guidelines for creating effective CLAUDE.md files
---

# CLAUDE.md Best Practices

This guide provides best practices for creating effective CLAUDE.md files that help
Claude Code understand and work with your project.

## Purpose

CLAUDE.md files provide project-specific guidance to Claude Code. They should:

- Help Claude understand the project's purpose and structure
- Provide common commands and workflows
- Document important constraints and conventions
- Reduce repetitive explanations in conversations

## Recommended Sections

### Required Sections

1. **Project Overview** - Brief description of what the project does
2. **Key Commands** - Most commonly used commands (build, test, run)

### Recommended Sections

1. **Architecture** - High-level structure and key components
2. **Coding Conventions** - Style guide, patterns to follow
3. **Important Constraints** - Things Claude should always consider

### Optional Sections

1. **Testing Guidelines** - How to run tests, coverage expectations
2. **Deployment Notes** - CI/CD, environment specifics
3. **Project Agents** - Custom agents for this project

## Content Guidelines

### Be Specific, Not Generic

#### Bad Example

```markdown
## Commands
Run the usual development commands.
```

#### Good Example

```markdown
## Key Commands

\`\`\`bash
make dev          # Start Flask dev server on port 5000
make test         # Run pytest with coverage
make lint         # Run black + flake8
make docker-up    # Start all services with Docker
\`\`\`
```

### Focus on What's Unique

Don't repeat what Claude already knows. Focus on:

- Project-specific patterns
- Non-obvious workflows
- Important constraints
- Custom conventions

### Keep It Current

Outdated CLAUDE.md files are worse than none. Include:

- Commands that actually work
- Paths that actually exist
- Dependencies that are installed

### Use Concrete Examples

```markdown
## API Pattern

All API endpoints follow this pattern:

\`\`\`python
@router.get("/items/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404)
    return item
\`\`\`
```

## Length Guidelines

| Project Size | Recommended Length |
| --- | --- |
| Small (< 10 files) | 50-150 lines |
| Medium (10-100 files) | 150-300 lines |
| Large (> 100 files) | 300-500 lines |

Longer files should be split into sections that can be loaded on demand.

## Hierarchy Usage

### Project Level (./CLAUDE.md)

- Project-specific commands
- Architecture decisions
- Team conventions
- Deployment notes

### User Level (~/.claude/CLAUDE.md)

- Personal preferences
- Default behaviors
- Cross-project patterns
- Editor/tool preferences

### Plugin Level

- Plugin-specific guidance
- Extension points
- Configuration options

## Validation Checklist

### Structure

- [ ] Has frontmatter with type and title
- [ ] Has Project Overview section
- [ ] Has Key Commands section
- [ ] Sections are properly formatted

### Content Quality

- [ ] Commands are accurate and work
- [ ] Paths reference real files/directories
- [ ] No sensitive data (passwords, keys)
- [ ] No outdated information

### Best Practices

- [ ] Under 500 lines (or split logically)
- [ ] Specific rather than generic
- [ ] Uses code blocks with language tags
- [ ] Explains why, not just what

## Common Mistakes

### Mistake 1: Too Generic

```markdown
## Overview
This is a web application.
```

**Better approach:**

```markdown
## Overview
REST API for inventory management built with FastAPI and PostgreSQL.
Handles ~50k requests/day with sub-100ms response times.
```

### Mistake 2: Outdated Commands

```markdown
## Commands
npm run dev  # This was renamed to npm start months ago
```

**Better approach:**

```markdown
## Commands
npm start    # Start development server (previously npm run dev)
```

### Mistake 3: Missing Context

```markdown
## Testing
Run the tests.
```

**Better approach:**

```markdown
## Testing

\`\`\`bash
pytest tests/                    # All tests
pytest tests/unit/               # Unit tests only (~2 min)
pytest tests/integration/ -x     # Integration tests, stop on first failure
pytest --cov=src tests/          # With coverage report
\`\`\`

Note: Integration tests require `docker-compose up -d` first.
```

## Template

```markdown
---
type: documentation
title: Project Name - CLAUDE.md
description: Claude Code configuration for this repository
---

# CLAUDE.md

Brief project description (1-2 sentences).

## Project Overview

What this project does and its main purpose.

**Type:** Web application / CLI / Library
**Languages:** Python, JavaScript
**Key Technologies:** FastAPI, React, PostgreSQL

## Key Commands

\`\`\`bash
make dev      # Start development
make test     # Run tests
make lint     # Check code style
make build    # Build for production
\`\`\`

## Architecture

High-level structure and key components.

## Coding Conventions

Style guide and patterns to follow.

## Important Constraints

Critical things to always consider.
```
