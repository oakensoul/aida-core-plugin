# Claude Code Documentation Research Findings

Research conducted: 2026-02-24
Source: https://code.claude.com/docs/ (57 documentation pages)
Compared against: agents/claude-code-expert/knowledge/ (8 files)

---

## 1. New Features Not Covered in Our Knowledge Base

### 1.1 Agent Teams (Experimental)

The official docs describe a full **agent teams** system (enabled via
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) that is not covered anywhere
in our knowledge base. Key details:

- **Architecture**: Team lead + teammates, each a separate Claude Code
  instance with its own context window
- **Shared task list**: Tasks with pending/in_progress/completed states,
  dependency tracking, file-lock-based claiming
- **Inter-agent messaging**: Direct message and broadcast between teammates
- **Display modes**: In-process (Shift+Down cycling) or tmux/iTerm2 split panes
- **Team hooks**: `TeammateIdle` and `TaskCompleted` events for quality gates
- **Plan approval**: Teammates can require lead approval before implementing
- **Config location**: `~/.claude/teams/{team-name}/config.json`

### 1.2 LSP Server Integration

Plugins can now bundle **Language Server Protocol (LSP)** servers via
`.lsp.json` for real-time code intelligence:

- Diagnostics, go-to-definition, find references, hover info
- Configuration via `.lsp.json` or inline in `plugin.json` under `lspServers`
- Pre-built plugins available for Pyright, TypeScript LSP, rust-analyzer
- Extensive configuration options: transport, timeouts, restart behavior

### 1.3 Auto Memory System

A persistent auto memory system exists that our knowledge base does not cover:

- Claude automatically saves project patterns, debugging insights,
  architecture notes, and preferences
- Stored at `~/.claude/projects/<project>/memory/`
- `MEMORY.md` entrypoint (first 200 lines loaded into context)
- Topic files loaded on demand (e.g., `debugging.md`, `api-conventions.md`)
- Controlled via `CLAUDE_CODE_DISABLE_AUTO_MEMORY` env var
- Separate from CLAUDE.md instruction files

### 1.4 Modular Rules (`.claude/rules/`)

A new rules system not documented in our knowledge:

- `.claude/rules/*.md` files for modular, topic-specific instructions
- Supports **path-specific rules** via YAML frontmatter `paths` field with
  glob patterns
- Recursive subdirectory discovery
- Symlink support for shared cross-project rules
- User-level rules at `~/.claude/rules/`
- Priority: project rules override user-level rules

### 1.5 CLAUDE.local.md

Local memory files (`CLAUDE.local.md`) are automatically gitignored and
serve as personal project-specific preferences. Not covered in our
`claude-md-files.md`.

### 1.6 Plugin Output Styles

Plugins can include `outputStyles/` directories and reference them via
the `outputStyles` field in `plugin.json`. Not documented in our knowledge.

### 1.7 Plugin Settings (settings.json in plugins)

Plugins can ship a `settings.json` at their root with default configuration.
Currently the `agent` key is supported, which activates a plugin agent as
the main thread. This is a significant new capability.

### 1.8 Agent Skills Open Standard

Skills now follow the [Agent Skills](https://agentskills.io) open standard,
which works across multiple AI tools. Claude Code extends it with additional
features. Our knowledge does not reference this standard.

### 1.9 MCP Tool Search

Automatic tool search that defers MCP tool loading when definitions exceed
context thresholds:

- Auto mode activates at 10% of context window
- Configurable via `ENABLE_TOOL_SEARCH` env var
- Requires Sonnet 4+ or Opus 4+ models

### 1.10 MCP Resources and Prompts

- Resources can be referenced via `@server:protocol://resource/path` syntax
- MCP prompts become available as `/mcp__servername__promptname` commands
- Neither feature is documented in our knowledge base

### 1.11 Managed MCP Configuration

Enterprise-level MCP management via `managed-mcp.json`:

- Exclusive control or policy-based allowlists/denylists
- Server filtering by name, command, or URL pattern
- System-level deployment paths for macOS/Linux/Windows

### 1.12 Desktop App and Web (Cloud) Sessions

Claude Code now runs as a desktop app and in the browser at claude.ai/code.
Session teleportation between surfaces via `/teleport` and `/desktop`.

### 1.13 Chrome Extension

Claude Code has a Chrome extension for debugging live web applications.
Not referenced in our knowledge.

### 1.14 Slack Integration

Claude Code can be used from Slack via `@Claude` mentions, producing PRs
from bug reports. Not in our knowledge base.

### 1.15 Fast Mode

A "fast mode" toggle (`/fast`) that uses the same model but optimizes for
faster output. Not documented in our knowledge.

### 1.16 Checkpointing

A checkpointing system for sessions. Not in our knowledge base.

### 1.17 Output Styles

Configurable output styles via `outputStyle` setting (e.g., "concise",
"Explanatory"). Not documented.

### 1.18 Server-Managed Settings

A public beta feature for server-managed settings. Not documented.

---

## 2. Gaps in Our Knowledge Base

### 2.1 Skills Documentation (skills.md - MISSING)

We have **no dedicated knowledge file for skills**. This is a critical gap.
The official docs have extensive coverage:

- Skill locations: Enterprise, Personal, Project, Plugin scopes
- Frontmatter reference: `name`, `description`, `argument-hint`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`,
  `context`, `agent`, `hooks`
- String substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`,
  `${CLAUDE_SESSION_ID}`
- Dynamic context injection: `!`command`` syntax for shell preprocessing
- `context: fork` for running skills in subagents
- Agent types: `Explore`, `Plan`, `general-purpose`, or custom agents
- Skill discovery from nested directories and `--add-dir` paths
- `SLASH_COMMAND_TOOL_CHAR_BUDGET` for context budget control
- Integration with Agent Skills open standard

### 2.2 Subagents Documentation (subagents.md - MISSING)

We have no dedicated knowledge file for subagents. The official docs cover:

- Built-in subagents: Explore (Haiku, read-only), Plan, general-purpose,
  Bash, statusline-setup, Claude Code Guide
- Subagent scopes: `--agents` CLI flag > `.claude/agents/` > `~/.claude/agents/` > plugins
- Frontmatter fields: `name`, `description`, `tools`, `disallowedTools`,
  `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`,
  `memory`, `background`, `isolation`
- CLI-defined subagents via `--agents` JSON flag
- Permission modes: `default`, `acceptEdits`, `dontAsk`,
  `bypassPermissions`, `plan`
- Persistent memory for subagents with `user`/`project`/`local` scopes
- Background vs foreground execution, Ctrl+B to background
- Worktree isolation via `isolation: "worktree"`
- `/agents` command for interactive management
- `Task(agent_type)` syntax for restricting spawnable subagents
- Hooks in subagent frontmatter
- Subagent resume capability

### 2.3 Plugin Hooks Location

Our knowledge says hooks are in `settings.json`. The official plugin docs
show plugins use `hooks/hooks.json` at the plugin root, plus the hooks
can be inline in `plugin.json`. We need to document this distinction.

### 2.4 Plugin MCP Servers

Plugins can bundle MCP servers via `.mcp.json` at the plugin root or
inline in `plugin.json` under `mcpServers`. Not covered in our
plugin-development.md.

### 2.5 Plugin CLI Commands

The official docs describe extensive CLI commands for plugin management:
`claude plugin install`, `uninstall`, `enable`, `disable`, `update`,
`validate`. Our knowledge references `/aida plugin` commands but not the
native `claude plugin` CLI.

### 2.6 Plugin Caching and File Resolution

Marketplace plugins are copied to `~/.claude/plugins/cache`. Path
traversal limitations and symlink handling are documented officially
but not in our knowledge.

### 2.7 MCP Configuration Details

Our `settings.md` covers MCP minimally. The official docs have extensive
coverage of:

- Three transport types: stdio, HTTP (recommended), SSE (deprecated)
- Three scopes: local (default), project (`.mcp.json`), user
- OAuth 2.0 authentication with pre-configured credentials
- `claude mcp add-json` for JSON configuration
- `claude mcp add-from-claude-desktop` for importing
- `claude mcp serve` (Claude Code as MCP server)
- Environment variable expansion in `.mcp.json`
- Dynamic tool updates via `list_changed` notifications
- MCP output limits and `MAX_MCP_OUTPUT_TOKENS`

### 2.8 Hooks: New Event Types

Our hooks.md lists 10 events. The official docs now document **17 events**:

| Our Knowledge | Official Docs |
|---|---|
| PreToolUse | PreToolUse |
| PostToolUse | PostToolUse |
| - | **PostToolUseFailure** (NEW) |
| PermissionRequest | PermissionRequest |
| SessionStart | SessionStart |
| SessionEnd | SessionEnd |
| UserPromptSubmit | UserPromptSubmit |
| Notification | Notification |
| Stop | Stop |
| SubagentStop | SubagentStop |
| - | **SubagentStart** (NEW) |
| PreCompact | PreCompact |
| - | **TeammateIdle** (NEW) |
| - | **TaskCompleted** (NEW) |
| - | **ConfigChange** (NEW) |
| - | **WorktreeCreate** (NEW) |
| - | **WorktreeRemove** (NEW) |

### 2.9 Hooks: New Hook Types

Our knowledge only covers `command` type hooks. The official docs show
three hook types:

- `command`: Shell commands (what we document)
- `prompt`: LLM-evaluated prompts with `$ARGUMENTS` placeholder (NEW)
- `agent`: Agentic verifiers with tools for complex verification (NEW)

### 2.10 Hooks: Async Hooks

The official docs describe async hook support. Not in our knowledge.

### 2.11 Hooks: JSON Output Format

The official docs show a structured JSON output format with
`hookSpecificOutput` containing `permissionDecision` and
`permissionDecisionReason`. Our knowledge uses exit codes only, which
is a simplified view.

### 2.12 Permission Rule Syntax

The official docs describe detailed permission rule syntax including
`Skill(name)`, `Skill(name *)`, `Task(agent-name)`, and
`WebFetch(domain:example.com)`. Our knowledge covers basic patterns
only.

### 2.13 Context Loading Model

The features-overview page has a detailed context loading model showing
when each feature type loads and its context cost. This understanding
is missing from our knowledge base.

---

## 3. Outdated Information in Our Knowledge Files

### 3.1 settings.md - Hook Event Names

Our `settings.md` uses `preToolExecution` and `postToolExecution` as
hook event names. The official docs use `PreToolUse` and `PostToolUse`.
These are **PascalCase** in the official docs, suggesting our camelCase
names may be outdated or incorrect.

### 3.2 settings.md - Hook Configuration Structure

Our `settings.md` shows a simplified hook structure:
```json
{
  "hooks": {
    "preToolExecution": [
      { "matcher": "Write", "command": "echo test" }
    ]
  }
}
```

The official structure is:
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

Note the extra nesting level (`hooks` array inside matcher group) and
the `type` field in the hook handler.

### 3.3 settings.md - Outdated Model Names

Our settings.md references `claude-sonnet-4-5-20250514`. Current models
include `claude-sonnet-4-6`, `claude-opus-4-6`, and `claude-haiku-4-5`.

### 3.4 settings.md - Missing Settings Fields

Many settings fields from the official docs are missing from our
knowledge. Notable additions include:

- `$schema` for JSON schema validation
- `attribution` for git commit/PR attribution customization
- `availableModels` for restricting model selection
- `fileSuggestion` for custom `@` file autocomplete
- `respectGitignore` for `@` autocomplete behavior
- `outputStyle` for response style
- `companyAnnouncements` for enterprise announcements
- `alwaysThinkingEnabled` for extended thinking
- `plansDirectory` for plan storage
- `showTurnDuration` for turn timing display
- `spinnerVerbs` and `spinnerTipsOverride` for UI customization
- `language` for response language preference
- `autoUpdatesChannel` for update channel selection
- `teammateMode` for agent team display
- `cleanupPeriodDays` for session cleanup
- `sandbox` with extensive network and filesystem configuration

### 3.5 settings.md - Sandbox Configuration

Our knowledge has a minimal sandbox example. The official docs show
extensive sandbox configuration including:

- `autoAllowBashIfSandboxed`
- `excludedCommands`
- `allowUnsandboxedCommands`
- Network configuration: `allowedDomains`, `allowUnixSockets`,
  `allowLocalBinding`, `httpProxyPort`, `socksProxyPort`

### 3.6 claude-md-files.md - Missing Enterprise Paths

Our knowledge shows macOS Enterprise path as
`/Library/Application Support/ClaudeCode/CLAUDE.md`. The official docs
confirm this and add Windows path:
`C:\Program Files\ClaudeCode\CLAUDE.md` (differs from our
`C:\ProgramData\ClaudeCode\CLAUDE.md`).

### 3.7 claude-md-files.md - Missing Import Features

The official docs mention:
- Import approval dialog for external imports (one-time per project)
- `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` env var for `--add-dir`
- `@~/.claude/my-project-instructions.md` home-directory imports
- Worktree-specific behavior for `CLAUDE.local.md`

### 3.8 index.md - Outdated External Resources

Our index.md references:
- `https://docs.anthropic.com/en/docs/claude-code` (old URL)
- `https://github.com/anthropics/claude-code/tree/main/sdk` (old SDK URL)

Current URLs are:
- `https://code.claude.com/docs/en/overview`
- Agent SDK: `https://platform.claude.com/docs/en/agent-sdk/overview`

### 3.9 plugin-development.md - Missing Plugin Features

Our plugin-development.md is missing:
- `.lsp.json` for LSP servers
- `.mcp.json` for MCP servers
- `hooks/hooks.json` for hooks (shows hooks in settings.json only)
- `settings.json` for default plugin settings
- `outputStyles/` directory
- `${CLAUDE_PLUGIN_ROOT}` environment variable
- Plugin caching to `~/.claude/plugins/cache`
- `claude plugin` CLI commands (install, uninstall, etc.)
- `--plugin-dir` flag for development testing

### 3.10 extension-types.md - Outdated Plugin Invocation

Our knowledge says plugins are invoked via `/plugin add`. The official
system uses `claude plugin install` CLI or `/plugin` in interactive mode.

---

## 4. Claude Cowork / Agent Teams and Plugin System

### 4.1 Agent Teams Architecture

The "Cowork" concept is now called **Agent Teams**. Key architectural
details:

- **Experimental**: Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **Components**: Team lead, teammates, shared task list, mailbox
- **Coordination**: Task dependencies, self-claiming, file-lock-based
  claiming
- **Communication**: Direct messaging and broadcast between agents
- **Display**: In-process mode or tmux/iTerm2 split panes
- **Hooks**: `TeammateIdle` and `TaskCompleted` for quality enforcement
- **Limitations**: No session resumption for in-process teammates,
  one team per session, no nested teams, fixed leader

### 4.2 Plugin System Updates

The plugin system has matured significantly:

- **Discovery and Marketplaces**: Dedicated pages for discovering plugins
  and creating plugin marketplaces
- **Marketplace sources**: GitHub repos, Git repos, URLs, NPM packages,
  file paths, directory paths, host patterns
- **Managed marketplace restrictions**: `strictKnownMarketplaces` in
  managed settings for enterprise lockdown
- **Plugin scopes**: user, project, local, managed
- **CLI management**: Full `claude plugin` subcommands
- **Component types expanded**: Now includes skills, agents, hooks,
  MCP servers, LSP servers, output styles, and settings
- **`commands/` directory**: Still supported alongside `skills/` for
  backward compatibility

---

## 5. TypeScript/Node SDK and TS-Based Plugin Development

### 5.1 Agent SDK

The official docs reference an **Agent SDK** at
`https://platform.claude.com/docs/en/agent-sdk/overview` for building
custom agents powered by Claude Code's tools. This is separate from
Claude Code itself and provides:

- Full control over orchestration, tool access, and permissions
- Programmatic use of Claude Code capabilities
- Custom agent workflows

### 5.2 Headless/Programmatic Mode

Claude Code can be run programmatically via `claude -p` (print mode)
or the headless SDK. This enables:

- CI/CD integration
- Scripted automation
- Piping input/output
- JSON output mode

### 5.3 Plugin Development is Markdown-Based (Not TypeScript)

Importantly, **Claude Code plugins are NOT TypeScript/Node packages**.
The plugin system is entirely markdown-based:

- Skills are `SKILL.md` files with YAML frontmatter
- Agents are markdown files with YAML frontmatter
- Hooks are shell commands defined in JSON
- MCP servers are configured via JSON
- No TypeScript compilation or Node.js build step required
- Scripts can be in any language (Python, Bash, etc.)

This is a key distinction from typical IDE extension systems. Our
knowledge base should clarify this to avoid confusion.

### 5.4 MCP Servers Can Be TypeScript/Node

While plugins themselves are not TypeScript, MCP servers bundled with
plugins CAN be TypeScript/Node applications:

- `npx -y @some/mcp-server` pattern for Node-based MCP servers
- MCP SDK available at `https://modelcontextprotocol.io/quickstart/server`
- Full MCP protocol support (stdio, HTTP, SSE transports)

---

## 6. Impact Assessment for Issue-31 Decomposition

### High Priority for Decomposition

1. **Skills knowledge file is missing** - Critical for decomposing the
   management skill. We need a dedicated `skills.md` in knowledge/.
2. **Subagents knowledge file is missing** - Critical for understanding
   how subagents relate to the decomposition.
3. **Hook event names and structure are outdated** - Must fix before
   generating new hook configurations.
4. **Plugin structure has expanded** - Need to account for LSP, MCP,
   settings.json, and outputStyles in plugin scaffolding.

### Medium Priority

5. **Agent teams are not documented** - New extension type that our
   framework should acknowledge even if we don't manage it.
6. **Settings documentation significantly outdated** - Many new settings
   fields and corrected structures needed.
7. **MCP documentation needs expansion** - Transport types, scopes,
   OAuth, and plugin MCP bundling.
8. **Auto memory system** - New feature that affects context loading model.
9. **Modular rules (`.claude/rules/`)** - New feature for organizing
   project instructions.

### Lower Priority

10. **External resource URLs outdated** - Quick fix.
11. **Desktop/Web/Chrome/Slack integrations** - Informational, not
    directly affecting decomposition.
12. **Fast mode, checkpointing, output styles** - Nice to know, not
    critical for decomposition work.

---

## 7. Recommendations for Knowledge Base Updates

### Immediate (Before Decomposition)

1. Create `skills.md` - Document skill types, frontmatter fields,
   substitutions, context modes, and discovery
2. Create `subagents.md` - Document built-in agents, scopes, frontmatter,
   memory, hooks, and background execution
3. Fix `hooks.md` - Update event names, add new events, document new
   hook types (prompt, agent), add JSON output format
4. Fix `settings.md` - Correct hook structure, update model names, add
   missing settings fields

### Soon After

5. Update `plugin-development.md` - Add LSP, MCP, hooks, settings,
   outputStyles, CLI commands, CLAUDE_PLUGIN_ROOT
6. Update `claude-md-files.md` - Add auto memory, CLAUDE.local.md,
   rules system, import features
7. Update `extension-types.md` - Add agent teams, correct plugin
   invocation, add LSP servers
8. Update `index.md` - Fix external resource URLs, add new knowledge
   files to index
9. Update `framework-design-principles.md` - Acknowledge agent teams
   as a new extension type

### Future

10. Create `agent-teams.md` - Document the full agent teams system
11. Create `mcp.md` - Dedicated MCP configuration guide
12. Update design-patterns.md - Add patterns for LSP servers, MCP
    bundling, and plugin settings
