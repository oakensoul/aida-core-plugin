---
type: research
title: "Extension Framework Review: Issue #31"
description: >
  Evaluation of the WHO/HOW/CONTEXT/MEMORY/AUTOMATION taxonomy against
  current Claude Code capabilities and recommendations for the
  claude-code-management decomposition.
status: final
author: claude-code-expert
date: 2026-02-24
---

# Extension Framework Review: Issue #31

## Summary

The existing WHO/HOW/CONTEXT/MEMORY/AUTOMATION taxonomy is **fundamentally
sound** but Claude Code has evolved significantly since our knowledge base was
written. The docs researcher found 18 new features and over 10 outdated areas.

Key findings for the decomposition:

1. The taxonomy holds for the file-based extension model, but Claude Code has
   added substantial new extension points (agent teams, rules, auto memory,
   LSP/MCP server bundling) that the framework does not yet address
2. The `claude-code-expert` knowledge base has **critical gaps**: missing
   dedicated `skills.md` and `subagents.md` files, outdated hook event names
   and structure in `settings.md`, and outdated plugin structure documentation
3. All proposed manager skills should remain **Skills (HOW)** -- the taxonomy
   is correct for the decomposition
4. The `claude-code-expert` agent's knowledge base needs targeted updates
   **before or alongside** the decomposition, not after

---

## 1. Taxonomy Evaluation: WHO/HOW/CONTEXT/MEMORY/AUTOMATION

### Does the taxonomy hold?

**Yes, with expansions needed.**

The five core categories still map accurately to Claude Code's extension model:

| Category | Claude Code Reality | Assessment |
| -------- | ------------------- | ---------- |
| WHO (Subagent) | `/agents/` directories with `.md` persona files | Accurate |
| HOW (Skill) | `/skills/` directories with `SKILL.md` entry points | Accurate |
| CONTEXT (Knowledge) | `knowledge/` subdirs loaded with extensions | Accurate |
| MEMORY (CLAUDE.md) | Auto-loaded markdown at project/user/enterprise levels | Mostly accurate; new features |
| AUTOMATION (Hooks) | `settings.json` lifecycle event bindings | Mostly accurate; hooks expanded |

### New extension points not in the taxonomy

Claude Code has added extension mechanisms that do not fit cleanly into the
five existing categories:

**Agent Teams (WHO, orchestrated)**

The "agent teams" experimental system (enabled via
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) allows multiple Claude Code instances
to work as a team lead + teammates with a shared task list, inter-agent
messaging, and quality gate hooks (`TeammateIdle`, `TaskCompleted`).

This is not a separate extension type so much as a new **orchestration mode**
for existing subagents. The framework can accommodate it without a new category,
but agent teams need documentation.

**Modular Rules (`.claude/rules/`)**

A new rules system with path-specific glob pattern targeting is neither MEMORY
(CLAUDE.md) nor a full extension. It's closer to structured MEMORY with
targeting. Our `claude-md-manager` skill will need to decide whether to manage
`.claude/rules/` files or leave that for a future manager.

**Auto Memory**

Claude Code now auto-saves project patterns to `~/.claude/projects/<project>/memory/`.
This is separate from CLAUDE.md instruction files. Our framework calls CLAUDE.md
"MEMORY" but auto memory is a distinct, automated system. The MEMORY category
in the taxonomy needs clarification.

**MCP Servers and LSP Servers in Plugins**

Plugins can now bundle MCP servers (`.mcp.json`) and LSP servers (`.lsp.json`).
These are configured via JSON, not markdown. They are a new component type
within plugins. Our plugin-development.md and schemas must reflect this.

### Recommended taxonomy update

The five core categories still work. No new top-level category is needed for
the decomposition. However, the framework should acknowledge:

- Agent teams are a coordination mode for WHO (Subagent), not a new type
- Auto memory is an automatic MEMORY subsystem, separate from CLAUDE.md
- Modular rules are a targeted MEMORY mechanism within CLAUDE.md territory
- MCP servers and LSP servers are plugin-bundled components, not standalone types

---

## 2. Critical Knowledge Base Gaps

The docs researcher identified two missing files that are **critical** for the
claude-code-expert agent's ability to support the decomposition:

### 2a. MISSING: skills.md

We have no dedicated knowledge file for skills. The official docs cover:

- Skill locations: Enterprise, Personal, Project, Plugin scopes
- Frontmatter fields: `name`, `description`, `argument-hint`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`,
  `context`, `agent`, `hooks`
- String substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`,
  `${CLAUDE_SESSION_ID}`
- Dynamic context injection: `!`command`` syntax for shell preprocessing
- `context: fork` for running skills in subagents
- Agent types for spawning: `Explore`, `Plan`, `general-purpose`, or custom
- `SLASH_COMMAND_TOOL_CHAR_BUDGET` for context budget control
- Integration with the Agent Skills open standard (agentskills.io)

**Impact on decomposition:** Every manager skill we create follows skill
conventions. Without a `skills.md` reference, the claude-code-expert agent
lacks authoritative guidance when generating skill content for `agent-manager`,
`skill-manager`, etc.

**Recommendation:** Create `knowledge/skills.md` before implementing the
decomposition.

### 2b. MISSING: subagents.md

We have no dedicated knowledge file for subagents. The official docs cover:

- Built-in subagents: Explore (Haiku, read-only), Plan, general-purpose,
  Bash, statusline-setup, Claude Code Guide
- Frontmatter fields: `name`, `description`, `tools`, `disallowedTools`,
  `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`,
  `memory`, `background`, `isolation`
- Permission modes: `default`, `acceptEdits`, `dontAsk`,
  `bypassPermissions`, `plan`
- Persistent memory for subagents with `user`/`project`/`local` scopes
- Background vs foreground execution, worktree isolation
- `Task(agent_type)` syntax for restricting which agents can be spawned
- Hooks in subagent frontmatter

**Impact on decomposition:** The manager skills will spawn the `claude-code-expert`
subagent. Understanding the full subagent frontmatter options (especially
`permissionMode`, `maxTurns`, `memory`, `isolation`) could improve how the
managers spawn it.

**Recommendation:** Create `knowledge/subagents.md` before or alongside the
decomposition.

---

## 3. Outdated Knowledge That Must Be Fixed

### 3a. settings.md: Hook Event Names (Critical Bug)

Confirmed by docs research. `settings.md` uses legacy camelCase names:

```json
"preToolExecution"  // WRONG
"postToolExecution" // WRONG
```

Official docs use PascalCase:

```json
"PreToolUse"   // CORRECT
"PostToolUse"  // CORRECT
```

Additionally, `settings.md` shows a simplified hook structure missing the
nested `hooks` array and `type` field. The correct structure is:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          { "type": "command", "command": "echo test" }
        ]
      }
    ]
  }
}
```

**Recommendation:** Fix `settings.md` hook examples immediately. This is a
correctness issue that will cause broken configurations if users follow our
examples.

### 3b. hooks.md: Missing 7 New Hook Events

Our `hooks.md` documents 10 events. The official docs now have 17 events.
Missing events:

| New Event | Purpose |
| --------- | ------- |
| `PostToolUseFailure` | After a tool fails (new diagnostic event) |
| `SubagentStart` | Before a subagent begins work |
| `TeammateIdle` | Agent teams: teammate waiting for work |
| `TaskCompleted` | Agent teams: task marked done in shared list |
| `ConfigChange` | When settings configuration changes |
| `WorktreeCreate` | When a worktree is created |
| `WorktreeRemove` | When a worktree is removed |

**Recommendation:** Update `hooks.md` with the seven new events.

### 3c. hooks.md: Missing New Hook Types

Our `hooks.md` only documents `command` type hooks. The official docs now
document three hook types:

- `command` -- Shell commands (already documented)
- `prompt` -- LLM-evaluated prompts with `$ARGUMENTS` placeholder (NEW)
- `agent` -- Agentic verifiers with tool access for complex verification (NEW)

The `prompt` and `agent` hook types represent a significant expansion of the
AUTOMATION category -- hooks are no longer purely deterministic shell commands.
This has framework implications.

**Framework implication:** The characterization of hooks as "deterministic"
in our framework needs nuance. `command` hooks are deterministic; `prompt`
and `agent` hooks invoke the LLM. The framework's Hooks section should
distinguish between hook types.

**Recommendation:** Update `hooks.md` with `prompt` and `agent` hook types.
Update `framework-design-principles.md` hook section to note that only
`command` hooks are deterministic; `prompt` and `agent` hooks involve LLM
judgment.

### 3d. plugin-development.md: Missing Plugin Components

The plugin structure has expanded significantly. Missing from our docs:

- `.lsp.json` -- LSP server bundling
- `.mcp.json` or `mcpServers` in `plugin.json` -- MCP server bundling
- `hooks/hooks.json` -- Plugin-level hooks (separate from settings.json)
- `settings.json` at plugin root -- Default settings, including `agent` key
- `outputStyles/` directory
- `${CLAUDE_PLUGIN_ROOT}` environment variable
- Plugin caching to `~/.claude/plugins/cache`
- `claude plugin install|uninstall|enable|disable|update|validate` CLI
- `--plugin-dir` flag for development testing

**Impact on decomposition:** The `plugin-manager` skill (and the `create-plugin`
merge into it) must generate the correct expanded plugin structure. Without
updating this knowledge, the claude-code-expert subagent will generate
incomplete plugin scaffolds.

**Recommendation:** Update `plugin-development.md` with all missing plugin
components. This is high priority for the `plugin-manager` implementation.

### 3e. index.md: Outdated External Resource URLs

Both external URLs in `index.md` are outdated:

| Current (Wrong) | Correct |
| --------------- | ------- |
| `https://docs.anthropic.com/en/docs/claude-code` | `https://code.claude.com/docs/en/overview` |
| `https://github.com/anthropics/claude-code/tree/main/sdk` | `https://platform.claude.com/docs/en/agent-sdk/overview` |

**Recommendation:** Update `index.md` URLs immediately.

### 3f. settings.md: Outdated Model Names

`settings.md` references `claude-sonnet-4-5-20250514`. Current models are:
- `claude-sonnet-4-6`
- `claude-opus-4-6`
- `claude-haiku-4-5`

**Recommendation:** Update model names in `settings.md` examples.

### 3g. extension-types.md: Outdated Plugin Invocation

Our knowledge says plugins are invoked via `/plugin add`. The official system
uses `claude plugin install` CLI or `/plugin` in interactive mode.

**Recommendation:** Update plugin invocation examples in `extension-types.md`.

### 3h. claude-md-files.md: Missing Import Features and New Memory Types

Missing:
- Import approval dialog for external imports
- `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` environment variable
- `@~/.claude/my-project-instructions.md` home-directory imports
- `CLAUDE.local.md` (auto-gitignored personal project preferences)
- Auto memory system (`~/.claude/projects/<project>/memory/`) distinction
- Modular rules (`.claude/rules/`) system
- Windows enterprise path correction

**Recommendation:** Update `claude-md-files.md` with these features.

---

## 4. Framework Implications for the Decomposition

### 4a. Does entity-focused decomposition align with the framework?

**Yes, strongly.** The Single Responsibility principle in `design-patterns.md`
directly calls out "Monolithic Skills" as an anti-pattern. The current
`claude-code-management` SKILL.md at 590+ lines with agent, skill, plugin,
hook, and CLAUDE.md operations is the exact anti-pattern described.

The decomposition corrects this.

### 4b. Do manager skills remain "Skills" or do any become "Subagents"?

All proposed managers (`agent-manager`, `skill-manager`, `plugin-manager`,
`hook-manager`, `claude-md-manager`, `marketplace-manager`) should remain
**Skills (HOW)**, not Subagents (WHO).

Rationale (unchanged from preliminary analysis):
- They define processes (create, validate, version, list)
- They orchestrate scripts and spawn the `claude-code-expert` subagent
- They do not define domain expertise or judgment frameworks

The `claude-code-expert` subagent holds the expertise. The manager skills are
entry points that orchestrate work and delegate expertise to the subagent.
This is correct per the framework's Consultant Rule.

### 4c. Does agent-manager differ from the claude-code-expert's role?

This question arises: if `claude-code-expert` knows how to CREATE agents, and
`agent-manager` is a skill that MANAGES agents, isn't the agent creating
itself?

The answer is no -- the distinction is clean:

- `agent-manager` (Skill) = the **process** for agent CRUD operations
  (when to gather questions, how to invoke scripts, what output contract to use)
- `claude-code-expert` (Subagent) = the **expertise** for what a good agent
  looks like, what quality standards to apply, how to generate content

The manager skill orchestrates; the subagent provides judgment. This is the
Consultant Rule in action.

### 4d. Should claude-code-expert know about all 6 new manager skills?

The `claude-code-expert` subagent currently documents the framework for building
extensions but doesn't need to document the specific manager skill CRUD process.
The manager skills self-document their own processes.

What the claude-code-expert DOES need to know (and currently lacks) is the
updated skill frontmatter options, subagent frontmatter options, and expanded
plugin component types -- because these directly inform content generation
when managers invoke it.

### 4e. Hooks are no longer purely deterministic

The addition of `prompt` and `agent` hook types changes the characterization
of the AUTOMATION category. The framework currently says hooks provide
"deterministic control" and "guaranteed execution." This remains true for
`command` hooks but not for `prompt` or `agent` hooks.

The `hook-manager` skill must handle all three hook types. The framework's
description of hooks should be updated to:

> Hooks provide lifecycle-bound execution. `command` hooks are deterministic
> shell commands. `prompt` hooks invoke LLM judgment at specific events.
> `agent` hooks run agentic verifiers with tool access.

### 4f. Agent teams require a new operational pattern

Agent teams are an orchestration mode where a lead Claude Code instance manages
multiple teammate instances. This does not require a new extension type, but
it does require:

- A new SKILL.md pattern for team coordination (assigning tasks, messaging,
  quality gates)
- Understanding of `TeammateIdle` and `TaskCompleted` hook events in
  `hook-manager`
- New documentation in the knowledge base

The decomposition does not need to solve agent teams. But the `hook-manager`
skill should document the two new team-related hook events.

---

## 5. Recommended Knowledge Base Updates

### Priority 1: Create Before Decomposition

| File | Action | Reason |
| ---- | ------ | ------ |
| `knowledge/skills.md` | CREATE | Manager skills follow skill conventions; critical reference |
| `knowledge/subagents.md` | CREATE | Manager skills spawn claude-code-expert; must know frontmatter |
| `knowledge/settings.md` | FIX hook names | Broken examples (PascalCase vs camelCase) |
| `knowledge/hooks.md` | ADD 7 new events | hook-manager must handle all events |

### Priority 2: Update Alongside Decomposition

| File | Action | Reason |
| ---- | ------ | ------ |
| `knowledge/plugin-development.md` | UPDATE | plugin-manager must scaffold full plugin structure |
| `knowledge/hooks.md` | ADD `prompt`/`agent` types | hook-manager must handle all hook types |
| `knowledge/framework-design-principles.md` | CLARIFY hooks | Deterministic qualifier only applies to `command` hooks |
| `knowledge/index.md` | FIX URLs, ADD entries | Broken external links; new knowledge files |
| `knowledge/settings.md` | UPDATE model names, ADD fields | Outdated models and missing settings |

### Priority 3: Update After Decomposition

| File | Action | Reason |
| ---- | ------ | ------ |
| `knowledge/claude-md-files.md` | UPDATE | Add auto memory, CLAUDE.local.md, rules, imports |
| `knowledge/extension-types.md` | UPDATE | Correct plugin invocation, add agent teams note |
| `knowledge/design-patterns.md` | UPDATE | Add LSP/MCP server bundling patterns |

### New Files to Create (Post-Decomposition)

| File | Purpose |
| ---- | ------- |
| `knowledge/agent-teams.md` | Document agent teams system |
| `knowledge/mcp.md` | Dedicated MCP configuration guide |

---

## 6. Conclusions for the Decomposition

### Taxonomy verdict

The WHO/HOW/CONTEXT/MEMORY/AUTOMATION framework is valid and does not need
structural overhaul. The extensions it describes are real and correctly
characterized. However, Claude Code has grown beyond what the framework
documents. The framework needs targeted updates and two new knowledge files,
not a redesign.

### Extension type choices

All six manager skills should be **Skills (HOW)**. This is correct per:
- Single Responsibility principle (each manager handles one entity domain)
- The Consultant Rule (expertise stays in `claude-code-expert` subagent)
- The HOW/WHO distinction (skills define process; agents hold expertise)

### Knowledge base health

The `claude-code-expert` knowledge base has **two critical gaps** (`skills.md`,
`subagents.md`) and **four files with outdated information** (`settings.md`,
`hooks.md`, `plugin-development.md`, `index.md`). These gaps will impair the
agent's effectiveness in supporting the decomposition work if not addressed.

The most urgent fixes (before implementing any manager skills):
1. Create `skills.md` -- manager skills are skills; need authoritative reference
2. Create `subagents.md` -- manager skills spawn claude-code-expert; need
   frontmatter knowledge
3. Fix `settings.md` -- broken hook configuration examples
4. Update `hooks.md` -- seven new events, two new hook types

### Impact on agent-manager specifically

The `agent-manager` creates subagents. With the new `subagents.md` frontmatter
knowledge (covering `permissionMode`, `maxTurns`, `memory`, `background`,
`isolation`, `hooks` in subagent frontmatter), the agent-manager can generate
richer, more capable subagent definitions than the current system produces.

This is an opportunity, not just a gap to fill.

### Skills open standard

Skills now conform to the Agent Skills open standard (agentskills.io), which
works across multiple AI tools. Our framework should acknowledge this
interoperability when documenting the HOW (Skill) category. The `skills.md`
knowledge file should cover this.

---

## 7. Framework Review Checklist

For the decomposition implementation team:

- [ ] Create `knowledge/skills.md` (framework gap: critical)
- [ ] Create `knowledge/subagents.md` (framework gap: critical)
- [ ] Fix `settings.md` hook event names and structure (correctness bug)
- [ ] Update `hooks.md` with 7 new events and 3 hook types
- [ ] Update `plugin-development.md` with expanded plugin components
- [ ] Fix `index.md` external resource URLs
- [ ] Update `settings.md` model names and add missing settings fields
- [ ] Update `framework-design-principles.md` hooks section (determinism qualifier)
- [ ] After decomposition: update `claude-md-files.md`, `extension-types.md`,
      `design-patterns.md`
- [ ] After decomposition: create `agent-teams.md` and `mcp.md`

The decomposition itself (splitting `claude-code-management` into entity-focused
managers) aligns with framework principles and is the right direction. The
framework review surfaced important knowledge base updates that will make the
decomposed managers more capable, not just structurally cleaner.
