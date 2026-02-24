---
type: issue
issue: 31
title: "refactor: decompose claude-code-management into entity-focused manager skills"
status: "In Progress"
branch: "milestone-v1.0/refactor/31-decompose-management"
worktree: "issue-31-decompose-management"
started: "2026-02-24"
created: "2026-02-24"
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/31"
assignee: "@me"
---

# Issue #31: Decompose claude-code-management into entity-focused manager skills

**Status**: In Progress
**Labels**: enhancement
**Milestone**: 1.0.0
**Assignees**: oakensoul

## Description

Decompose the monolith `claude-code-management` skill into entity-focused
manager skills. Currently `aida` routes to `claude-code-management` as a
middleman which then dispatches internally -- three layers of indirection.

### Target Architecture

```text
/aida agent [create|validate|version|list]      → agent-manager skill
/aida skill [create|validate|version|list]       → skill-manager skill
/aida plugin [scaffold|create|validate|...]      → plugin-manager skill
/aida hook [list|add|remove|validate]            → hook-manager skill
/aida claude [create|optimize|validate|list]     → claude-md-manager skill
/aida marketplace [scaffold|validate|list|...]   → marketplace-manager skill
```

### Key Decisions Needed

- Naming convention: `*-manager` vs alternatives
- Shared utilities: keep `scripts/shared/utils.py`
- Template organization: per-manager or shared library
- Plugin manager scope: merge `create-plugin` scaffolding + existing ops
- Skill naming: `skills/skill-manager/` manages skills -- confusing?

## Work Tracking

- Branch: `milestone-v1.0/refactor/31-decompose-management`
- Worktree: `issue-31-decompose-management`
- Started: 2026-02-24
- Work directory: `.issues/in-progress/issue-31/`

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/31)
- Issue #23 / PR #30 - Plugin scaffolding (exposed the inconsistency)

## Notes

Add your work notes here...
