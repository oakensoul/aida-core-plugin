---
type: reference
title: Claude Code Hooks Guide
description: Understanding hooks for deterministic control in Claude Code
---

# Claude Code Hooks

Hooks are **user-defined handlers** that execute at specific points in Claude
Code's lifecycle. They provide lifecycle-bound automation -- ensuring certain
actions always happen rather than relying on the LLM to choose.

Claude Code supports three hook types:

- **Command hooks** (`type: "command"`) run shell commands deterministically
- **Prompt hooks** (`type: "prompt"`) send a prompt to an LLM for evaluation
- **Agent hooks** (`type: "agent"`) spawn agentic verifiers with tool access

Only command hooks are deterministic. Prompt and agent hooks involve LLM
judgment and may produce different results across runs.

## Hooks vs Other Extension Types

| Aspect | Hooks | Skills |
| ------ | ----- | ------ |
| **Trigger** | Automatic (lifecycle events) | Manual (user invocation) |
| **Control** | Command: deterministic; Prompt/Agent: LLM-guided | LLM-guided |
| **Purpose** | Enforcement, automation, verification | Workflows, expertise |
| **Execution** | Shell commands, LLM prompts, agentic verifiers | Claude orchestration |

**Use Hooks for:** Things that MUST happen (formatting, logging, blocking,
quality gates, policy enforcement)
**Use Skills for:** Things that SHOULD happen (workflows, analysis, guided
processes)

## Hook Types

### Command Hooks

Command hooks (`type: "command"`) execute shell commands. They are
deterministic -- the same input always triggers the same command. Your script
receives event JSON on stdin and communicates results through exit codes and
stdout.

```json
{
  "type": "command",
  "command": ".claude/hooks/validate.sh",
  "timeout": 600,
  "async": false
}
```

**When to use:** Formatting, linting, logging, file validation, external system
integration, or any task where predictable behavior is required.

**Limitations:** Cannot inspect codebase context beyond what is provided in
stdin JSON. Cannot make judgment calls.

### Prompt Hooks

Prompt hooks (`type: "prompt"`) send a prompt to a Claude model for single-turn
evaluation. The model returns a yes/no decision as JSON.

```json
{
  "type": "prompt",
  "prompt": "Evaluate if this action is safe: $ARGUMENTS",
  "model": "claude-haiku-4-5",
  "timeout": 30
}
```

The `$ARGUMENTS` placeholder is replaced with the hook's JSON input. If
`$ARGUMENTS` is not present, the input JSON is appended to the prompt.

The LLM responds with:

```json
{
  "ok": true,
  "reason": "Explanation for the decision"
}
```

When `ok` is `false`, `reason` is required and shown to Claude as feedback.

**When to use:** Semantic evaluation of tool inputs, nuanced policy checks,
content analysis that cannot be expressed as simple pattern matching.

**Limitations:** Single-turn only (no tool access). Non-deterministic. Default
timeout is 30 seconds.

### Agent Hooks

Agent hooks (`type: "agent"`) spawn a subagent that can use tools like Read,
Grep, and Glob to verify conditions before returning a decision. They support
up to 50 turns of tool use.

```json
{
  "type": "agent",
  "prompt": "Verify all tests pass and code follows conventions. $ARGUMENTS",
  "model": "claude-haiku-4-5",
  "timeout": 60
}
```

The response schema is the same as prompt hooks: `{ "ok": true }` to allow or
`{ "ok": false, "reason": "..." }` to block.

**When to use:** Complex verification requiring file inspection, test result
analysis, or multi-step checks that need codebase access.

**Limitations:** Non-deterministic. Slower than prompt hooks. Default timeout
is 60 seconds.

### Hook Type Support by Event

Not all events support all three hook types.

Events supporting `command`, `prompt`, and `agent`:

- `PreToolUse`
- `PostToolUse`
- `PostToolUseFailure`
- `PermissionRequest`
- `UserPromptSubmit`
- `Stop`
- `SubagentStop`
- `TaskCompleted`

Events supporting `command` only:

- `SessionStart`
- `SessionEnd`
- `Notification`
- `SubagentStart`
- `TeammateIdle`
- `ConfigChange`
- `PreCompact`
- `WorktreeCreate`
- `WorktreeRemove`

## Hook Lifecycle Events

Claude Code supports 17 hook events organized into lifecycle categories.

### Tool Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `PreToolUse` | Before tool executes | Yes | Block dangerous operations, validate/modify inputs |
| `PostToolUse` | After tool succeeds | No | Format code, log actions, trigger builds |
| `PostToolUseFailure` | After tool fails | No | Log failures, send alerts, provide corrective context |
| `PermissionRequest` | Permission dialog appears | Yes | Auto-approve safe patterns, deny dangerous ones |

### Session Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `SessionStart` | Session begins/resumes | No | Load context, set environment variables |
| `SessionEnd` | Session terminates | No | Cleanup, save state, log session stats |

### Prompt Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `UserPromptSubmit` | User submits prompt | Yes | Validate input, inject context, filter prompts |
| `Notification` | Claude sends notification | No | Custom alerts, integrations |
| `Stop` | Claude finishes responding | Yes | Quality gates, enforce task completion |

### Agent Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `SubagentStart` | Subagent is spawned | No | Inject context into subagent |
| `SubagentStop` | Subagent finishes | Yes | Aggregate results, enforce completion criteria |
| `PreCompact` | Before context compaction | No | Save important context |

### Team Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `TeammateIdle` | Teammate about to go idle | Yes | Quality gates before a teammate stops working |
| `TaskCompleted` | Task marked as completed | Yes | Enforce completion criteria (tests, lint) |

These events fire in [agent teams](/en/agent-teams) contexts.
`TeammateIdle` hooks receive `teammate_name` and `team_name` fields.
`TaskCompleted` hooks receive `task_id`, `task_subject`, and optionally
`task_description`, `teammate_name`, and `team_name`.

Both use exit code 2 to block and stderr for feedback. They do not support
matchers and fire on every occurrence.

### Configuration Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `ConfigChange` | Configuration file changes | Yes | Audit changes, enforce security policies |

Matcher filters on configuration source: `user_settings`,
`project_settings`, `local_settings`, `policy_settings`, `skills`.

Note: `policy_settings` changes cannot be blocked. Hooks still fire for audit
logging, but blocking decisions are ignored for managed policy settings.

### Worktree Lifecycle

| Event | Trigger | Can Block? | Use Case |
| ----- | ------- | ---------- | -------- |
| `WorktreeCreate` | Worktree is created | Yes | Custom VCS integration (SVN, Perforce, Mercurial) |
| `WorktreeRemove` | Worktree is removed | No | Cleanup VCS state, archive changes |

`WorktreeCreate` replaces the default `git worktree` behavior when configured.
The hook must print the absolute path to the created worktree directory on
stdout. Only `type: "command"` hooks are supported.

`WorktreeRemove` fires when a worktree session exits or when a subagent with
`isolation: "worktree"` finishes. Only `type: "command"` hooks are supported.

## Configuration Structure

Hooks are configured in JSON settings files with three levels of nesting:

1. Choose a **hook event** to respond to (e.g., `PreToolUse`)
2. Add a **matcher group** to filter when it fires
3. Define one or more **hook handlers** to run when matched

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
│   └── [array of matcher groups]
│       ├── matcher: regex filtering when hook fires
│       └── hooks: [array of hook handlers]
│           ├── type: "command" | "prompt" | "agent"
│           ├── command: shell command (command type)
│           ├── prompt: LLM prompt text (prompt/agent type)
│           ├── model: model override (prompt/agent type)
│           ├── timeout: seconds before canceling
│           ├── async: run in background (command type only)
│           ├── statusMessage: custom spinner text
│           └── once: run only once per session (skills only)
```

### Common Handler Fields

| Field | Required | Description |
| ----- | -------- | ----------- |
| `type` | Yes | `"command"`, `"prompt"`, or `"agent"` |
| `timeout` | No | Seconds before canceling. Defaults: 600 (command), 30 (prompt), 60 (agent) |
| `statusMessage` | No | Custom spinner message while hook runs |
| `once` | No | If `true`, runs only once per session then removed (skills/agents only) |

### Command-Specific Fields

| Field | Required | Description |
| ----- | -------- | ----------- |
| `command` | Yes | Shell command to execute |
| `async` | No | If `true`, runs in background without blocking |

### Prompt/Agent-Specific Fields

| Field | Required | Description |
| ----- | -------- | ----------- |
| `prompt` | Yes | Prompt text. Use `$ARGUMENTS` for hook input JSON |
| `model` | No | Model to use. Defaults to a fast model |

## Matcher Patterns

Matchers are regex strings that filter when hooks fire. Use `"*"`, `""`, or
omit `matcher` entirely to match all occurrences.

### What Matchers Filter

| Event | Matches On | Example Values |
| ----- | ---------- | -------------- |
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest` | Tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| `SessionStart` | How session started | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | Why session ended | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` |
| `Notification` | Notification type | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` |
| `SubagentStart`, `SubagentStop` | Agent type | `Bash`, `Explore`, `Plan`, or custom agent names |
| `PreCompact` | Compaction trigger | `manual`, `auto` |
| `ConfigChange` | Configuration source | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` |
| `UserPromptSubmit`, `Stop`, `TeammateIdle`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove` | No matcher support | Always fires on every occurrence |

### Tool-Specific Matchers

The matcher is a regex, so `Edit|Write` matches either tool and `Notebook.*`
matches any tool starting with Notebook.

### MCP Tool Matchers

MCP tools follow the naming pattern `mcp__<server>__<tool>`. Use regex
patterns to target specific MCP tools or groups:

| Pattern | Matches |
| ------- | ------- |
| `mcp__memory__.*` | All tools from the memory server |
| `mcp__.*__write.*` | Any write tool from any server |
| `mcp__github__search_repositories` | Specific GitHub tool |

## Hook Execution

### Input (stdin)

All hook events receive common fields via stdin as JSON:

| Field | Description |
| ----- | ----------- |
| `session_id` | Current session identifier |
| `transcript_path` | Path to conversation JSON |
| `cwd` | Current working directory |
| `permission_mode` | Current permission mode: `default`, `plan`, `acceptEdits`, `dontAsk`, `bypassPermissions` |
| `hook_event_name` | Name of the event that fired |

Example for a `PreToolUse` hook:

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  }
}
```

### Environment Variables

| Variable | Description |
| -------- | ----------- |
| `CLAUDE_PROJECT_DIR` | Current project directory |
| `CLAUDE_SESSION_ID` | Current session identifier |
| `CLAUDE_ENV_FILE` | File path for persisting env vars (SessionStart only) |
| `CLAUDE_PLUGIN_ROOT` | Plugin root directory (plugin hooks only) |
| `CLAUDE_CODE_REMOTE` | Set to `"true"` in remote web environments |

### Exit Codes

| Exit Code | Meaning | Behavior |
| --------- | ------- | -------- |
| `0` | Success | Stdout parsed for JSON. Action proceeds |
| `2` | Blocking error | Stderr fed to Claude as error. Action blocked (for events that can block) |
| Other | Non-blocking error | Stderr shown in verbose mode. Execution continues |

### Exit Code 2 Behavior Per Event

| Event | Can Block? | What Happens on Exit 2 |
| ----- | ---------- | ---------------------- |
| `PreToolUse` | Yes | Blocks the tool call |
| `PermissionRequest` | Yes | Denies the permission |
| `UserPromptSubmit` | Yes | Blocks prompt processing, erases prompt |
| `Stop` | Yes | Prevents Claude from stopping |
| `SubagentStop` | Yes | Prevents the subagent from stopping |
| `TeammateIdle` | Yes | Prevents teammate from going idle |
| `TaskCompleted` | Yes | Prevents task from being marked completed |
| `ConfigChange` | Yes | Blocks config change (except `policy_settings`) |
| `WorktreeCreate` | Yes | Worktree creation fails |
| `PostToolUse` | No | Shows stderr to Claude (tool already ran) |
| `PostToolUseFailure` | No | Shows stderr to Claude (tool already failed) |
| `Notification` | No | Shows stderr to user only |
| `SubagentStart` | No | Shows stderr to user only |
| `SessionStart` | No | Shows stderr to user only |
| `SessionEnd` | No | Shows stderr to user only |
| `PreCompact` | No | Shows stderr to user only |
| `WorktreeRemove` | No | Failures logged in debug mode only |

### JSON Output Format

Exit codes let you allow or block, but JSON output gives finer-grained
control. Exit 0 and print a JSON object to stdout. You must choose one
approach per hook: exit codes alone, or exit 0 with JSON.

**Universal JSON fields** (all events):

| Field | Default | Description |
| ----- | ------- | ----------- |
| `continue` | `true` | If `false`, Claude stops processing entirely |
| `stopReason` | none | Message shown to user when `continue` is `false` |
| `suppressOutput` | `false` | If `true`, hides stdout from verbose mode |
| `systemMessage` | none | Warning message shown to user |

**Decision control patterns** vary by event:

| Events | Decision Pattern | Key Fields |
| ------ | ---------------- | ---------- |
| `UserPromptSubmit`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop`, `ConfigChange` | Top-level `decision` | `decision: "block"`, `reason` |
| `TeammateIdle`, `TaskCompleted` | Exit code only | Exit 2 blocks, stderr is feedback |
| `PreToolUse` | `hookSpecificOutput` | `permissionDecision` (allow/deny/ask), `permissionDecisionReason` |
| `PermissionRequest` | `hookSpecificOutput` | `decision.behavior` (allow/deny) |
| `WorktreeCreate` | stdout path | Print absolute path to created worktree |
| `WorktreeRemove`, `Notification`, `SessionEnd`, `PreCompact` | None | No decision control (side effects only) |

### PreToolUse hookSpecificOutput

PreToolUse returns decisions inside a `hookSpecificOutput` object with three
possible outcomes: allow, deny, or ask (escalate to user).

| Field | Description |
| ----- | ----------- |
| `permissionDecision` | `"allow"` bypasses permission, `"deny"` blocks, `"ask"` prompts user |
| `permissionDecisionReason` | For allow/ask: shown to user. For deny: shown to Claude |
| `updatedInput` | Modifies tool input before execution |
| `additionalContext` | String added to Claude's context |

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook"
  }
}
```

### PermissionRequest hookSpecificOutput

| Field | Description |
| ----- | ----------- |
| `decision.behavior` | `"allow"` grants permission, `"deny"` denies it |
| `decision.updatedInput` | For allow: modifies tool input |
| `decision.updatedPermissions` | For allow: applies "always allow" rules |
| `decision.message` | For deny: tells Claude why denied |
| `decision.interrupt` | For deny: if `true`, stops Claude |

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow",
      "updatedInput": {
        "command": "npm run lint"
      }
    }
  }
}
```

## Async Hooks

By default, hooks block Claude's execution until they complete. For
long-running tasks, set `"async": true` to run in the background.

### Configuration

Add `"async": true` to a command hook handler. This field is only available
on `type: "command"` hooks.

```json
{
  "type": "command",
  "command": "/path/to/run-tests.sh",
  "async": true,
  "timeout": 120
}
```

### How Async Hooks Execute

1. Claude Code starts the hook process and continues immediately
2. The hook receives the same JSON input via stdin as a synchronous hook
3. When the process exits, `systemMessage` or `additionalContext` from JSON
   output is delivered on the next conversation turn

### Limitations

- Only `type: "command"` hooks support `async`
- Cannot block tool calls or return decisions (action already proceeded)
- Output delivered on next conversation turn (waits if session is idle)
- Each execution creates a separate background process (no deduplication)

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

### Block Destructive Commands (JSON Output)

```bash
#!/bin/bash
# .claude/hooks/block-rm.sh
COMMAND=$(jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q 'rm -rf'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Destructive command blocked by hook"
    }
  }'
else
  exit 0
fi
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

### Prompt-Based Stop Gate

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if Claude should stop: $ARGUMENTS. Check if all tasks are complete, any errors need addressing, and follow-up work is needed. Respond with JSON: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"explanation\"} to continue.",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Agent-Based Test Verification

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite and check results. $ARGUMENTS",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### Team Quality Gate (TaskCompleted)

```bash
#!/bin/bash
INPUT=$(cat)
TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject')

if ! npm test 2>&1; then
  echo "Tests not passing. Fix before completing: $TASK_SUBJECT" >&2
  exit 2
fi

exit 0
```

### Async Background Tests

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/run-tests-async.sh",
            "async": true,
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```

### Persist Environment Variables (SessionStart)

```bash
#!/bin/bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
  echo 'export DEBUG_LOG=true' >> "$CLAUDE_ENV_FILE"
fi
exit 0
```

## Security Considerations

**Hooks run with your system user's full permissions.**

### Risks

- Hooks execute automatically during the agent loop
- They have access to your shell environment
- Malicious hooks can exfiltrate data
- Command hooks have no sandboxing by default
- Prompt and agent hooks invoke LLM calls that consume API credits

### Best Practices

1. **Review before registering** -- Treat hooks as executable code
2. **Audit third-party hooks** -- Don't blindly copy hook configurations
3. **Limit scope** -- Use specific matchers, not `*` when possible
4. **Log sensitive hooks** -- Track what's running
5. **Test in isolation** -- Verify hook behavior before production use
6. **Validate and sanitize inputs** -- Never trust input data blindly
7. **Always quote shell variables** -- Use `"$VAR"` not `$VAR`
8. **Block path traversal** -- Check for `..` in file paths
9. **Use absolute paths** -- Specify full paths using `"$CLAUDE_PROJECT_DIR"`
10. **Skip sensitive files** -- Avoid `.env`, `.git/`, keys

### Enterprise Considerations

Enterprise managed settings can enforce hooks that users cannot override:

- Audit logging for compliance
- Security scanning requirements
- Blocking dangerous patterns organization-wide
- Use `allowManagedHooksOnly` to block user, project, and plugin hooks

## Hook Configuration Locations

Hooks follow settings.json precedence:

```text
Priority (highest to lowest):
1. Enterprise managed policies
2. .claude/settings.local.json (project local, gitignored)
3. .claude/settings.json (project shared, committable)
4. ~/.claude/settings.json (user global)
```

### Hooks in Skills and Agents

Hooks can be defined directly in skill and subagent YAML frontmatter. These
hooks are scoped to the component's lifecycle and only run while that
component is active.

```yaml
---
name: secure-operations
description: Perform operations with security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

All hook events are supported. For subagents, `Stop` hooks are automatically
converted to `SubagentStop`. Hooks are cleaned up when the component finishes.

## Plugin Hooks

Plugins define hooks in `hooks/hooks.json` at the plugin root, with an
optional top-level `description` field. When a plugin is enabled, its hooks
merge with user and project hooks.

```json
{
  "description": "Automatic code formatting",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Plugin hooks appear in the `/hooks` menu with a `[Plugin]` label and are
read-only (cannot be edited from the menu).

## The /hooks Menu

Type `/hooks` in Claude Code to open the interactive hooks manager. Each hook
is labeled with a bracket prefix indicating its source:

- `[User]`: from `~/.claude/settings.json`
- `[Project]`: from `.claude/settings.json`
- `[Local]`: from `.claude/settings.local.json`
- `[Plugin]`: from a plugin's `hooks/hooks.json` (read-only)

### Disable or Remove Hooks

- Remove a hook by deleting its entry from the settings JSON file or via the
  `/hooks` menu
- Set `"disableAllHooks": true` in settings to temporarily disable all hooks
- `disableAllHooks` respects the managed settings hierarchy (cannot disable
  managed hooks from lower-priority settings)

Direct edits to hooks in settings files don't take effect immediately. Claude
Code captures a snapshot at startup and uses it throughout the session. If
hooks are modified externally, Claude Code warns you and requires review in
the `/hooks` menu before changes apply.

## Debugging Hooks

### Run with debug mode

```bash
claude --debug
```

Shows hook execution details: which hooks matched, exit codes, and output.

### Toggle verbose mode

Use `Ctrl+O` to see hook progress in the transcript.

### Test hook command standalone

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"test.ts"}}' \
  | your-hook-command
```

### Check exit codes

```bash
echo '...' | your-hook-command; echo "Exit code: $?"
```

### Debug output example

```text
[DEBUG] Executing hooks for PostToolUse:Write
[DEBUG] Getting matching hook commands for PostToolUse with query: Write
[DEBUG] Found 1 hook matchers in settings
[DEBUG] Matched 1 hooks for query "Write"
[DEBUG] Found 1 hook commands to execute
[DEBUG] Executing hook command: <cmd> with timeout 600000ms
[DEBUG] Hook command completed with status 0: <stdout>
```

## When to Use Hooks

### Good Use Cases

- **Formatting**: Auto-run prettier, gofmt, black after edits (command)
- **Validation**: Block writes to protected files (command)
- **Logging**: Audit trail for compliance (command)
- **Notifications**: Custom alerts when Claude needs input (command)
- **Integration**: Trigger CI, update external systems (command, async)
- **Quality gates**: Verify tests pass before stopping (prompt or agent)
- **Policy enforcement**: Semantic input validation (prompt)
- **Code review**: Verify conventions before completion (agent)
- **Team quality**: Enforce completion criteria in agent teams (command)

### Poor Use Cases

- **Complex logic**: Use Skills instead
- **User interaction**: Hooks are non-interactive
- **Conditional workflows**: Use Skills instead
- **Domain expertise**: Use Subagents instead

### Choosing a Hook Type

| Need | Hook Type |
| ---- | --------- |
| Deterministic enforcement (must always happen the same way) | `command` |
| Pattern matching on file paths or commands | `command` |
| Semantic evaluation of content or intent | `prompt` |
| Quick yes/no judgment on tool inputs | `prompt` |
| Verification requiring file inspection or test runs | `agent` |
| Long-running background tasks | `command` with `async: true` |

## Hooks vs Permissions

| Aspect | Hooks | Permissions |
| ------ | ----- | ----------- |
| **Mechanism** | Run code/prompts on events | Allow/deny rules |
| **Flexibility** | Can inspect content, run verifiers | Pattern matching only |
| **Action** | Execute anything, block, modify input | Block or allow |
| **Use when** | Need custom logic or verification | Simple access control |

Use permissions for simple allow/deny. Use hooks when you need to inspect
content, run formatters, invoke LLM judgment, or execute custom logic.
