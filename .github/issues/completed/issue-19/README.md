---
issue: 19
title: "Merge Commands into Skills - align with Anthropic's upstream changes"
status: "COMPLETED"
created: "2026-02-23"
completed: "2026-02-23"
pr: 21
actual_effort: 4
estimated_effort: 4
---

# Issue #19: Merge Commands into Skills - align with Anthropic's upstream changes

**Status**: COMPLETED
**Labels**: enhancement
**Milestone**: 0.8.0
**Assignees**: oakensoul

## Description

Anthropic has merged the "Commands" extension type into "Skills" in Claude Code.
Our plugin currently maintains Commands as a separate extension type (WHAT)
distinct from Skills (HOW), with a `commands/` directory and extensive knowledge
documentation describing the two-tier model.

This issue covers investigating the upstream changes, updating our framework
taxonomy, migrating `commands/aida.md` to a skill, and updating all knowledge
docs and references.

## Requirements

### Investigation

- [x] Confirm the upstream change: verify Commands are fully merged into Skills
      in Claude Code's current release
- [x] Document new skill frontmatter fields that replace command functionality
      (`user-invocable`, `disable-model-invocation`, `argument-hint`, etc.)
- [x] Determine if `commands/` directories are still recognized at all by Claude
      Code, or if they're completely deprecated
- [x] Check if plugin structure (`commands/` in plugins) is still supported

### Migration

- [x] Migrate `commands/aida.md` to a skill - create `skills/aida/SKILL.md`
- [x] Remove `commands/` directory after migration
- [x] Update skill frontmatter to use new fields where appropriate
      (`user-invocable: true`, `argument-hint`, etc.)

### Knowledge & Documentation Updates

- [x] Rewrite `agents/claude-code-expert/knowledge/extension-types.md`
- [x] Update `agents/claude-code-expert/knowledge/framework-design-principles.md`
- [x] Update `skills/claude-code-management/` CRUD operations
- [x] Update project `CLAUDE.md`
- [x] Update `.claude-plugin/plugin.json` if needed

### Downstream Impact

- [x] Check other AIDA plugins/projects that reference the Command type
- [x] Update templates in `skills/claude-code-management/templates/`

## Resolution

**Completed**: 2026-02-23

### Changes Made

- Migrated `commands/aida.md` to `skills/aida/SKILL.md` with `user-invocable: true`
- Removed `commands/` directory and command template
- Updated `.frontmatter-schema.json`: removed `command` type, added skill fields
- Removed `command` from `COMPONENT_TYPES` in Python extension management
- Rewrote all knowledge docs (extension-types, framework-design-principles,
  design-patterns, plugin-development, hooks, claude-md-files)
- Updated all user-facing docs (HOWTO guides, Getting Started, Install Guide,
  Development Guide, Examples, Architecture)
- Updated C4 diagrams (merged Commands container into Skills)
- Updated CI workflow, CODEOWNERS, integration tests
- Fixed agent model frontmatter (`claude-sonnet-4.5` -> `sonnet`)
- Added negative tests for command type rejection (512 tests passing)

### Implementation Details

- Chose to create `skills/aida/SKILL.md` as a thin redirect skill rather than
  merging into `aida-dispatch`, keeping the entry point separate from routing
- Used `user-invocable: true`, `allowed-tools: "*"`, and `argument-hint` as
  the new frontmatter fields that replace command functionality
- Three rounds of code review (system-architect, tech-lead, claude-code-expert)
  caught stragglers across CI, integration tests, and docs

### Notes

- `commands/` directories still work in Claude Code (backwards compatible) but
  skills are the recommended approach going forward
- The `model` field in agent frontmatter must use short aliases (`sonnet`,
  `opus`, `haiku`) not full model IDs

## Work Tracking

- Branch: `milestone-v0.8.0/feature/19-merge-commands-into-skills`
- Started: 2026-02-23
- Completed: 2026-02-23
- Work directory: `issues/in-progress/issue-19/`

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/19)
