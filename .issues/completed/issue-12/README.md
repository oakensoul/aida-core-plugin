---
type: issue
issue: 12
title: "Auto-generate agent routing directives in CLAUDE.md during config"
status: "Completed"
created: "2026-02-16"
completed: "2026-02-16"
pr: 15
actual_effort: 2
---

# Issue #12: Auto-generate agent routing directives in CLAUDE.md during config

**Status**: COMPLETED
**Labels**: enhancement
**Milestone**: none
**Assignees**: none

## Description

During AIDA's config/init workflow, scan for available agents across all
sources, read their metadata/frontmatter, and auto-generate a routing
section in the project's CLAUDE.md that tells Claude when and why to
consult each agent as a subagent.

This enables **progressive context loading** -- the main context window
stays lean while specialized knowledge is pulled in on-demand via
subagent calls. Without this, users must manually maintain CLAUDE.md
directives for each agent, which doesn't scale as plugins add agents.

### Background

Claude Code's custom agents (subagents) and Agent Teams are separate
systems. Custom agents defined in `agents/` are read-only research/
analysis tools that return results. Agent Teams spawn full Claude Code
sessions with edit permissions. There is currently no way to use custom
agent definitions as Team members.

The practical implication: CLAUDE.md needs to contain routing directives
that tell Claude *when* to consult specific subagents for specialized
knowledge. This feature automates generating those directives.

## Requirements

- [ ] Scan for agents in all standard locations:
  - Project-level `agents/` directory
  - User-level `~/.claude/agents/` directory
  - Plugin-provided agents (via plugin manifest)
- [ ] Read each agent's frontmatter metadata (name, description, tags,
      skills, model)
- [ ] Generate an `## Available Agents` section in the project CLAUDE.md
      with routing directives for each discovered agent
- [ ] Each directive should include:
  - Agent name
  - What it specializes in (from description/tags)
  - When to consult it (inferred from tags and description)
  - Example invocation pattern
- [ ] Operation must be idempotent -- re-running config updates the
      section rather than duplicating it
- [ ] Preserve any manually-added content outside the managed section
- [ ] Use clear section markers (e.g., comments) to delineate the
      auto-generated block

## Technical Details

### Agent Discovery Sources

```text
1. {project}/agents/{name}/{name}.md     -- project agents
2. ~/.claude/agents/{name}/{name}.md      -- user global agents
3. Plugin manifests → agents/ paths       -- plugin-provided agents
```

### Example Generated Output

```markdown
## Available Agents

<!-- BEGIN AIDA AGENT ROUTING (auto-generated, do not edit) -->

### Agent Routing Directives

When working on this project, consult these specialized agents for
domain expertise before making decisions in their areas:

- **aida**: Expert on AIDA configuration, mementos, diagnostics, and
  feedback. Consult when analyzing, creating, or reviewing AIDA
  artifacts, configuration issues, or memento workflows.

- **claude-code-expert**: Expert on Claude Code extension patterns.
  Consult when reviewing, scoring, or creating agents, commands, skills,
  and plugins to ensure best practices are followed.

<!-- END AIDA AGENT ROUTING -->
```

### Agent Teams Guidance

The generated section should also include guidance for Agent Teams mode
so that team leads and teammates understand the routing pattern:

- When a **team lead** is orchestrating work, it should know to consult
  relevant subagents for domain expertise before delegating implementation
  to teammates
- When **teammates** encounter decisions in an agent's domain, they
  should know to either consult the subagent themselves or flag it back
  to the lead for expert consultation
- The routing directives should be written clearly enough that any agent
  in a team (lead or member) can understand when and why to invoke a
  subagent

### Integration Point

This should integrate with the existing config discovery workflow
(PR #11) which already scans for plugin configuration. Agent discovery
is a natural extension of that scan.

## Success Criteria

- [ ] Running config/init discovers all agents from all sources
- [ ] CLAUDE.md is updated with accurate routing directives
- [ ] Re-running config updates (not duplicates) the agent section
- [ ] Manually-added CLAUDE.md content is preserved
- [ ] New agents from installed plugins appear after re-running config
- [ ] Removed agents are cleaned up from the routing section

## Work Tracking

- Branch: `feat/12-auto-generate-agent-routing`
- Started: 2026-02-16
- Work directory: `issues/in-progress/issue-12/`

## Resolution

**Completed**: 2026-02-16
**Pull Request**: #15
**Actual Effort**: 2 hours

### Changes Made

- Added `skills/aida-dispatch/scripts/utils/agents.py` — agent discovery
  and CLAUDE.md routing generation module
- Added `tests/unit/test_agent_discovery.py` — 40 tests covering
  discovery, security, frontmatter parsing, routing generation, and
  CLAUDE.md updates
- Modified `skills/aida-dispatch/scripts/utils/plugins.py` — added
  `max_size` parameter to `_safe_read_file` for shared use
- Modified `skills/aida-dispatch/scripts/configure.py` — integrated
  agent discovery in Phase 1 and routing update in Phase 2
- Modified `.claude-plugin/aida-config.json` — declared plugin agents
- Modified `skills/aida-dispatch/scripts/utils/__init__.py` — exported
  agent discovery functions

### Implementation Details

- Three-source agent discovery (project > user > plugin) with
  first-found-wins deduplication
- YAML frontmatter parsing with `yaml.safe_load()` and robust
  closing delimiter detection
- Marker-based idempotent CLAUDE.md updates using HTML comments
- TOCTOU-safe file reading reused from plugins.py with parameterized
  size limits (500KB for agents, 1MB for plugins)
- Non-blocking error handling throughout — agent routing failures
  never block core configuration

### Notes

- PyYAML required for frontmatter parsing; graceful degradation if
  unavailable (returns empty list with warning)
- Plugin agents declared in `aida-config.json` with fallback to
  directory scanning for backward compatibility

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/12)
- PR #11: Plugin config discovery and permissions management
- Issue #7: Launch preparedness
