---
type: reference
name: settings
title: Claude Code Settings Guide
description: Understanding settings.json configuration for Claude Code behavior
version: "1.0.0"
---

# Claude Code Settings

Claude Code uses `settings.json` files to configure behavior, permissions, and
integrations. This is separate from CLAUDE.md files which provide instructions
and context.

## Settings vs CLAUDE.md

| Aspect | settings.json | CLAUDE.md |
| ------ | ------------- | --------- |
| **Format** | JSON | Markdown |
| **Purpose** | Behavior configuration | Instructions and context |
| **Contains** | Permissions, hooks, model, sandbox | Conventions, workflows, patterns |
| **Scope** | Machine-enforced constraints | LLM-interpreted guidance |
| **Analogy** | App preferences / policy | Onboarding docs |

**Use settings.json for:** What Claude Code CAN do (permissions, tools, model,
sandbox boundaries, hooks, MCP servers)

**Use CLAUDE.md for:** What Claude SHOULD do (conventions, patterns, context,
coding standards)

## Settings File Locations

Settings files are loaded hierarchically with precedence:

```text
Priority (highest to lowest):
1. Managed policies (enterprise, cannot be overridden)
2. Command-line arguments (temporary session overrides)
3. .claude/settings.local.json   # Local overrides (gitignored)
4. .claude/settings.json         # Project settings (shared)
5. ~/.claude/settings.json       # User settings (global)
```

### Location Details

| Location | Scope | Shared |
| -------- | ----- | ------ |
| `~/.claude/settings.json` | User global | No |
| `.claude/settings.json` | Project | Yes (commit to repo) |
| `.claude/settings.local.json` | Project local | No (gitignored) |
| Managed policy settings | Organization | Enforced by IT |

### Managed Settings File Paths

| Platform | Path |
| -------- | ---- |
| macOS | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| Linux/WSL | `/etc/claude-code/managed-settings.json` |
| Windows | `C:\Program Files\ClaudeCode\managed-settings.json` |

These are system-wide paths (not user home directories) that require
administrator privileges for deployment.

## Accessing Settings

Use the `/config` command in Claude Code to open the settings interface:

```text
/config
```

This displays a tabbed interface for viewing and modifying settings.

## Core Settings

### JSON Schema Validation

Enable IDE autocompletion and validation for settings files:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json"
}
```

### Model Override

Override the default Claude model:

```json
{
  "model": "claude-sonnet-4-6"
}
```

Current model identifiers:

- `claude-opus-4-6` -- Most capable model
- `claude-sonnet-4-6` -- Balanced performance and speed
- `claude-haiku-4-5` -- Fastest model

### Available Models

Restrict which models users can select:

```json
{
  "availableModels": ["sonnet", "haiku"]
}
```

### Extended Thinking

Enable always-on extended thinking:

```json
{
  "alwaysThinkingEnabled": true
}
```

### Environment Variables

Set environment variables for every session:

```json
{
  "env": {
    "NODE_ENV": "development",
    "DEBUG": "true"
  }
}
```

### Attribution

Customize git commit and PR attribution:

```json
{
  "attribution": {
    "commit": "Co-Authored-By: Claude <noreply@anthropic.com>",
    "pr": "Generated with Claude Code"
  },
  "includeCoAuthoredBy": false
}
```

### Output Style

Adjust response style:

```json
{
  "outputStyle": "Explanatory"
}
```

## Permissions

Control tool access with allow/deny/ask rules. Rules are evaluated by priority:
**deny** rules are checked first, then **ask**, then **allow**. The
highest-priority matching rule wins, so deny always takes precedence over allow.

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git *)",
      "Bash(npm run *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Read(./.env)",
      "Read(./secrets/**)"
    ],
    "ask": [
      "Bash(git push *)"
    ],
    "additionalDirectories": ["../docs/"],
    "defaultMode": "default"
  }
}
```

### Permission Modes

| Mode | Description |
| ---- | ----------- |
| `default` | Prompts for permission on first use of each tool |
| `acceptEdits` | Auto-accepts file edit permissions for the session |
| `plan` | Plan Mode: analyze only, no modifications |
| `dontAsk` | Auto-denies unless pre-approved via rules |
| `bypassPermissions` | Skips all prompts (containers/VMs only) |

### Permission Rule Syntax

Rules follow the format `Tool` or `Tool(specifier)`:

#### Match All Uses of a Tool

| Rule | Effect |
| ---- | ------ |
| `Bash` | Matches all Bash commands |
| `Read` | Matches all file reads |
| `Write` | Matches all file writes |
| `Edit` | Matches all file edits |
| `WebFetch` | Matches all web fetch requests |
| `Task` | Matches all subagent spawning |

`Bash(*)` is equivalent to `Bash` and matches all Bash commands.

#### Bash Patterns (Wildcard Matching)

Wildcards can appear at any position:

| Rule | Effect |
| ---- | ------ |
| `Bash(npm run build)` | Exact command match |
| `Bash(npm run *)` | Commands starting with `npm run` |
| `Bash(* --version)` | Commands ending with `--version` |
| `Bash(git * main)` | Commands like `git checkout main` |
| `Bash(npm*)` | Matches `npm`, `npx`, etc. (no word boundary) |

The space before `*` matters: `Bash(ls *)` matches `ls -la` but not `lsof`,
while `Bash(ls*)` matches both. Claude Code is aware of shell operators so
`Bash(safe-cmd *)` will not match `safe-cmd && other-cmd`.

#### Read and Edit Patterns (Gitignore Syntax)

Read and Edit rules follow the gitignore specification:

| Pattern | Meaning | Example |
| ------- | ------- | ------- |
| `//path` | Absolute filesystem path | `Read(//Users/alice/secrets/**)` |
| `~/path` | Home directory path | `Read(~/Documents/*.pdf)` |
| `/path` | Relative to settings file | `Edit(/src/**/*.ts)` |
| `path` | Relative to current directory | `Read(*.env)` |

In gitignore patterns, `*` matches files in a single directory while `**`
matches recursively across directories.

#### WebFetch Patterns (Domain Matching)

```json
"WebFetch(domain:example.com)"
```

#### MCP Tool Patterns

| Rule | Effect |
| ---- | ------ |
| `mcp__puppeteer` | All tools from `puppeteer` server |
| `mcp__puppeteer__*` | Wildcard: all tools from `puppeteer` |
| `mcp__puppeteer__puppeteer_navigate` | Specific MCP tool |

#### Skill Patterns

| Rule | Effect |
| ---- | ------ |
| `Skill(name)` | Matches a specific skill invocation |
| `Skill(name *)` | Matches a skill with any arguments |

#### Task (Subagent) Patterns

| Rule | Effect |
| ---- | ------ |
| `Task(Explore)` | Matches the Explore subagent |
| `Task(Plan)` | Matches the Plan subagent |
| `Task(my-custom-agent)` | Matches a custom subagent |

Example -- disable the Explore subagent:

```json
{
  "permissions": {
    "deny": ["Task(Explore)"]
  }
}
```

### Disable Bypass Permissions Mode

Prevent users from using `bypassPermissions` mode (managed settings only):

```json
{
  "permissions": {
    "disableBypassPermissionsMode": "disable"
  }
}
```

## Hooks Configuration

Hooks are user-defined commands that execute at specific lifecycle points.
For complete hook documentation including exit codes, JSON output format,
and security considerations, see knowledge/hooks.md.

### Hook Structure

Hooks use a three-level nesting structure:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/script.sh"
          }
        ]
      }
    ]
  }
}
```

Structure breakdown:

```text
hooks
+-- EventName (e.g., PreToolUse)
|   +-- [array of matcher groups]
|       +-- matcher: regex pattern filtering when the hook fires
|       +-- hooks: [array of hook handlers]
|           +-- type: "command", "prompt", or "agent"
|           +-- command/prompt: the handler to execute
```

### Hook Event Names

Claude Code uses **PascalCase** for all hook events:

| Event | Trigger |
| ----- | ------- |
| `PreToolUse` | Before tool executes (can block) |
| `PostToolUse` | After tool succeeds |
| `PostToolUseFailure` | After tool fails |
| `PermissionRequest` | Permission dialog appears |
| `SessionStart` | Session begins or resumes |
| `SessionEnd` | Session terminates |
| `UserPromptSubmit` | User submits prompt |
| `Notification` | Claude sends notification |
| `Stop` | Claude finishes responding |
| `SubagentStart` | Subagent is spawned |
| `SubagentStop` | Subagent finishes |
| `TeammateIdle` | Agent team: teammate going idle |
| `TaskCompleted` | Agent team: task marked done |
| `ConfigChange` | Configuration file changes |
| `WorktreeCreate` | Worktree being created |
| `WorktreeRemove` | Worktree being removed |
| `PreCompact` | Before context compaction |

### Hook Handler Types

| Type | Description |
| ---- | ----------- |
| `command` | Shell command; receives JSON on stdin |
| `prompt` | LLM-evaluated prompt with `$ARGUMENTS` placeholder |
| `agent` | Agentic verifier with tool access for complex checks |

### Hook Handler Fields

Common fields for all hook types:

| Field | Required | Description |
| ----- | -------- | ----------- |
| `type` | yes | `"command"`, `"prompt"`, or `"agent"` |
| `timeout` | no | Seconds before canceling (command: 600, prompt: 30, agent: 60) |
| `statusMessage` | no | Custom spinner message during execution |
| `once` | no | If `true`, runs only once per session (skills/agents only) |

Additional fields for command hooks:

| Field | Required | Description |
| ----- | -------- | ----------- |
| `command` | yes | Shell command to execute |
| `async` | no | If `true`, runs in background without blocking |

Additional fields for prompt and agent hooks:

| Field | Required | Description |
| ----- | -------- | ----------- |
| `prompt` | yes | Prompt text (`$ARGUMENTS` for input JSON) |
| `model` | no | Model for evaluation (defaults to fast model) |

### Hook Management Settings

```json
{
  "disableAllHooks": false,
  "allowManagedHooksOnly": true
}
```

- `disableAllHooks` -- Temporarily disable all hooks without removing them
- `allowManagedHooksOnly` -- Only allow hooks from managed policy settings
  (managed settings only)

## MCP Server Configuration

MCP (Model Context Protocol) servers extend Claude Code with external tools.

### Transport Types

| Transport | Description |
| --------- | ----------- |
| stdio | Local process communication (default) |
| HTTP | Recommended for remote servers |
| SSE | Server-Sent Events (deprecated, use HTTP) |

### Configuration Scopes

| Scope | Location | Description |
| ----- | -------- | ----------- |
| Local | `~/.claude.json` | User-level MCP servers (note: this is a separate file from `~/.claude/settings.json`) |
| Project | `.mcp.json` | Project-level (supports env var expansion) |
| User settings | `~/.claude/settings.json` | Via MCP management settings |

### MCP Management Settings

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["memory", "github"],
  "disabledMcpjsonServers": ["filesystem"],
  "allowedMcpServers": [
    { "serverName": "github" }
  ],
  "deniedMcpServers": [
    { "serverName": "filesystem" }
  ]
}
```

### MCP Authentication

MCP servers support OAuth 2.0 authentication with pre-configured credentials.
The `MCP_CLIENT_SECRET` environment variable provides the OAuth client secret,
and `MCP_OAUTH_CALLBACK_PORT` sets a fixed callback port.

## Sandbox Configuration

Configure bash command isolation with filesystem and network restrictions:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["git", "docker"],
    "allowUnsandboxedCommands": true,
    "enableWeakerNestedSandbox": false,
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"],
      "allowUnixSockets": ["~/.ssh/agent-socket"],
      "allowAllUnixSockets": false,
      "allowLocalBinding": true,
      "httpProxyPort": 8080,
      "socksProxyPort": 8081
    }
  }
}
```

### Sandbox Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `enabled` | boolean | Enable sandbox for Bash commands |
| `autoAllowBashIfSandboxed` | boolean | Auto-approve sandboxed Bash without prompting |
| `excludedCommands` | string[] | Commands that always run outside the sandbox |
| `allowUnsandboxedCommands` | boolean | Allow escape hatch for failed sandbox commands |
| `enableWeakerNestedSandbox` | boolean | Weaker sandbox for Docker environments |

### Network Configuration

| Field | Type | Description |
| ----- | ---- | ----------- |
| `allowedDomains` | string[] | Domains Bash commands can access |
| `allowUnixSockets` | string[] | Specific Unix sockets to allow |
| `allowAllUnixSockets` | boolean | Allow all Unix socket access |
| `allowLocalBinding` | boolean | Allow binding to local ports |
| `httpProxyPort` | number | Custom HTTP proxy port |
| `socksProxyPort` | number | Custom SOCKS proxy port |

### OS-Level Enforcement

| Platform | Mechanism |
| -------- | --------- |
| macOS | Seatbelt framework |
| Linux/WSL2 | bubblewrap (`bwrap`) |
| WSL1 | Not supported |

## Authentication Settings

### API Key Helper

Custom script for generating auth values (refreshed periodically):

```json
{
  "apiKeyHelper": "~/.claude/get-api-key.sh"
}
```

### OpenTelemetry Headers Helper

Custom script for generating OTel headers:

```json
{
  "otelHeadersHelper": "/bin/generate_otel_headers.sh"
}
```

### Force Login Method

Restrict login to specific methods:

```json
{
  "forceLoginMethod": "claudeai"
}
```

Options: `"claudeai"`, `"console"`

### Organization Selection

Auto-select organization during login:

```json
{
  "forceLoginOrgUUID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### AWS and Cloud Authentication

```json
{
  "awsAuthRefresh": "aws sso login --profile myprofile",
  "awsCredentialExport": "/bin/generate_aws_grant.sh"
}
```

## UI and Display Settings

### Language

Set preferred response language:

```json
{
  "language": "japanese"
}
```

### Turn Duration

Show how long each turn takes:

```json
{
  "showTurnDuration": true
}
```

### Spinner Customization

```json
{
  "spinnerVerbs": {
    "mode": "append",
    "verbs": ["Pondering", "Crafting"]
  },
  "spinnerTipsEnabled": true,
  "spinnerTipsOverride": {
    "excludeDefault": true,
    "tips": ["Use our internal tool X"]
  }
}
```

The `spinnerVerbs.mode` can be `"append"` (add to defaults) or `"replace"`
(override defaults).

### Terminal Display

```json
{
  "terminalProgressBarEnabled": true,
  "prefersReducedMotion": true
}
```

### Status Line

Display custom context in the status line:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

## Enterprise Settings

### Company Announcements

Display messages to all users:

```json
{
  "companyAnnouncements": [
    "Welcome to Acme Corp! Review our code guidelines at docs.acme.com",
    "Reminder: Code reviews required for all PRs"
  ]
}
```

### Managed-Only Settings

These settings are only effective in managed settings files:

| Setting | Description |
| ------- | ----------- |
| `disableBypassPermissionsMode` | Set to `"disable"` to prevent bypass mode |
| `allowManagedPermissionRulesOnly` | Only managed permission rules apply |
| `allowManagedHooksOnly` | Only managed and SDK hooks are allowed |
| `strictKnownMarketplaces` | Restrict plugin marketplace sources |

### Server-Managed Settings (Beta)

A public beta feature for centralized settings management from a server,
beyond file-based managed settings. This allows organizations to push
configuration updates without deploying files to each machine. See official
documentation for current status.

## File and Project Settings

### File Suggestion

Custom `@` file autocomplete:

```json
{
  "fileSuggestion": {
    "type": "command",
    "command": "~/.claude/file-suggestion.sh"
  }
}
```

### Gitignore Respect

Control `@` autocomplete behavior with gitignored files:

```json
{
  "respectGitignore": true
}
```

### Plans Directory

Custom location for plan storage:

```json
{
  "plansDirectory": "./plans"
}
```

### Session Cleanup

Control session cleanup period:

```json
{
  "cleanupPeriodDays": 20
}
```

## Team and Session Settings

### Teammate Mode

Control agent team display (for agent teams feature):

```json
{
  "teammateMode": "in-process"
}
```

### Auto Updates

Select update channel:

```json
{
  "autoUpdatesChannel": "stable"
}
```

## Plugin Management

Control marketplace plugins:

```json
{
  "enabledPlugins": {
    "formatter@acme-tools": true,
    "deployer@acme-tools": true,
    "analyzer@security-plugins": false
  },
  "extraKnownMarketplaces": {
    "acme-tools": {
      "source": {
        "source": "github",
        "repo": "acme-corp/claude-plugins"
      }
    }
  },
  "strictKnownMarketplaces": [
    { "source": "github", "repo": "acme-corp/approved-plugins" }
  ]
}
```

## Environment Variables

Claude Code recognizes these environment variables.

**Most commonly used:**

| Variable | Purpose |
| -------- | ------- |
| `ANTHROPIC_API_KEY` | API key for Claude SDK |
| `ANTHROPIC_MODEL` | Model name to use |
| `CLAUDE_CODE_USE_BEDROCK` | Use AWS Bedrock |
| `CLAUDE_CODE_USE_VERTEX` | Use Google Vertex AI |
| `CLAUDE_CODE_EFFORT_LEVEL` | `low`, `medium`, `high` (Opus 4.6) |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Disable auto memory (0/1) |
| `ENABLE_TOOL_SEARCH` | MCP tool search (`auto`, `true`, `false`, `auto:N`) |

### Authentication

| Variable | Purpose |
| -------- | ------- |
| `ANTHROPIC_API_KEY` | API key for Claude SDK |
| `ANTHROPIC_AUTH_TOKEN` | Custom Authorization header value |
| `ANTHROPIC_CUSTOM_HEADERS` | Custom headers (Name: Value, newline-separated) |
| `ANTHROPIC_FOUNDRY_API_KEY` | Microsoft Foundry API key |
| `ANTHROPIC_FOUNDRY_BASE_URL` | Full Foundry resource URL |
| `AWS_BEARER_TOKEN_BEDROCK` | Bedrock API key |

### Model Configuration

| Variable | Purpose |
| -------- | ------- |
| `ANTHROPIC_MODEL` | Model name to use |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Override Haiku model |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Override Sonnet model |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Override Opus model |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Model for subagents |
| `CLAUDE_CODE_EFFORT_LEVEL` | `low`, `medium`, `high` (Opus 4.6) |
| `MAX_THINKING_TOKENS` | Override extended thinking budget |

### Sandbox and Security

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CODE_SHELL` | Override shell detection (e.g., `bash`, `zsh`) |
| `CLAUDE_CODE_SHELL_PREFIX` | Command prefix for logging/auditing |
| `BASH_DEFAULT_TIMEOUT_MS` | Default bash timeout |
| `BASH_MAX_TIMEOUT_MS` | Maximum bash timeout |
| `BASH_MAX_OUTPUT_LENGTH` | Max bash output characters |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | Return to project dir after bash |

### MCP and Tools

| Variable | Purpose |
| -------- | ------- |
| `ENABLE_TOOL_SEARCH` | MCP tool search (`auto`, `true`, `false`, `auto:N`) |
| `MAX_MCP_OUTPUT_TOKENS` | Max tokens in MCP responses (default: 25000) |
| `MCP_TIMEOUT` | MCP server startup timeout (ms) |
| `MCP_TOOL_TIMEOUT` | MCP tool execution timeout (ms) |
| `MCP_CLIENT_SECRET` | OAuth client secret |
| `MCP_OAUTH_CALLBACK_PORT` | Fixed OAuth callback port |

### Performance and Memory

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Max output tokens (32000 default, max 64000) |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Override file read token limit |
| `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE` | Auto-compaction trigger (1-100%) |
| `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | Exit delay after idle (ms) |

### Features and Behavior

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CODE_SIMPLE` | Minimal mode (bash, file read/edit only) |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Disable auto memory (0/1) |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Disable background tasks |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT` | Disable 1M context window support |
| `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` | Enable prompt suggestions |
| `CLAUDE_CODE_ENABLE_TASKS` | Enable task tracking system |
| `CLAUDE_CODE_ENABLE_TELEMETRY` | Enable OpenTelemetry (1/0) |
| `CLAUDE_CODE_HIDE_ACCOUNT_INFO` | Hide email/org from UI |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | Load CLAUDE.md from extra dirs |

### Network and Proxy

| Variable | Purpose |
| -------- | ------- |
| `HTTP_PROXY` | HTTP proxy server |
| `HTTPS_PROXY` | HTTPS proxy server |
| `NO_PROXY` | Hosts to bypass proxy |
| `CLAUDE_CODE_PROXY_RESOLVES_HOSTS` | Allow proxy DNS resolution |

### Cloud Providers

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CODE_USE_BEDROCK` | Use AWS Bedrock |
| `CLAUDE_CODE_USE_FOUNDRY` | Use Microsoft Foundry |
| `CLAUDE_CODE_USE_VERTEX` | Use Google Vertex AI |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH` | Skip Bedrock auth |
| `CLAUDE_CODE_SKIP_FOUNDRY_AUTH` | Skip Foundry auth |
| `CLAUDE_CODE_SKIP_VERTEX_AUTH` | Skip Vertex auth |

### Telemetry and Reporting

| Variable | Purpose |
| -------- | ------- |
| `DISABLE_TELEMETRY` | Opt out of Statsig telemetry (1/0) |
| `DISABLE_ERROR_REPORTING` | Opt out of Sentry error reporting (1/0) |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Disable all non-essential traffic |
| `DISABLE_COST_WARNINGS` | Disable cost warnings (1/0) |

### UI and Updates

| Variable | Purpose |
| -------- | ------- |
| `DISABLE_AUTOUPDATER` | Disable auto-updates (1/0) |
| `FORCE_AUTOUPDATE_PLUGINS` | Force plugin updates |
| `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` | Disable terminal title updates |
| `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | Disable quality surveys |

### Storage and Configuration

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CONFIG_DIR` | Custom configuration directory |
| `CLAUDE_CODE_TMPDIR` | Override temp directory |
| `CLAUDE_CODE_TASK_LIST_ID` | Share task list across sessions |
| `CLAUDE_CODE_TEAM_NAME` | Agent team name (auto-set) |
| `CLAUDE_CODE_PLAN_MODE_REQUIRED` | Require plan approval (auto-set) |

### Advanced

| Variable | Purpose |
| -------- | ------- |
| `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` | Credential refresh interval |
| `CLAUDE_CODE_CLIENT_CERT` | Client certificate path (mTLS) |
| `CLAUDE_CODE_CLIENT_KEY` | Client key path (mTLS) |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Enable agent teams (1/0) |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Skill metadata character budget |
| `DISABLE_PROMPT_CACHING` | Disable all prompt caching (1/0) |

## Example Configurations

### Developer Workstation

Personal settings for a developer (`~/.claude/settings.json`):

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "claude-sonnet-4-6",
  "env": {
    "EDITOR": "code"
  },
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git *)",
      "Bash(npm *)",
      "Bash(make *)"
    ]
  },
  "outputStyle": "Explanatory",
  "showTurnDuration": true,
  "autoUpdatesChannel": "stable"
}
```

### Project Settings

Shared project configuration (`.claude/settings.json`):

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(npm test)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Bash(npm publish)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npm run typecheck"
          }
        ]
      }
    ]
  },
  "respectGitignore": true
}
```

### Restricted Environment

Locked-down settings for sensitive projects:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Read",
      "Grep",
      "Glob"
    ],
    "deny": [
      "Write",
      "Edit",
      "Bash",
      "WebFetch"
    ],
    "defaultMode": "plan"
  }
}
```

### Sandboxed Development

Sandbox-enabled configuration with network restrictions:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "claude-sonnet-4-6",
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker"],
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org", "registry.yarnpkg.com"]
    }
  },
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit"
    ]
  }
}
```

### Enterprise Managed Policy

Organization-wide managed settings:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl *)",
      "Bash(wget *)"
    ],
    "disableBypassPermissionsMode": "disable",
    "defaultMode": "default"
  },
  "allowManagedPermissionRulesOnly": false,
  "allowManagedHooksOnly": false,
  "companyAnnouncements": [
    "Follow the coding standards at docs.internal.example.com"
  ],
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "allowedDomains": ["github.example.com", "*.internal.example.com"]
    }
  }
}
```

## Best Practices

### Layering Strategy

1. **User settings** (`~/.claude/settings.json`):
   - Personal model preferences
   - Global environment variables
   - Default permissions for personal projects
   - UI preferences (language, spinner, turn duration)

2. **Project settings** (`.claude/settings.json`):
   - Team-agreed permissions
   - Project-specific hooks
   - Shared environment configuration
   - Plugin and MCP server configuration

3. **Local overrides** (`.claude/settings.local.json`):
   - Personal overrides for this project
   - Debug settings
   - Never commit (gitignored)

### Security Considerations

- Never put secrets in settings files (use environment variables or
  `apiKeyHelper`)
- Be careful with broad Bash permissions -- prefer specific patterns
- Use `deny` rules for dangerous operations (they take precedence)
- Consider sandbox for untrusted code with both filesystem and network
  isolation
- Use `allowManagedPermissionRulesOnly` for enterprise lockdown
- Bash permission patterns that constrain arguments are fragile; use
  WebFetch domain rules or PreToolUse hooks for URL filtering

### Common Patterns

**Allow only specific npm scripts:**

```json
{
  "permissions": {
    "allow": ["Bash(npm run *)"],
    "deny": ["Bash(npm *)"]
  }
}
```

**Auto-format on file write:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs -I {} prettier --write {}"
          }
        ]
      }
    ]
  }
}
```

**Block writes to sensitive files:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 2 || exit 0"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting

### Settings Not Applied

**Check precedence:** Higher-priority settings override lower ones.
Managed settings cannot be overridden. Use `/config` to view effective
settings.

**Check JSON validity:** Settings files must be valid JSON. Use the
`$schema` field for IDE validation.

### Permission Denied

**Check patterns:** Permission patterns must match the tool invocation.

```json
{
  "permissions": {
    "allow": ["Bash(git status)"]
  }
}
```

This only allows exactly `git status`. Use wildcards for flexibility:

```json
{
  "permissions": {
    "allow": ["Bash(git *)"]
  }
}
```

**Check deny rules:** Deny rules are evaluated first and take precedence
over allow rules.

### Hooks Not Running

**Check event name:** Hook events use PascalCase (`PreToolUse`, not
`preToolExecution`).

**Check structure:** Hooks require the nested structure with a `hooks`
array and `type` field:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "echo test"
          }
        ]
      }
    ]
  }
}
```

**Check snapshot behavior:** Hooks are captured at session startup. Changes
to hook configuration during a session require review in the `/hooks` menu
before they take effect.

### Sandbox Issues

**Command fails in sandbox:** Add the command to `excludedCommands` to run
it outside the sandbox, or check if it needs network access to an
unlisted domain.

**Network access blocked:** Add the domain to `sandbox.network.allowedDomains`.

**Linux sandbox not available:** Install bubblewrap and socat:
`sudo apt-get install bubblewrap socat` (Debian/Ubuntu) or
`sudo dnf install bubblewrap socat` (Fedora).
