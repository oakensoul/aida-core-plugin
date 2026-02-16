---
type: reference
title: "Team Prompt for Issue #4: Plugin Config Discovery & Permissions Management"
---

# Team Prompt for Issue #4: Plugin Config Discovery & Permissions Management

## How to Use

Copy the **Team Kickoff Prompt** below into a new Claude Code session. Use
`/team` or spawn the team manually with the agent definitions listed.

---

## Team Members

| Name | Agent Type | Role |
|------|-----------|------|
| `lead` | general-purpose | Orchestrates work, handles shared files (schemas, plugin.json, docs), integration |
| `config-dev` | general-purpose | Part 1: Plugin config discovery (utils/plugins.py + configure.py) |
| `permissions-dev` | general-purpose | Part 2: Permissions skill (new skills/permissions/ directory) |
| `reviewer` | code-reviewer | Code reviews at each phase gate |
| `qa` | qa-engineer | Test development and final validation |

---

## Team Kickoff Prompt

```
Implement GitHub Issue #4: Plugin Configuration Discovery and Permissions Management
for the aida-core-plugin project.

## Plan

Read the implementation plan at:
.issues/in-progress/issue-4-plugin-config-and-permissions/team-prompt.md
and the detailed plan at:
~/.claude/plans/resilient-painting-cocke.md

## Issue

The full issue is on GitHub: `gh issue view 4`

## Summary

Two features for `/aida config`:

1. **Config Discovery** - Plugins declare `config` in `.claude-plugin/plugin.json`.
   `/aida config` scans installed plugins, presents a multi-select checklist of
   available configs, asks follow-up preference questions, and saves results to
   `aida-project-context.yml` under a `plugins:` key.

2. **Permissions Management** - Plugins declare `recommendedPermissions` in
   `plugin.json`. A new `skills/permissions/` skill provides `/aida config permissions`
   which scans plugins, aggregates permission categories, presents interactive
   allow/ask/deny choices, and writes rules to the correct `settings.json` scope.

## Execution Plan

### Phase 1: Foundation (lead - sequential)

1. Update `skills/claude-code-management/references/schemas.md` - add `config` and
   `recommendedPermissions` schemas to plugin.json reference
2. Update `agents/aida/knowledge/config-schema.md` - add `plugins:` section
3. Update `agents/claude-code-expert/knowledge/plugin-development.md` - document both
   declaration patterns with examples

**Review Gate 1**: reviewer validates schemas and docs.

### Phase 2: Parallel Implementation

**Track A (config-dev):**
1. Create `skills/aida-dispatch/scripts/utils/plugins.py` with:
   - `discover_installed_plugins()` - scan ~/.claude/plugins/cache/
   - `get_plugins_with_config()` - filter for config section
   - `validate_plugin_config()` - schema validation
   - `generate_plugin_checklist()` - multi-select question builder
   - `generate_plugin_preference_questions()` - per-plugin questions
2. Modify `skills/aida-dispatch/scripts/configure.py`:
   - Phase 1: add plugin checklist question after line 577
   - Phase 2: extract plugin_* responses and save under config["plugins"]
3. Update `skills/aida-dispatch/references/config.md` with plugin config docs

**Track B (permissions-dev):**
1. Create skill structure at `skills/permissions/`:
   - `SKILL.md` with frontmatter and activation triggers
   - `scripts/scanner.py` - scan plugins for recommendedPermissions
   - `scripts/aggregator.py` - deduplicate, categorize, detect conflicts
   - `scripts/settings_manager.py` - read/write settings.json for all scopes
   - `scripts/permissions.py` - two-phase API (get_questions + execute + audit)
   - `references/permissions-workflow.md`, `rule-syntax.md`, `presets.md`
2. Update `skills/aida-dispatch/SKILL.md` - add permissions routing and help text

**Review Gate 2**: reviewer checks both tracks.

### Phase 3: Integration (lead - sequential)
1. Dogfood `.claude-plugin/plugin.json` with both `config` and
   `recommendedPermissions` sections
2. Add "Next step" message in configure.py pointing to permissions setup

**Review Gate 3**: reviewer validates integration.

### Phase 4: Testing (qa)
1. Create `tests/unit/test_plugin_discovery.py` - config discovery tests
2. Create `tests/unit/test_permissions.py` - permissions skill tests
3. Run `make lint` and `make test`

**Review Gate 4**: reviewer does comprehensive final review.

### Phase 5: Final Validation (qa)
- Verify all acceptance criteria from the issue
- Run full quality suite: `make clean && make lint && make test`

## Key Conventions

- Python: ruff-compliant, type hints for public functions, 88 char line length
- Markdown: YAML frontmatter required, markdownlint config in `.markdownlint.json`
- Tests: pytest in `tests/unit/`, import pattern uses sys.path.insert
- Two-phase API pattern: `get_questions(context) -> dict` then
  `configure(responses, inferred) -> dict`
- Reuse utilities from `skills/aida-dispatch/scripts/utils/` (paths, files,
  json_utils, errors)
- Always fix linting errors, never bypass them

## Quality Gates

After each phase, run:
```bash
make lint    # ruff, yamllint, markdownlint, frontmatter validation
make test    # pytest
```

All linters and tests must pass before proceeding to the next phase.
```

---

## Alternative: Manual Team Spawn

If you prefer to spawn agents individually rather than using `/team`:

```
# Create team
TeamCreate: team_name="issue-4-plugin-config", description="Plugin config and permissions"

# Spawn teammates (in parallel)
Task: name="config-dev", subagent_type="general-purpose", team_name="issue-4-plugin-config"
Task: name="permissions-dev", subagent_type="general-purpose", team_name="issue-4-plugin-config"
Task: name="reviewer", subagent_type="code-reviewer", team_name="issue-4-plugin-config"
Task: name="qa", subagent_type="qa-engineer", team_name="issue-4-plugin-config"
```

The lead role is played by the main session (you).
