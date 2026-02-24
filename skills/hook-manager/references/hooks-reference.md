---
type: reference
name: hooks-reference
title: Hooks Reference
description: >-
  Reference documentation for Claude Code hook
  operations including lifecycle events, hook types,
  configuration format, and usage examples.
version: 0.1.0
---

# Hooks Reference

Claude Code hooks are shell commands that execute at
specific lifecycle events. They provide deterministic
control -- ensuring certain actions always happen rather
than relying on the LLM.

## Lifecycle Events

Claude Code supports 10 hook events across four
lifecycle categories.

### Tool Lifecycle

| Event | Trigger | Use Case |
| --- | --- | --- |
| `PreToolUse` | Before tool executes | Block ops, validate |
| `PostToolUse` | After tool completes | Format, log, build |
| `PermissionRequest` | Permission dialog | Auto-approve safe |

### Session Lifecycle

| Event | Trigger | Use Case |
| --- | --- | --- |
| `SessionStart` | Session begins | Load context |
| `SessionEnd` | Session ends | Cleanup, save state |

### Prompt Lifecycle

| Event | Trigger | Use Case |
| --- | --- | --- |
| `UserPromptSubmit` | User submits | Validate, inject |
| `Notification` | Claude notifies | Custom alerts |
| `Stop` | Claude finishes | Post-processing |

### Agent Lifecycle

| Event | Trigger | Use Case |
| --- | --- | --- |
| `SubagentStop` | Subagent completes | Aggregate results |
| `PreCompact` | Before compaction | Save context |

## Hook Types

### Command Hook

The primary hook type. Executes a shell command.

```json
{
  "type": "command",
  "command": "your-shell-command"
}
```

### Prompt Hook (Future)

Injects content into the conversation context.
Not yet widely available.

### Agent Hook (Future)

Delegates to a subagent for processing.
Not yet widely available.

## Configuration Format

Hooks live in `settings.json` files:

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "shell-command"
          }
        ]
      }
    ]
  }
}
```

### Structure

```text
hooks
 +-- EventName (e.g., PreToolUse)
      +-- [array of hook configurations]
           +-- matcher: which tools trigger this
           +-- hooks: [array of commands]
                +-- type: "command"
                +-- command: shell command
```

## Matcher Patterns

Matchers determine which tools trigger a hook:

| Pattern | Matches |
| --- | --- |
| `"Write"` | Only Write tool |
| `"Edit\|Write"` | Edit OR Write tools |
| `"Bash"` | Bash tool only |
| `"*"` | All tools (universal) |
| `"Bash(git:*)"` | Bash with git commands |

## Hook Execution

### Input (stdin)

Hooks receive JSON via stdin:

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

| Variable | Description |
| --- | --- |
| `CLAUDE_PROJECT_DIR` | Current project dir |
| `CLAUDE_SESSION_ID` | Current session ID |

### Exit Codes (PreToolUse, PermissionRequest)

| Code | Meaning |
| --- | --- |
| `0` | Allow / approve |
| Non-zero | Block / deny |

## Built-in Templates

The hook manager includes four common templates.

### Formatter

Auto-format code after file edits:

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

### Logger

Log bash commands for audit:

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

### Blocker

Block writes to sensitive files:

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

### Notifier

Desktop notifications when Claude needs input:

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

## Configuration Locations

Settings files are checked in priority order:

| Priority | Path | Scope |
| --- | --- | --- |
| 1 | Enterprise managed policies | Org-wide |
| 2 | `.claude/settings.local.json` | Project local |
| 3 | `.claude/settings.json` | Project shared |
| 4 | `~/.claude/settings.json` | User global |

## Validation Rules

The `validate` operation checks:

- **Event names** -- Must be one of the 10 valid events
- **Structure** -- Each event must have an array of
  configs, each config must have a `hooks` array
- **Commands** -- Each hook must have a `command` field
- **Safety** -- Warns about `rm -rf` and `sudo` usage

## Debugging

### Test a hook command standalone

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"test.ts"}}' \
  | your-hook-command
```

### Check exit codes

```bash
echo '...' | your-hook-command
echo "Exit code: $?"
```

## Security Notes

Hooks run with your environment's full credentials.

**Best practices:**

1. Review before registering
2. Audit third-party hooks
3. Use specific matchers (not `*`) when possible
4. Log sensitive hook activity
5. Test hooks in isolation first
