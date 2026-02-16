---
type: reference
title: "Team Prompt: Issue #3 - Move Memento Storage to User-Level"
---

# Team Prompt: Issue #3 - Move Memento Storage to User-Level

## How to Use

Paste the prompt below into a new Claude Code conversation from the working
directory:

```
/Users/oakensoul/Developer/oakensoul/aida-publishing/aida-core-plugin/issue-3-memento-user-level-storage
```

---

## Prompt

```
Implement GitHub issue #3: Move memento storage from project-level to user-level.

Read the implementation plan at:
.issues/in-progress/issue-3-memento-user-level-storage/PLAN.md

Then read GitHub issue #3 for full requirements:
gh issue view 3

## Team Setup

Create a team called "issue-3-memento" with 4 members:

### 1. lead (you)
- Orchestrate the team
- Implement Phase 1: Core Python logic in `skills/memento/scripts/memento.py`
- Perform code reviews after each phase before the next phase starts
- Run final verification (`make lint && make test` + grep audit)

### 2. template-worker (general-purpose agent)
- Phase 2: Update both Jinja2 templates to add `project:` frontmatter block
  - `skills/memento/templates/work-session.md.jinja2`
  - `skills/memento/templates/freeform.md.jinja2`
- Phase 4 (docs): Update 3 documentation files:
  - `skills/memento/SKILL.md`
  - `skills/memento/references/memento-workflow.md`
  - `agents/aida/knowledge/memento-format.md`
- Can start Phase 2 templates while lead finishes Phase 1
- Wait for lead's review approval before starting Phase 4 docs

### 3. test-worker (general-purpose agent)
- Phase 3: Update `tests/unit/test_memento.py`
- Add new test classes: TestMementoFilename, TestNestedFrontmatter,
  TestProjectContext, TestListFiltering
- Update existing tests to mock user-level paths
- Must wait until Phase 1 is approved before starting
- Run `pytest tests/unit/test_memento.py -v` to verify

### 4. docs-worker (general-purpose agent)
- Phase 4 (docs): Update 2 documentation files:
  - `agents/aida/knowledge/troubleshooting.md`
  - `skills/aida-dispatch/SKILL.md`
- Must wait until Phase 1 is approved before starting
- Can work in parallel with template-worker's Phase 4 docs

## Workflow

1. Lead implements Phase 1 (core Python logic)
2. Template-worker starts Phase 2 (templates) in parallel with Phase 1
3. Lead reviews Phase 1 + Phase 2 when both complete
4. After Phase 1 approved: test-worker starts Phase 3, docs-worker and
   template-worker start Phase 4 docs (all in parallel)
5. Lead reviews Phase 3 tests
6. Lead does final review: `make lint && make test` + grep audit for stale refs
7. Report results and shut down team

## Code Review Protocol

After each phase, the lead must review the changes:
- Read the modified files
- Check for correctness, edge cases, consistency
- Verify no stale references to old paths/functions
- Run relevant linters
- Send approval or feedback to the worker

## Key Constraints

- No migration of old files - clean break
- Storage: `~/.claude/memento/` (active), `~/.claude/memento/.completed/`
- Filenames: `{project}--{slug}.md` (double-hyphen separator)
- Slug validation already prevents double-hyphens, making `--` safe
- `parse_frontmatter()` must handle nested YAML blocks (one level deep)
- Tests must mock paths - never touch actual `~/.claude/memento/`
- All linters must pass: `make lint`
- All tests must pass: `make test`

## Acceptance Criteria

- [ ] Mementos stored at `~/.claude/memento/`
- [ ] Filenames use `{project}--{slug}.md` pattern
- [ ] Project context auto-detected and saved in frontmatter
- [ ] List defaults to current project; supports `--all` and `--project`
- [ ] All linters pass (`make lint`)
- [ ] All tests pass (`make test`)
- [ ] No stale path references in codebase
- [ ] Code reviewed at each phase boundary
```

---

## Summary of Team Members to Configure

| Name | Agent Type | Subagent Type | Why |
|------|-----------|---------------|-----|
| lead | Team lead (you) | N/A (the lead) | Orchestrates, writes core logic, reviews |
| template-worker | Teammate | `general-purpose` | Needs file editing for templates + docs |
| test-worker | Teammate | `general-purpose` | Needs file editing + bash for pytest |
| docs-worker | Teammate | `general-purpose` | Needs file editing for markdown docs |
