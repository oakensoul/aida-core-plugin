---
type: guide
title: "How to Use Mementos"
description: "Step-by-step guide to saving and restoring session context"
audience: users
---

# How to Use Mementos

Mementos are context snapshots that help you resume work after `/clear`, `/compact`,
or in new sessions. They capture what you're working on, your approach, progress,
and next steps.

## Quick Start

```bash
# Save your current context
/aida memento create "Implementing OAuth flow"

# Later, restore it
/aida memento restore
```

## When to Use Mementos

Use mementos when:

- **Ending a session** - Save context before closing
- **Before /clear** - Preserve important context
- **Switching tasks** - Park current work to handle something else
- **Complex features** - Track progress across multiple sessions

## Commands

### Create a Memento

```bash
/aida memento create "description"
```

Saves the current session context with:

- Problem/goal you're working on
- Approach and decisions made
- Current progress
- Next steps

**Examples:**

```bash
/aida memento create "Adding user authentication with JWT"
/aida memento create "Debugging the payment webhook timeout"
/aida memento create "Refactoring database layer to use repository pattern"
```

### List Mementos

```bash
/aida memento list
```

Shows all saved mementos with their:

- Slug (identifier)
- Description
- Created date
- Status (active/completed)

### Restore a Memento

```bash
/aida memento restore
/aida memento restore auth-feature
```

Loads the memento context so Claude understands:

- What you were working on
- Where you left off
- What to do next

### Update a Memento

```bash
/aida memento update
```

Updates the active memento with current progress. Use this:

- At natural breakpoints
- When you've made significant progress
- Before taking a break

### Complete a Memento

```bash
/aida memento complete
```

Marks the memento as done. Use when:

- The feature is finished
- The bug is fixed
- The task is complete

### Remove a Memento

```bash
/aida memento remove auth-feature
```

Deletes a memento you no longer need.

## Memento Workflow

### Starting Work

```bash
# Beginning a new feature
/aida memento create "Building the user dashboard"
```

### During Work

```bash
# Made good progress, save checkpoint
/aida memento update

# Need to handle an interrupt
/aida memento create "Quick fix for login bug"
# ... fix the bug ...
/aida memento complete
/aida memento restore user-dashboard
```

### Ending a Session

```bash
# Before closing
/aida memento update

# Or if starting fresh tomorrow
/aida memento create "Dashboard - API integration complete, starting UI"
```

### Next Session

```bash
# Resume where you left off
/aida memento restore

# Claude will know your context and continue
```

## Memento Sources

When creating a memento, AIDA can pull context from different sources:

### Manual (Default)

You provide the description:

```bash
/aida memento create "Working on OAuth implementation"
```

### From PR

Extract context from current pull request:

```bash
/aida memento create --from-pr
```

Captures PR title, description, and changes.

### From Changes

Summarize current file changes:

```bash
/aida memento create --from-changes
```

Useful when you have uncommitted work to describe.

## Memento Storage

Mementos are stored in `~/.claude/memory/mementos/`:

```text
~/.claude/memory/mementos/
├── auth-feature.md
├── dashboard-ui.md
└── api-refactor.md
```

Each memento is a markdown file you can read or edit directly.

## Memento Format

```markdown
---
slug: auth-feature
description: Implementing JWT authentication
created: 2024-01-15T10:30:00Z
updated: 2024-01-15T14:45:00Z
status: active
---

# Auth Feature Implementation

## Problem

Users need to authenticate to access protected resources.

## Approach

Using JWT tokens with refresh token rotation:
- Access tokens: 15 minute expiry
- Refresh tokens: 7 day expiry
- Stored in httpOnly cookies

## Progress

- [x] Set up JWT library
- [x] Create login endpoint
- [x] Create refresh endpoint
- [ ] Add logout endpoint
- [ ] Implement token validation middleware

## Next Steps

1. Complete the logout endpoint
2. Add the auth middleware to protected routes
3. Write tests for token refresh flow

## Context

Key files:
- src/auth/jwt.ts - Token handling
- src/routes/auth.ts - Auth endpoints
- src/middleware/auth.ts - Protection middleware
```

## Best Practices

### Do

- Create mementos at session start for new work
- Update regularly during long sessions
- Use descriptive slugs and descriptions
- Complete mementos when work is done

### Don't

- Create too many active mementos (keep it focused)
- Forget to restore after /clear
- Let mementos get stale (update or complete them)

## Tips

### Quick Save Before /clear

```bash
/aida memento update
/clear
/aida memento restore
```

### Multiple Workstreams

```bash
# Park current work
/aida memento update

# Start new task
/aida memento create "Urgent bug fix"
# ... work on bug ...
/aida memento complete

# Resume original work
/aida memento restore feature-work
```

### Review Old Context

```bash
# See what you were doing
/aida memento list

# Read a specific memento without restoring
/aida memento read auth-feature
```

## Troubleshooting

### Memento not restoring properly?

- Check the memento file exists in `~/.claude/memory/mementos/`
- Verify the YAML frontmatter is valid
- Try reading it first: `/aida memento read [slug]`

### Lost context after /clear?

- If you created a memento before clearing, restore it
- If not, check git history or recent files for context
- Create a new memento from scratch

### Too many stale mementos?

```bash
/aida memento list
# Complete or remove old ones
/aida memento complete old-feature
/aida memento remove abandoned-task
```

## Next Steps

- [Create an Agent](HOWTO_CREATE_AGENT.md) - Build custom expertise
- [Create a Command](HOWTO_CREATE_COMMAND.md) - Define workflows
- [Getting Started](GETTING_STARTED.md) - Overview of AIDA features
