---
type: reference
title: Claude Code Hooks Guide
description: Understanding hooks for deterministic control in Claude Code
---

# Claude Code Hooks

Hooks are **user-defined shell commands** that execute at specific points in
Claude Code's lifecycle. They provide deterministic control - ensuring certain
actions always happen rather than relying on the LLM to choose.

## Hooks vs Other Extension Types

| Aspect | Hooks | Commands/Skills |
|--------|-------|-----------------|
| **Trigger** | Automatic (lifecycle events) | Manual (user invocation) |
| **Control** | Deterministic | LLM-guided |
| **Purpose** | Enforcement, automation | Workflows, expertise |
| **Execution** | Shell commands | Claude orchestration |

**Use Hooks for:** Things that MUST happen (formatting, logging, blocking)
**Use Commands/Skills for:** Things that SHOULD happen (workflows, analysis)

## Hook Lifecycle Events

Claude Code supports 10 hook events:

### Tool Lifecycle

| Event | Trigger | Use Case |
|-------|---------|----------|
| `PreToolUse` | Before tool executes | Block dangerous operations, validate inputs |
| `PostToolUse` | After tool completes | Format code, log actions, trigger builds |
| `PermissionRequest` | Permission dialog appears | Auto-approve safe patterns |

### Session Lifecycle

| Event | Trigger | Use Case |
|-------|---------|----------|
| `SessionStart` | Session begins/resumes | Load context, set environment |
| `SessionEnd` | Session terminates | Cleanup, save state |

### Prompt Lifecycle

| Event | Trigger | Use Case |
|-------|---------|----------|
| `UserPromptSubmit` | User submits prompt | Validate input, inject context |
| `Notification` | Claude sends notification | Custom alerts, integrations |
| `Stop` | Claude finishes responding | Post-processing, notifications |

### Agent Lifecycle

| Event | Trigger | Use Case |
|-------|---------|----------|
| `SubagentStop` | Subagent task completes | Aggregate results, cleanup |
| `PreCompact` | Before context compaction | Save important context |

## Configuration Structure

Hooks are configured in settings.json files:

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

### Structure Breakdown

```text
hooks
├── EventName (e.g., PreToolUse)
│   └── [array of hook configurations]
│       ├── matcher: which tools trigger this hook
│       └── hooks: [array of commands to run]
│           ├── type: "command"
│           └── command: shell command to execute
```

## Matcher Patterns

Matchers determine which tools trigger hooks:

| Pattern | Matches |
|---------|---------|
| `"Write"` | Only Write tool |
| `"Edit\|Write"` | Edit OR Write tools |
| `"Bash"` | Bash tool |
| `"*"` | All tools (universal) |

### Tool-Specific Matchers

For tools with arguments, match on the full tool signature:

```json
{
  "matcher": "Bash(git:*)",
  "hooks": [...]
}
```

## Hook Execution

### Input (stdin)

Hooks receive JSON via stdin containing event context:

```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.ts",
    "content": "..."
  },
  "session_id": "...",
  "project_dir": "/path/to/project"
}
```

### Environment Variables

Hooks have access to:

| Variable | Description |
|----------|-------------|
| `CLAUDE_PROJECT_DIR` | Current project directory |
| `CLAUDE_SESSION_ID` | Current session identifier |

### Exit Codes

For `PreToolUse` and `PermissionRequest`:

| Exit Code | Meaning |
|-----------|---------|
| `0` | Allow/approve |
| Non-zero | Block/deny |

### Output

Hooks can:

- Write to stdout/stderr (logged)
- Write to files
- Trigger external systems
- Return JSON for feedback

## Common Patterns

### Auto-Format on Write

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

### Block Sensitive Files

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 1 || exit 0"
          }
        ]
      }
    ]
  }
}
```

### Command Logging

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"\\(.tool_input.command) - \\(.tool_input.description // \"No description\")\"' >> ~/.claude/bash-log.txt"
          }
        ]
      }
    ]
  }
}
```

### Desktop Notifications

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.message' | xargs -I {} osascript -e 'display notification \"{}\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

## Security Considerations

**Hooks run with your environment's full credentials and permissions.**

### Risks

- Hooks execute automatically during the agent loop
- They have access to your shell environment
- Malicious hooks can exfiltrate data
- No sandboxing by default

### Best Practices

1. **Review before registering** - Treat hooks as executable code
2. **Audit third-party hooks** - Don't blindly copy hook configurations
3. **Limit scope** - Use specific matchers, not `*` when possible
4. **Log sensitive hooks** - Track what's running
5. **Test in isolation** - Verify hook behavior before production use

### Enterprise Considerations

Enterprise settings can enforce hooks that users cannot override:

- Audit logging for compliance
- Security scanning requirements
- Blocking dangerous patterns organization-wide

## Hook Configuration Locations

Hooks follow settings.json precedence:

```text
Priority (highest to lowest):
1. Enterprise managed policies
2. .claude/settings.local.json (project local)
3. .claude/settings.json (project shared)
4. ~/.claude/settings.json (user global)
```

## Debugging Hooks

### Test hook command standalone

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"test.ts"}}' | your-hook-command
```

### Check exit codes

```bash
echo '...' | your-hook-command; echo "Exit code: $?"
```

### View hook logs

Check Claude Code's output for hook execution results.

## When to Use Hooks

### Good Use Cases

- **Formatting**: Auto-run prettier, gofmt, black after edits
- **Validation**: Block writes to protected files
- **Logging**: Audit trail for compliance
- **Notifications**: Custom alerts when Claude needs input
- **Integration**: Trigger CI, update external systems

### Poor Use Cases

- **Complex logic**: Use Skills instead
- **User interaction**: Hooks are non-interactive
- **Conditional workflows**: Use Commands instead
- **Domain expertise**: Use Agents instead

## Hooks vs Permissions

| Aspect | Hooks | Permissions |
|--------|-------|-------------|
| **Mechanism** | Run code on events | Allow/deny rules |
| **Flexibility** | Can inspect content | Pattern matching only |
| **Action** | Execute anything | Block or allow |
| **Use when** | Need custom logic | Simple access control |

Use permissions for simple allow/deny. Use hooks when you need to inspect
content, run formatters, or execute custom logic.
