---
type: guide
title: "How to Use Hooks"
description: "Step-by-step guide to using Claude Code hooks for automation"
audience: users
---

# How to Use Hooks

Hooks are shell commands that run automatically at specific points in Claude Code's
lifecycle. Use them for things that MUST happen - like auto-formatting code or
blocking dangerous operations.

## Quick Start

```bash
/aida hook list      # See current hooks
/aida hook add       # Add a new hook interactively
```

## When to Use Hooks

Use hooks when you need:

- **Enforcement** - Auto-format code after every write
- **Blocking** - Prevent writes to protected files
- **Logging** - Track all file modifications
- **Automation** - Trigger builds after changes

Don't use hooks for:

- Workflows (use a [skill](HOWTO_CREATE_SKILL.md))
- Expertise (use an [agent](HOWTO_CREATE_AGENT.md))
- Complex logic (use a [skill](HOWTO_CREATE_SKILL.md))

## Hook Events

### Tool Lifecycle

| Event | When It Runs | Common Use |
| ----- | ------------ | ---------- |
| `PreToolUse` | Before a tool executes | Block or validate |
| `PostToolUse` | After a tool completes | Format or log |

### Session Lifecycle

| Event | When It Runs | Common Use |
| ----- | ------------ | ---------- |
| `SessionStart` | Session begins | Load context |
| `SessionEnd` | Session ends | Cleanup, save state |

### Prompt Lifecycle

| Event | When It Runs | Common Use |
| ----- | ------------ | ---------- |
| `UserPromptSubmit` | User sends message | Inject context |
| `Stop` | Claude finishes | Post-processing |

## Managing Hooks

### List Current Hooks

```bash
/aida hook list
```

Shows all configured hooks at user and project levels.

### Add a Hook

```bash
/aida hook add
```

AIDA will guide you through:

1. Which event to hook into
2. Which tools to match (for tool events)
3. What command to run

### Remove a Hook

```bash
/aida hook remove
```

Select the hook to remove from the list.

### Validate Hooks

```bash
/aida hook validate
```

Checks that all hook scripts exist and are executable.

## Hook Configuration

Hooks are stored in `settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write \"$CLAUDE_FILE_PATH\""
          }
        ]
      }
    ]
  }
}
```

### Configuration Locations

- **User hooks**: `~/.claude/settings.json` - Apply to all projects
- **Project hooks**: `.claude/settings.json` - Apply to current project only

### Matcher Patterns

| Pattern | Matches |
| ------- | ------- |
| `"Write"` | Only Write tool |
| `"Write\|Edit"` | Write OR Edit tools |
| `"Bash"` | Only Bash tool |
| `"*"` | All tools |

## Environment Variables

Hooks receive context via environment variables:

| Variable | Description |
| -------- | ----------- |
| `$CLAUDE_FILE_PATH` | Path to the affected file |
| `$CLAUDE_TOOL_NAME` | Name of the tool being used |
| `$CLAUDE_SESSION_ID` | Current session identifier |

## Examples

### Auto-Format on Save

Format code automatically after every write:

```bash
/aida hook add
# Event: PostToolUse
# Matcher: Write|Edit
# Command: prettier --write "$CLAUDE_FILE_PATH"
```

Or for Python:

```bash
# Command: ruff format "$CLAUDE_FILE_PATH"
```

### Block Protected Files

Prevent modifications to certain files:

```bash
/aida hook add
# Event: PreToolUse
# Matcher: Write|Edit
# Command: [[ "$CLAUDE_FILE_PATH" != *"package-lock.json"* ]] || exit 1
```

### Log All Changes

Keep a log of all file modifications:

```bash
/aida hook add
# Event: PostToolUse
# Matcher: Write|Edit
# Command: echo "$(date): Modified $CLAUDE_FILE_PATH" >> ~/.claude/changes.log
```

### Run Tests After Changes

Trigger tests after code changes:

```bash
/aida hook add
# Event: PostToolUse
# Matcher: Write|Edit
# Command: [[ "$CLAUDE_FILE_PATH" == *.py ]] && pytest --tb=short -q || true
```

### Inject Project Context

Add context to every prompt:

```bash
/aida hook add
# Event: UserPromptSubmit
# Command: echo "Current branch: $(git branch --show-current)"
```

## Hook Scripts

For complex logic, create a script:

```bash
#!/bin/bash
# ~/.claude/hooks/format-on-save.sh

FILE="$CLAUDE_FILE_PATH"

# Only format certain file types
case "$FILE" in
  *.py)
    ruff format "$FILE"
    ruff check --fix "$FILE"
    ;;
  *.js|*.ts|*.jsx|*.tsx)
    prettier --write "$FILE"
    ;;
  *.md)
    markdownlint --fix "$FILE" 2>/dev/null || true
    ;;
esac
```

Make it executable:

```bash
chmod +x ~/.claude/hooks/format-on-save.sh
```

Then reference it in your hook:

```bash
/aida hook add
# Event: PostToolUse
# Matcher: Write|Edit
# Command: ~/.claude/hooks/format-on-save.sh
```

## Best Practices

### Do

- Keep hooks fast (they block Claude)
- Use exit codes correctly (non-zero blocks for PreToolUse)
- Test hooks manually before adding
- Use scripts for complex logic

### Don't

- Run slow operations synchronously
- Modify files in PreToolUse hooks
- Rely on hooks for business logic
- Forget to handle errors gracefully

## Troubleshooting

### Hook not running?

- Verify the event name is correct
- Check the matcher pattern
- Ensure the script is executable
- Look for syntax errors in settings.json

### Hook blocking unexpectedly?

- Check exit codes (non-zero = block for PreToolUse)
- Add `|| true` to commands that might fail
- Test the command manually

### Hook running too slowly?

- Move to background: `command &`
- Use async patterns
- Simplify the logic

## Next Steps

- [Create a Skill](HOWTO_CREATE_SKILL.md) - For workflows and reusable capabilities
- [Extension Framework](EXTENSION_FRAMEWORK.md) - Understand the architecture
