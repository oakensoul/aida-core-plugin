---
type: issue
issue: 27
title: "Plugin upgrade: /aida plugin update should migrate existing plugins to current standards"
status: "In Progress"
branch: "milestone-v1.0/feature/27-plugin-update"
worktree: "issue-27-plugin-update"
started: "2026-02-24"
created: "2026-02-16"
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/27"
assignee: "@me"
---

# Issue #27: Plugin upgrade - /aida plugin update

**Status**: In Progress
**Labels**: (none)
**Milestone**: 1.0.0
**Assignees**: oakensoul

## Description

Add `/aida plugin update` as a standards migration tool for existing
plugins. As AIDA plugin standards evolve (new linting configs, updated
Makefile targets, CI workflows, new required files), existing plugins
fall behind with no automated way to catch up.

### Key Design Principles

- **Detect-and-patch**, not generate-from-scratch
- Respect custom content in CLAUDE.md, README.md, aida-config.json
- Non-destructive patching of boilerplate (Makefile, .gitignore,
  linting configs, CI)
- Version-aware migrations (apply delta between scaffolded version
  and current standards)
- Merge strategy similar to package managers (overwrite, skip, merge)

### Proposed Behavior

1. Scan current plugin directory against latest scaffolding standards
2. Identify gaps: missing files, outdated configs, deprecated patterns
3. Generate diff report (current vs needs attention)
4. Offer to patch non-destructively:
   - Add missing files
   - Merge new Makefile targets
   - Update CI workflows
   - Preserve custom content
5. Handle version-aware migrations (e.g., v0.7 -> v0.9 delta)
6. Produce summary of changes made and manual steps remaining

## Work Tracking

- Branch: `milestone-v1.0/feature/27-plugin-update`
- Worktree: `issue-27-plugin-update`
- Started: 2026-02-24
- Work directory: `.issues/in-progress/issue-27/`

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/27)
- Issue #23 / PR #30 - Plugin scaffolding (defines the standards)
- Issue #31 / PR #32 - Decomposition (plugin-manager owns this)

## Notes

This feature lives in `skills/plugin-manager/` as a new operation
alongside scaffold, create, validate, version, and list.
