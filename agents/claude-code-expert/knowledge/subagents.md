---
type: reference
name: subagents
title: Claude Code Subagents Guide
description: Comprehensive reference for creating and configuring subagents in Claude Code
version: "1.0.0"
---

# Claude Code Subagents

Subagents are **specialized AI assistants** that handle specific types of tasks.
Each subagent runs in its own context window with a custom system prompt,
specific tool access, and independent permissions. When Claude encounters a task
that matches a subagent's description, it delegates to that subagent, which
works independently and returns results.

## Subagents in the Extension Model

In the WHO/HOW/CONTEXT taxonomy, subagents represent **WHO** -- identity,
expertise, and judgment. The orchestrator (Claude Code) is the primary agent.
Subagents are specialists spawned when specific expertise is needed.

| Extension | Role | Relationship to Subagents |
| --------- | ---- | ------------------------- |
| **Subagent** | WHO | Defines expertise and judgment |
| **Skill** | HOW | Subagents can load skills; skills can fork into subagents |
| **Knowledge** | CONTEXT | Loaded with subagent via `knowledge/` directory |
| **Hook** | AUTOMATION | Can run scoped to a subagent's lifecycle |

**Key insight:** Subagents receive only their system prompt (the markdown body)
plus basic environment details like the working directory. They do NOT receive
the full Claude Code system prompt or the parent conversation's history.

## Built-in Subagent Types

Claude Code includes built-in subagents that Claude automatically uses when
appropriate. Each inherits the parent conversation's permissions with additional
tool restrictions.

### Explore

A fast, read-only agent optimized for searching and analyzing codebases.

- **Model:** Haiku (fast, low-latency)
- **Tools:** Read-only tools (Write and Edit denied)
- **Purpose:** File discovery, code search, codebase exploration
- **Thoroughness levels:** quick (targeted lookups), medium (balanced), very
  thorough (comprehensive analysis)

Claude delegates to Explore when it needs to search or understand a codebase
without making changes. This keeps exploration results out of the main
conversation context.

### Plan

A research agent used during plan mode to gather context before presenting a
plan.

- **Model:** Inherits from main conversation
- **Tools:** Read-only tools (Write and Edit denied)
- **Purpose:** Codebase research for planning

When in plan mode, Claude delegates research to the Plan subagent. This prevents
infinite nesting (subagents cannot spawn other subagents) while still gathering
necessary context.

### General-purpose

A capable agent for complex, multi-step tasks that require both exploration and
action.

- **Model:** Inherits from main conversation
- **Tools:** All tools
- **Purpose:** Complex research, multi-step operations, code modifications

Claude delegates to general-purpose when the task requires both exploration and
modification, complex reasoning, or multiple dependent steps.

### Bash

A command execution specialist for running terminal commands in a separate
context.

- **Model:** Inherits from main conversation
- **Tools:** Bash
- **Purpose:** Running terminal commands in a separate context

### statusline-setup

A configuration helper for the status line feature.

- **Model:** Sonnet
- **Purpose:** Configuring the Claude Code status line when `/statusline` is run

### Claude Code Guide

A help and documentation assistant.

- **Model:** Haiku
- **Tools:** Read-only tools (Read, Grep, Glob)
- **Purpose:** Answering questions about Claude Code features

## Subagent File Structure

Subagent files are Markdown with YAML frontmatter for configuration, followed by
the system prompt in the markdown body.

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

The frontmatter defines metadata and configuration. The body becomes the system
prompt that guides the subagent's behavior.

### File Naming Convention

- File: `agents/{name}/{name}.md`
- Knowledge directory: `agents/{name}/knowledge/`
- Plugin-bundled: `{plugin}/agents/{name}/{name}.md`

## Frontmatter Fields Reference

Only `name` and `description` are required. All other fields are optional.

### name (required)

Unique identifier using lowercase letters and hyphens.

```yaml
name: code-reviewer
```

### description (required)

When Claude should delegate to this subagent. Claude uses this field to decide
when to delegate tasks. Write a clear, specific description.

```yaml
description: >
  Expert code review specialist. Proactively reviews code for quality,
  security, and maintainability. Use immediately after writing or modifying
  code.
```

To encourage proactive delegation, include phrases like "use proactively" in the
description.

### tools

Tools the subagent can use. Inherits all tools from the main conversation if
omitted. Specify as a comma-separated list or YAML array. Prefer
comma-separated string format for simplicity.

```yaml
# Comma-separated (preferred)
tools: Read, Glob, Grep, Bash

# YAML array
tools:
  - Read
  - Glob
  - Grep
  - Bash
```

Available tools include all Claude Code internal tools: Read, Write, Edit,
Glob, Grep, Bash, Task, WebFetch, WebSearch, and any configured MCP tools.

#### Restricting spawnable subagents with Task(agent_type)

When an agent runs as the main thread with `claude --agent`, use
`Task(agent_type)` syntax in the `tools` field to restrict which subagents it
can spawn:

```yaml
# Only allow spawning worker and researcher subagents
tools: Task(worker, researcher), Read, Bash
```

This is an allowlist: only the named subagents can be spawned. To allow
spawning any subagent, use `Task` without parentheses. If `Task` is omitted
from `tools` entirely, the agent cannot spawn any subagents.

**Note:** This restriction only applies to agents running as the main thread
with `claude --agent`. Subagents cannot spawn other subagents, so
`Task(agent_type)` has no effect in subagent definitions.

### disallowedTools

Tools to deny, removed from the inherited or specified list.

```yaml
disallowedTools: Write, Edit
```

Use `disallowedTools` as a denylist when you want to inherit most tools but
block specific ones.

### model

Which Claude model to use. Available values:

| Value | Behavior |
| ----- | -------- |
| `sonnet` | Use Claude Sonnet |
| `opus` | Use Claude Opus |
| `haiku` | Use Claude Haiku (fast, low-cost) |
| `inherit` | Use the same model as the main conversation |
| *(omitted)* | Defaults to `inherit` |

```yaml
model: sonnet
```

Choose `haiku` for fast, read-only operations. Choose `sonnet` or `opus` for
complex analysis or generation. Use `inherit` when the subagent should match
the main conversation's model.

### permissionMode

Controls how the subagent handles permission prompts. Subagents inherit the
permission context from the main conversation but can override the mode.

| Mode | Behavior |
| ---- | -------- |
| `default` | Standard permission checking with prompts |
| `acceptEdits` | Auto-accept file edits |
| `dontAsk` | Auto-deny permission prompts (explicitly allowed tools still work) |
| `bypassPermissions` | Skip all permission checks |
| `plan` | Plan mode (read-only exploration) |

```yaml
permissionMode: acceptEdits
```

**Warning:** Use `bypassPermissions` with caution. It skips all permission
checks. If the parent uses `bypassPermissions`, this takes precedence and
cannot be overridden.

### maxTurns

Maximum number of agentic turns before the subagent stops. Limits how long a
subagent can work before returning control.

```yaml
maxTurns: 25
```

### skills

Skills to load into the subagent's context at startup. The full skill content
is injected, not just made available for invocation. Subagents do NOT inherit
skills from the parent conversation; you must list them explicitly.

```yaml
skills:
  - api-conventions
  - error-handling-patterns
```

This is the inverse of `context: fork` in a skill. With `skills` in a
subagent, the subagent controls the system prompt and loads skill content.
With `context: fork` in a skill, the skill content is injected into the agent.

### mcpServers

MCP servers available to this subagent. Each entry is either a server name
referencing an already-configured server or an inline definition.

```yaml
# Reference existing server by name
mcpServers:
  - slack

# Inline definition
mcpServers:
  my-server:
    command: npx
    args:
      - -y
      - "@myorg/mcp-server"
```

**Note:** This YAML syntax is for agent frontmatter. For MCP server
configuration in JSON settings files, see `knowledge/settings.md`.

**Note:** MCP tools are NOT available in background subagents.

### hooks

Lifecycle hooks scoped to this subagent. These hooks only run while the
subagent is active and are cleaned up when it finishes.

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
```

Supported events in subagent frontmatter:

| Event | Matcher Input | When It Fires |
| ----- | ------------- | ------------- |
| `PreToolUse` | Tool name | Before the subagent uses a tool |
| `PostToolUse` | Tool name | After the subagent uses a tool |
| `Stop` | *(none)* | When the subagent finishes (converted to `SubagentStop`) |

All hook events from settings.json are supported. `Stop` hooks in frontmatter
are automatically converted to `SubagentStop` events at runtime.

### memory

Persistent memory scope that survives across conversations. The subagent uses
this directory to build up knowledge over time.

```yaml
memory: user
```

| Scope | Location | Use When |
| ----- | -------- | -------- |
| `user` | `~/.claude/agent-memory/<agent-name>/` | Knowledge applies across all projects |
| `project` | `.claude/agent-memory/<agent-name>/` | Knowledge is project-specific and shareable via VCS |
| `local` | `.claude/agent-memory-local/<agent-name>/` | Knowledge is project-specific but should not be in VCS |

When memory is enabled:

- The subagent's system prompt includes instructions for reading and writing to
  the memory directory
- The first 200 lines of `MEMORY.md` in the memory directory are injected into
  context
- Read, Write, and Edit tools are automatically enabled so the subagent can
  manage its memory files

`user` is the recommended default scope.

### background

Set to `true` to always run this subagent as a background task.

```yaml
background: true
```

Default: `false`. See the
[Background vs Foreground Execution](#background-vs-foreground-execution)
section for details.

### isolation

Set to `worktree` to run the subagent in a temporary git worktree, giving it
an isolated copy of the repository. The worktree is automatically cleaned up
if the subagent makes no changes.

```yaml
isolation: worktree
```

## Subagent Scopes and Discovery

Subagents are discovered from multiple locations. When multiple subagents share
the same name, the higher-priority location wins.

| Priority | Location | Scope | How to Create |
| -------- | -------- | ----- | ------------- |
| 1 (highest) | `--agents` CLI flag | Current session | JSON when launching Claude Code |
| 2 | `.claude/agents/` | Current project | Interactive or manual |
| 3 | `~/.claude/agents/` | All your projects | Interactive or manual |
| 4 (lowest) | Plugin's `agents/` directory | Where plugin is enabled | Installed with plugins |

**Project subagents** (`.claude/agents/`) are ideal for codebase-specific
subagents. Check them into version control for team collaboration.

**User subagents** (`~/.claude/agents/`) are personal subagents available in
all projects.

**Plugin subagents** come from installed plugins and appear alongside custom
subagents in `/agents`.

## CLI-Defined Subagents

Pass subagent definitions as JSON when launching Claude Code with the
`--agents` flag. These exist only for that session and are not saved to disk.

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

The `--agents` flag accepts JSON with the same frontmatter fields as file-based
subagents. Use `prompt` for the system prompt (equivalent to the markdown body
in file-based subagents).

CLI-defined subagents have the highest priority and override any file-based
subagent with the same name.

## Spawning Subagents with the Task Tool

Claude spawns subagents using the Task tool. Key parameters:

| Parameter | Description |
| --------- | ----------- |
| `agent_type` | Name of the subagent to spawn (e.g., `"code-reviewer"`) |
| `prompt` | The task description passed to the subagent |
| `team_name` | For agent teams: name of the team |
| `name` | For agent teams: name of the teammate |
| `mode` | Execution mode (e.g., plan mode) |
| `isolation` | Set to `"worktree"` for git worktree isolation |
| `run_in_background` | Set to `true` to run the subagent as a background task |

You can request a specific subagent explicitly:

```text
Use the code-reviewer subagent to review my recent changes
```

Or Claude delegates automatically based on the subagent's `description` field.

**Important constraint:** Subagents cannot spawn other subagents. If a workflow
requires nested delegation, use skills or chain subagents from the main
conversation.

## Background vs Foreground Execution

Subagents can run in **foreground** (blocking) or **background** (concurrent):

### Foreground Subagents

- Block the main conversation until complete
- Permission prompts and clarifying questions pass through to the user
- Full MCP tool access

### Background Subagents

- Run concurrently while the user continues working
- Before launching, Claude prompts for all tool permissions upfront
- Once running, the subagent inherits pre-approved permissions and auto-denies
  anything not pre-approved
- If the subagent needs to ask clarifying questions, that tool call fails but
  the subagent continues
- **MCP tools are NOT available** in background subagents

Claude decides foreground vs background based on the task. You can also:

- Ask Claude to "run this in the background"
- Press **Ctrl+B** to background a running foreground task

If a background subagent fails due to missing permissions, you can resume it
in the foreground to retry with interactive prompts.

To disable background tasks entirely, set `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`
environment variable to `1`.

## Subagent Resume Capability

Each subagent invocation creates a new instance with fresh context. To continue
an existing subagent's work, ask Claude to resume it.

Resumed subagents retain their **full conversation history**, including all
previous tool calls, results, and reasoning. The subagent picks up exactly
where it stopped rather than starting fresh.

```text
Use the code-reviewer subagent to review the authentication module
[Agent completes]

Continue that code review and now analyze the authorization logic
[Claude resumes the subagent with full context]
```

### Transcript Persistence

Subagent transcripts are stored at
`~/.claude/projects/{project}/{sessionId}/subagents/` as
`agent-{agentId}.jsonl`.

- Main conversation compaction does not affect subagent transcripts
- Transcripts persist within their session
- Subagents can be resumed after restarting Claude Code by resuming the same
  session
- Automatic cleanup based on `cleanupPeriodDays` setting (default: 30 days)

### Auto-Compaction

Subagents support automatic compaction at approximately 95% capacity. Set
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to trigger compaction earlier (e.g., `50`).

## The /agents Command

The `/agents` command provides an interactive interface for managing subagents:

- View all available subagents (built-in, user, project, and plugin)
- Create new subagents with guided setup or Claude generation
- Edit existing subagent configuration and tool access
- Delete custom subagents
- See which subagents are active when duplicates exist

From the command line (non-interactive): `claude agents` lists all configured
subagents grouped by source.

Subagents created via `/agents` are loaded immediately without restarting the
session. Manually created files require a session restart or `/agents` to load.

## Disabling Specific Subagents

Prevent Claude from using specific subagents by adding them to the `deny` array
in settings:

```json
{
  "permissions": {
    "deny": ["Task(Explore)", "Task(my-custom-agent)"]
  }
}
```

Or use the CLI flag: `claude --disallowedTools "Task(Explore)"`

## Project-Level Hooks for Subagent Events

Configure hooks in `settings.json` that respond to subagent lifecycle events in
the main session:

| Event | Matcher Input | When It Fires |
| ----- | ------------- | ------------- |
| `SubagentStart` | Agent type name | When a subagent begins execution |
| `SubagentStop` | Agent type name | When a subagent completes |

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup.sh" }
        ]
      }
    ]
  }
}
```

## Agent Teams (Experimental)

> **Experimental.** Agent teams require
> `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and are disabled by default.

Agent teams coordinate **multiple Claude Code instances** working together. One
session acts as the team lead, coordinating work and assigning tasks. Teammates
work independently, each in its own context window, and can communicate directly
with each other.

Enable via settings:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Architecture

| Component | Role |
| --------- | ---- |
| **Team lead** | Main Claude Code session; creates team, spawns teammates, coordinates |
| **Teammates** | Separate Claude Code instances working on assigned tasks |
| **Task list** | Shared work items that teammates claim and complete |
| **Mailbox** | Messaging system for inter-agent communication |

### Shared Task Lists

Tasks have three states: pending, in_progress, and completed. Tasks can depend
on other tasks; a pending task with unresolved dependencies cannot be claimed
until those dependencies complete.

- The lead creates tasks and teammates work through them
- The lead can assign tasks explicitly, or teammates self-claim
- Task claiming uses file locking to prevent race conditions
- Stored at `~/.claude/tasks/{team-name}/`

### Inter-Agent Messaging

- **message**: Send to one specific teammate (DM)
- **broadcast**: Send to all teammates simultaneously (use sparingly; costs
  scale linearly with team size)
- Messages are delivered automatically to recipients
- Idle notifications are sent automatically when a teammate finishes

### Plan Approval Workflows

Require teammates to plan before implementing:

1. Teammate works in read-only plan mode
2. Teammate sends a plan approval request to the lead
3. Lead reviews and approves or rejects with feedback
4. If rejected, teammate revises and resubmits
5. Once approved, teammate exits plan mode and implements

### Quality Gates with Hooks

| Hook Event | Trigger | Behavior |
| ---------- | ------- | -------- |
| `TeammateIdle` | Teammate about to go idle | Exit code 2 sends feedback, keeps teammate working |
| `TaskCompleted` | Task marked complete | Exit code 2 prevents completion, sends feedback |

### Display Modes

| Mode | Description | Requirement |
| ---- | ----------- | ----------- |
| `in-process` | All teammates in main terminal; Shift+Down to cycle | Any terminal |
| `tmux` | Each teammate in its own split pane | tmux or iTerm2 |
| `auto` (default) | Split panes if inside tmux; in-process otherwise | N/A |

Configure in settings.json:

```json
{
  "teammateMode": "in-process"
}
```

Or per-session: `claude --teammate-mode in-process`

### Team Configuration

- **Team config:** `~/.claude/teams/{team-name}/config.json`
- **Task list:** `~/.claude/tasks/{team-name}/`
- Config contains a `members` array with each teammate's name, agent ID, and
  agent type

### Limitations

- No session resumption for in-process teammates (`/resume` and `/rewind` do
  not restore them)
- One team per session; clean up current team before starting a new one
- No nested teams; teammates cannot spawn their own teams
- Fixed leader; cannot promote a teammate or transfer leadership
- All teammates start with the lead's permission mode; per-teammate modes
  can be changed after spawning but not at spawn time
- Split panes require tmux or iTerm2 (not supported in VS Code terminal,
  Windows Terminal, or Ghostty)

## Subagents vs Skills

| Aspect | Subagent | Skill |
| ------ | -------- | ----- |
| **Role** | WHO -- expertise and judgment | HOW -- process and execution |
| **Context** | Own context window (isolated) | Main conversation context (shared) |
| **Invocation** | Via Task tool (automatic or explicit) | Via `/skill-name` or orchestrator |
| **State** | Fresh context each invocation (resumable) | Stateless; runs in caller's context |
| **Tools** | Configurable per subagent | Configurable per skill |
| **Model** | Can use a different model | Can use a different model |
| **Nesting** | Cannot spawn other subagents | Can fork into subagent via `context: fork` |
| **MCP** | Configurable; NOT available in background | Available |
| **Memory** | Persistent memory across sessions | No persistent memory |
| **Use when** | Task produces verbose output; need tool restrictions; work is self-contained | Reusable workflows; need main context; user-invocable processes |

**Use subagents when:**

- The task produces verbose output you don't need in the main context
- You want to enforce specific tool restrictions or permissions
- The work is self-contained and can return a summary
- You need to preserve the main conversation's context budget

**Use skills when:**

- You want reusable prompts or workflows in the main conversation context
- The process needs to be user-invocable (e.g., `/deploy`)
- Multiple phases share significant context

## Common Patterns

### Read-Only Reviewer

Restrict tools to prevent modifications:

```yaml
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Grep, Glob
model: inherit
---
```

### Domain Expert with Memory

Build institutional knowledge across sessions:

```yaml
---
name: security-advisor
description: Security expert that learns your codebase over time
tools: Read, Grep, Glob, Bash
model: sonnet
memory: user
---

You are a security advisor. Consult your memory for patterns you've seen
before. After completing a review, save what you learned to your memory.
```

### Hook-Guarded Database Agent

Allow Bash but validate commands:

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

### Cost-Optimized Explorer

Use Haiku for fast, cheap exploration:

```yaml
---
name: quick-search
description: Fast codebase search and analysis
tools: Read, Grep, Glob
model: haiku
---
```

### Isolated Worker with Worktree

Run in a separate git worktree to avoid conflicts:

```yaml
---
name: feature-builder
description: Implements features in isolation
model: sonnet
isolation: worktree
---
```

### Skill-Preloaded Specialist

Inject skill content at startup:

```yaml
---
name: api-developer
description: Implement API endpoints following team conventions
skills:
  - api-conventions
  - error-handling-patterns
---

Implement API endpoints. Follow the conventions and patterns from the
preloaded skills.
```

## Example: Complete Subagent File

A production-ready subagent with multiple configuration options:

```markdown
---
name: code-reviewer
description: >
  Expert code review specialist. Proactively reviews code for quality,
  security, and maintainability. Use immediately after writing or
  modifying code.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: sonnet
memory: user
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/log-review-command.sh"
---

You are a senior code reviewer ensuring high standards of code quality
and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is clear and readable
- Functions and variables are well-named
- No duplicated code
- Proper error handling
- No exposed secrets or API keys
- Input validation implemented
- Good test coverage
- Performance considerations addressed

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.

As you review code, update your agent memory with patterns, conventions,
and recurring issues you discover.
```

## Best Practices

1. **Design focused subagents** -- each subagent should excel at one specific
   task rather than being a generalist
2. **Write detailed descriptions** -- Claude uses the description to decide
   when to delegate; vague descriptions lead to poor delegation decisions
3. **Limit tool access** -- grant only necessary permissions for security and
   focus; use `tools` as an allowlist or `disallowedTools` as a denylist
4. **Choose the right model** -- use `haiku` for fast read-only tasks, `sonnet`
   or `opus` for complex analysis; default `inherit` matches the main session
5. **Check into version control** -- share project subagents with your team
   via `.claude/agents/`
6. **Use memory for learning** -- enable persistent memory for subagents that
   benefit from building institutional knowledge over time
7. **Isolate with worktrees** -- use `isolation: worktree` for subagents that
   modify files to avoid conflicts with the main session
8. **Use hooks for guardrails** -- add `PreToolUse` hooks to validate
   operations when you need finer control than the `tools` field provides
9. **Keep system prompts focused** -- subagents receive only their markdown
   body as a system prompt; keep the agent definition markdown under 500
   lines; include clear instructions, a workflow, and any domain knowledge
   they need
10. **Avoid verbose returns** -- subagent results return to the main
    conversation; keep summaries concise to preserve context budget
