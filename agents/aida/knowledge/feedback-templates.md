---
type: reference
title: Feedback Templates
description: Templates for bug reports, feature requests, and feedback
---

# Feedback Templates

How to structure issues for the AIDA repository.

## Bug Report Template

### Title Format

```text
[Bug] Brief description of the issue
```

### Body Structure

```markdown
## Description

Clear, concise description of the bug.

## Steps to Reproduce

1. Step one
2. Step two
3. Step three

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Environment

- AIDA Version: X.Y.Z
- Claude Code Version: X.Y.Z
- OS: macOS / Linux / Windows
- Python Version: X.Y.Z

## Additional Context

- Error messages (full text)
- Relevant log output
- Screenshots if applicable

## Possible Cause

(Optional) If you have insight into what might be causing this.
```

### Labels

- `bug`
- `needs-triage`
- Priority: `priority:high` / `priority:medium` / `priority:low`

## Feature Request Template

### Title Format

```text
[Feature] Brief description of the feature
```

### Body Structure

```markdown
## Summary

One-paragraph description of the feature.

## Use Case

Why do you need this? What problem does it solve?

## Proposed Solution

How do you envision this working?

## Alternatives Considered

What other approaches did you consider?

## Additional Context

- Related features or issues
- Examples from other tools
- Mockups or diagrams
```

### Labels

- `enhancement`
- `needs-triage`
- Scope: `scope:small` / `scope:medium` / `scope:large`

## General Feedback Template

### Title Format

```text
[Feedback] Topic of feedback
```

### Body Structure

```markdown
## Category

- [ ] Usability
- [ ] Documentation
- [ ] Performance
- [ ] Developer Experience
- [ ] Other

## Feedback

Your feedback here.

## Suggestions

(Optional) Ideas for improvement.

## Context

How you're using AIDA (what workflows, what projects).
```

### Labels

- `feedback`
- Category-specific label

## Sanitization Guidelines

Before submitting, remove or redact:

### Always Remove

- API keys and tokens
- Passwords and secrets
- Personal email addresses
- Private repository URLs
- Internal hostnames/IPs
- File paths containing usernames (replace with `~` or `$HOME`)

### Replace With Placeholders

```text
# Bad
/Users/johnsmith/projects/secret-project

# Good
~/projects/[project]
```

```text
# Bad
Authorization: Bearer sk-1234567890abcdef

# Good
Authorization: Bearer [REDACTED]
```

### Keep (Usually Safe)

- AIDA version numbers
- Claude Code version
- OS and Python versions
- Error messages (check for embedded secrets)
- File names (if not sensitive)
- Public repository URLs

## Quality Checklist

Before submitting:

- [ ] Title clearly describes the issue/request
- [ ] All relevant sections filled out
- [ ] Steps to reproduce are specific and complete (for bugs)
- [ ] No sensitive information included
- [ ] Appropriate labels suggested
- [ ] Checked for existing similar issues

## Examples

### Good Bug Report Title

```text
[Bug] /aida config fails when project has spaces in path
```

### Poor Bug Report Title

```text
[Bug] It doesn't work
```

### Good Feature Request

```text
[Feature] Add memento templates for common workflows
```

### Poor Feature Request

```text
[Feature] Make it better
```
