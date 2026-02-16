---
type: reference
title: Memento Format
description: Structure and best practices for AIDA mementos
---

# Memento Format

Mementos capture session context for later resumption. A good memento lets you
(or someone else) pick up exactly where you left off.

## File Location

```text
~/.claude/memento/{project}--{slug}.md
```

Filenames use a `{project}--{slug}` convention where `--` separates the
project name from the memento slug. Slugs are kebab-case, derived from
the description (e.g., "fix auth bug" in project "my-app" becomes
`my-app--fix-auth-bug.md`).

## Required Structure

```yaml
---
type: memento
slug: fix-auth-bug
description: Fixing authentication token expiry issue
created: 2024-01-15T10:30:00Z
status: active|completed
project:
  name: my-project
  path: /path/to/project
  repo: git@github.com:user/repo.git
  branch: feature/fix-auth-bug
issue: 123          # optional
pr: 456             # optional
---
```

## Required Sections

### Context

What was being worked on and why. Include:

- The problem or feature being addressed
- Why this work matters
- Any relevant background

### Current State

Where things stand right now:

- What's done
- What's in progress
- What's blocked

### Next Steps

Actionable items to continue:

```markdown
## Next Steps

- [ ] Implement token refresh logic
- [ ] Add unit tests for expiry handling
- [ ] Update API documentation
```

## Optional Sections

### Key Decisions

Important choices made and their rationale:

```markdown
## Key Decisions

- Using refresh tokens instead of longer expiry: Better security, industry standard
- Storing in httpOnly cookie: Prevents XSS access to tokens
```

### Blockers / Open Questions

Things that need resolution:

```markdown
## Blockers

- Need clarification on token lifetime from security team
- Waiting for API v2 endpoint to be deployed
```

### Files Modified

Quick reference to changed files:

```markdown
## Files Modified

- `src/auth/token.py` - Added refresh logic
- `tests/test_auth.py` - New expiry tests
- `docs/auth.md` - Updated flow diagram
```

### Session Notes

Anything helpful for resuming:

```markdown
## Session Notes

- The failing test on line 45 is expected until we merge the API changes
- Check Slack thread with @security for context on the token format decision
```

## Quality Checklist

A good memento:

- [ ] Has clear, specific description
- [ ] Explains context someone else could understand
- [ ] Lists concrete next steps (not vague todos)
- [ ] References specific files/lines when relevant
- [ ] Captures decisions and their reasoning
- [ ] Notes any blockers or dependencies

## Examples

### Good Memento

```markdown
## Context

Implementing rate limiting for the public API. Users have been hitting
endpoints too frequently, causing performance issues. Target: 100 req/min
per API key.

## Current State

- Redis-based counter is implemented and tested
- Middleware is written but not yet integrated
- Need to add response headers (X-RateLimit-*)

## Next Steps

- [ ] Integrate middleware in api/routes.py line 45
- [ ] Add X-RateLimit-Limit, X-RateLimit-Remaining headers
- [ ] Write integration test for rate limit exceeded (429)
- [ ] Update API docs with rate limit info
```

### Poor Memento

```markdown
## Context

Working on rate limiting.

## Next Steps

- Finish it
- Test it
```

The poor example lacks specifics - what's the limit? What's done? What exactly needs testing?
