---
type: reference
title: Claude Code Settings Guide
description: Understanding settings.json configuration for Claude Code behavior
---

# Claude Code Settings

Claude Code uses `settings.json` files to configure behavior, permissions, and
integrations. This is separate from CLAUDE.md files which provide instructions
and context.

## Settings vs CLAUDE.md

| Aspect | settings.json | CLAUDE.md |
|--------|---------------|-----------|
| **Format** | JSON | Markdown |
| **Purpose** | Behavior configuration | Instructions & context |
| **Contains** | Permissions, hooks, model | Conventions, workflows |
| **Analogy** | App preferences | Onboarding docs |

**Use settings.json for:** What Claude Code CAN do (permissions, tools, model)
**Use CLAUDE.md for:** What Claude SHOULD do (conventions, patterns, context)

## Settings File Locations

Settings files are loaded hierarchically with precedence:

```text
Priority (highest to lowest):
1. Enterprise managed policies
2. Command-line arguments
3. .claude/settings.local.json   # Local overrides (gitignored)
4. .claude/settings.json         # Project settings (shared)
5. ~/.claude/settings.json       # User settings (global)
```

### Location Details

| Location | Scope | Shared |
|----------|-------|--------|
| `~/.claude/settings.json` | User global | No |
| `.claude/settings.json` | Project | Yes (commit to repo) |
| `.claude/settings.local.json` | Project local | No (gitignored) |
| Enterprise managed | Organization | Enforced |

## Accessing Settings

Use the `/config` command in Claude Code to open the settings interface:

```
/config
```

This displays a tabbed interface for viewing and modifying settings.

## Core Settings

### Model Override

Override the default Claude model:

```json
{
  "model": "claude-sonnet-4-5-20250514"
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

### Permissions

Control tool access with allow/deny/ask rules:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git:*)",
      "Bash(npm:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)"
    ]
  }
}
```

Permission patterns:
- `"Read"` - Allow all Read operations
- `"Bash(git:*)"` - Allow git commands
- `"Bash(npm install)"` - Allow specific command
- `"WebFetch"` - Allow web fetching

### Hooks

Run commands before/after tool execution:

```json
{
  "hooks": {
    "preToolExecution": [
      {
        "matcher": "Write",
        "command": "echo 'Writing file...'"
      }
    ],
    "postToolExecution": [
      {
        "matcher": "Bash",
        "command": "echo 'Command completed'"
      }
    ]
  }
}
```

Hook types:
- `preToolExecution` - Run before a tool executes
- `postToolExecution` - Run after a tool completes

## Advanced Settings

### Custom Status Line

Display custom context in the status line:

```json
{
  "statusLine": {
    "command": "git branch --show-current",
    "interval": 30000
  }
}
```

### Output Style

Adjust system prompt behavior:

```json
{
  "outputStyle": "concise"
}
```

### Sandbox Configuration

Configure bash isolation (filesystem/network restrictions):

```json
{
  "sandbox": {
    "enabled": true,
    "allowedPaths": ["/workspace", "/tmp"],
    "networkAccess": false
  }
}
```

### Plugin Management

Control marketplace plugins:

```json
{
  "enabledPlugins": ["plugin-name"],
  "extraKnownMarketplaces": ["https://custom-marketplace.example.com"]
}
```

## Authentication Settings

### API Key Helper

Custom script for generating auth values:

```json
{
  "apiKeyHelper": "~/.claude/get-api-key.sh"
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
  "forceLoginOrgUUID": "org-uuid-here"
}
```

## Environment Variables

Claude Code recognizes these environment variables:

### Authentication

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | API key for authentication |
| `ANTHROPIC_AUTH_TOKEN` | Auth token (alternative) |

### Behavior

| Variable | Purpose |
|----------|---------|
| `BASH_DEFAULT_TIMEOUT_MS` | Default bash command timeout |
| `DISABLE_TELEMETRY` | Disable usage telemetry |

### Network

| Variable | Purpose |
|----------|---------|
| `HTTP_PROXY` | HTTP proxy server |
| `HTTPS_PROXY` | HTTPS proxy server |
| `NO_PROXY` | Hosts to bypass proxy |

## Example Configurations

### Developer Workstation

Personal settings for a developer:

```json
{
  "model": "claude-sonnet-4-5-20250514",
  "env": {
    "EDITOR": "code"
  },
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(make:*)"
    ]
  }
}
```

### Project Settings

Shared project configuration:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run:*)",
      "Bash(npm test)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Bash(npm publish)"
    ]
  },
  "hooks": {
    "preToolExecution": [
      {
        "matcher": "Write(*.ts)",
        "command": "npm run typecheck"
      }
    ]
  }
}
```

### Restricted Environment

Locked-down settings for sensitive projects:

```json
{
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
    ]
  },
  "sandbox": {
    "enabled": true,
    "networkAccess": false
  }
}
```

## Best Practices

### Layering Strategy

1. **User settings** (`~/.claude/settings.json`):
   - Personal model preferences
   - Global environment variables
   - Default permissions for personal projects

2. **Project settings** (`.claude/settings.json`):
   - Team-agreed permissions
   - Project-specific hooks
   - Shared environment configuration

3. **Local overrides** (`.claude/settings.local.json`):
   - Personal overrides for this project
   - Debug settings
   - Never commit (gitignored)

### Security Considerations

- Never put secrets in settings files (use environment variables)
- Be careful with broad Bash permissions
- Use `deny` rules for dangerous operations
- Consider sandbox for untrusted code

### Common Patterns

**Allow only specific npm scripts:**
```json
{
  "permissions": {
    "allow": ["Bash(npm run:*)"],
    "deny": ["Bash(npm:*)"]
  }
}
```

**Pre-commit hook equivalent:**
```json
{
  "hooks": {
    "preToolExecution": [
      {
        "matcher": "Bash(git commit:*)",
        "command": "npm run lint && npm test"
      }
    ]
  }
}
```

## Troubleshooting

### Settings Not Applied

**Check precedence:** Higher-priority settings override lower ones.

```bash
# View effective settings
/config
```

### Permission Denied

**Check patterns:** Permission patterns must match exactly.

```json
{
  "permissions": {
    "allow": ["Bash(git status)"]  // Only allows exactly "git status"
  }
}
```

Use wildcards for flexibility:
```json
{
  "permissions": {
    "allow": ["Bash(git:*)"]  // Allows all git commands
  }
}
```

### Hooks Not Running

**Check matcher:** Hooks only run if the matcher pattern matches the tool.

```json
{
  "hooks": {
    "preToolExecution": [
      {
        "matcher": "Write",      // Matches all Write operations
        "command": "echo test"
      }
    ]
  }
}
```
