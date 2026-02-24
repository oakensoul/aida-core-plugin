"""Hook operations for Claude Code hook management.

Handles lifecycle hooks configured in settings.json files:
- list: Show all configured hooks
- add: Add a new hook configuration
- remove: Remove a hook configuration
- validate: Validate hook configurations
"""

import json
from pathlib import Path
from typing import Any, Optional

# Valid hook events
VALID_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "Notification",
    "Stop",
    "SubagentStop",
    "PreCompact",
]

# Common hook templates
HOOK_TEMPLATES = {
    "formatter": {
        "event": "PostToolUse",
        "matcher": "Write|Edit",
        "description": "Auto-format code after file edits",
        "command": (
            "jq -r '.tool_input.file_path'"
            ' | xargs -I {} prettier --write "{}"'
        ),
    },
    "logger": {
        "event": "PostToolUse",
        "matcher": "Bash",
        "description": "Log bash commands for audit",
        "command": (
            'jq -r \'"\\(.tool_input.command) - '
            '\\(.tool_input.description // \\"No description\\")"'
            "' >> ~/.claude/bash-log.txt"
        ),
    },
    "blocker": {
        "event": "PreToolUse",
        "matcher": "Write|Edit",
        "description": "Block writes to sensitive files",
        "command": (
            "jq -e '.tool_input.file_path | "
            'test("\\\\.env|\\\\.git/")\' && exit 1 || exit 0'
        ),
    },
    "notifier": {
        "event": "Notification",
        "matcher": "*",
        "description": (
            "Desktop notifications when Claude needs input"
        ),
        "command": (
            "jq -r '.message' | xargs -I {} osascript -e "
            "'display notification \"{}\" "
            "with title \"Claude Code\"'"
        ),
    },
}

# Settings file locations
SETTINGS_PATHS = {
    "user": Path.home() / ".claude" / "settings.json",
    "project": Path.cwd() / ".claude" / "settings.json",
    "local": (
        Path.cwd() / ".claude" / "settings.local.json"
    ),
}


def _load_settings(path: Path) -> dict[str, Any]:
    """Load settings from a JSON file."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_settings(
    path: Path, settings: dict[str, Any]
) -> bool:
    """Save settings to a JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(settings, indent=2) + "\n"
        )
        return True
    except OSError:
        return False


def _get_hooks_from_settings(
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract hooks from a settings dictionary."""
    hooks = settings.get("hooks", {})
    result = []

    for event, configs in hooks.items():
        if not isinstance(configs, list):
            continue
        for config in configs:
            matcher = config.get("matcher", "*")
            for hook in config.get("hooks", []):
                result.append({
                    "event": event,
                    "matcher": matcher,
                    "type": hook.get("type", "command"),
                    "command": hook.get("command", ""),
                })

    return result


def get_questions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get questions for hook operations.

    Args:
        context: Operation context with 'operation'
            and optional 'description'

    Returns:
        Questions result dictionary
    """
    operation = context.get("operation", "list")

    if operation == "list":
        return {"questions": [], "inferred": {}}

    elif operation == "add":
        description = context.get("description", "")
        questions = []

        # Try to infer from description
        inferred: dict[str, Any] = {}
        desc_lower = description.lower()

        # Check if description matches a template
        for name, template in HOOK_TEMPLATES.items():
            template_desc = template["description"]
            if (
                name in desc_lower
                or template_desc.lower() in desc_lower
            ):
                inferred = {
                    "template": name,
                    "event": template["event"],
                    "matcher": template["matcher"],
                    "command": template["command"],
                }
                break

        # Event type question
        if "event" not in inferred:
            questions.append({
                "id": "event",
                "question": (
                    "What lifecycle event should "
                    "trigger this hook?"
                ),
                "options": [
                    {
                        "label": "PostToolUse",
                        "description": (
                            "After tool completes "
                            "(formatting, logging)"
                        ),
                    },
                    {
                        "label": "PreToolUse",
                        "description": (
                            "Before tool runs "
                            "(blocking, validation)"
                        ),
                    },
                    {
                        "label": "Notification",
                        "description": (
                            "When Claude sends "
                            "notification"
                        ),
                    },
                    {
                        "label": "SessionStart",
                        "description": (
                            "When session begins"
                        ),
                    },
                ],
            })

        # Scope question
        questions.append({
            "id": "scope",
            "question": (
                "Where should this hook be configured?"
            ),
            "options": [
                {
                    "label": "project",
                    "description": (
                        "Shared with team "
                        "(.claude/settings.json)"
                    ),
                },
                {
                    "label": "user",
                    "description": (
                        "Personal global "
                        "(~/.claude/settings.json)"
                    ),
                },
                {
                    "label": "local",
                    "description": (
                        "Personal project override "
                        "(.claude/settings.local.json)"
                    ),
                },
            ],
        })

        # Template question if not inferred
        if "template" not in inferred:
            questions.append({
                "id": "template",
                "question": (
                    "Would you like to use a "
                    "common template?"
                ),
                "options": [
                    {
                        "label": "formatter",
                        "description": (
                            "Auto-format code "
                            "after writes"
                        ),
                    },
                    {
                        "label": "logger",
                        "description": (
                            "Log bash commands "
                            "for audit"
                        ),
                    },
                    {
                        "label": "blocker",
                        "description": (
                            "Block writes to "
                            "sensitive files"
                        ),
                    },
                    {
                        "label": "custom",
                        "description": (
                            "Create custom hook"
                        ),
                    },
                ],
            })

        return {
            "questions": questions,
            "inferred": inferred,
        }

    elif operation == "remove":
        questions = [
            {
                "id": "scope",
                "question": (
                    "Which settings file "
                    "contains the hook?"
                ),
                "options": [
                    {
                        "label": "project",
                        "description": (
                            ".claude/settings.json"
                        ),
                    },
                    {
                        "label": "user",
                        "description": (
                            "~/.claude/settings.json"
                        ),
                    },
                    {
                        "label": "local",
                        "description": (
                            ".claude/"
                            "settings.local.json"
                        ),
                    },
                ],
            }
        ]
        return {"questions": questions, "inferred": {}}

    elif operation == "validate":
        return {"questions": [], "inferred": {}}

    return {"questions": [], "inferred": {}}


def execute(
    context: dict[str, Any],
    responses: dict[str, Any],
    templates_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute a hook operation.

    Args:
        context: Operation context
        responses: User responses to questions
        templates_dir: Path to templates directory
            (unused for hooks)

    Returns:
        Execution result dictionary
    """
    operation = context.get("operation", "list")
    scope = (
        context.get("scope")
        or responses.get("scope", "all")
    )

    if operation == "list":
        return _execute_list(scope)
    elif operation == "add":
        return _execute_add(context, responses)
    elif operation == "remove":
        return _execute_remove(context, responses)
    elif operation == "validate":
        return _execute_validate(scope)
    else:
        return {
            "success": False,
            "message": f"Unknown operation: {operation}",
        }


def _execute_list(scope: str) -> dict[str, Any]:
    """List all configured hooks."""
    results = []

    scopes_to_check = (
        list(SETTINGS_PATHS.keys())
        if scope == "all"
        else [scope]
    )

    for scope_name in scopes_to_check:
        path = SETTINGS_PATHS.get(scope_name)
        if not path:
            continue

        settings = _load_settings(path)
        hooks = _get_hooks_from_settings(settings)

        for hook in hooks:
            hook["source"] = scope_name
            hook["path"] = str(path)
            results.append(hook)

    return {
        "success": True,
        "hooks": results,
        "count": len(results),
        "message": f"Found {len(results)} hook(s)",
    }


def _execute_add(
    context: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Add a new hook configuration."""
    scope = (
        context.get("scope")
        or responses.get("scope", "project")
    )
    event = (
        context.get("event") or responses.get("event")
    )
    matcher = context.get("matcher", "*")
    command = context.get("command")
    template = (
        context.get("template")
        or responses.get("template")
    )

    # If using a template, get the command from it
    if template and template in HOOK_TEMPLATES:
        tmpl = HOOK_TEMPLATES[template]
        event = event or tmpl["event"]
        matcher = tmpl["matcher"]
        command = command or tmpl["command"]

    # Validate required fields
    if not event:
        return {
            "success": False,
            "message": "Event type is required",
        }
    if not command:
        return {
            "success": False,
            "message": "Command is required",
        }
    if event not in VALID_EVENTS:
        valid = ", ".join(VALID_EVENTS)
        return {
            "success": False,
            "message": (
                f"Invalid event: {event}. Valid: {valid}"
            ),
        }

    # Load current settings
    path = SETTINGS_PATHS.get(scope)
    if not path:
        return {
            "success": False,
            "message": f"Invalid scope: {scope}",
        }

    settings = _load_settings(path)

    # Initialize hooks structure if needed
    if "hooks" not in settings:
        settings["hooks"] = {}
    if event not in settings["hooks"]:
        settings["hooks"][event] = []

    # Create hook entry
    hook_entry = {
        "matcher": matcher,
        "hooks": [
            {
                "type": "command",
                "command": command,
            }
        ],
    }

    # Check for duplicates
    for existing in settings["hooks"][event]:
        if existing.get("matcher") == matcher:
            for h in existing.get("hooks", []):
                if h.get("command") == command:
                    return {
                        "success": False,
                        "message": (
                            "Hook already exists with "
                            "same matcher and command"
                        ),
                    }

    # Add the hook
    settings["hooks"][event].append(hook_entry)

    # Save settings
    if not _save_settings(path, settings):
        return {
            "success": False,
            "message": (
                f"Failed to write settings to {path}"
            ),
        }

    return {
        "success": True,
        "message": (
            f"Added {event} hook to {scope} settings"
        ),
        "hook": {
            "event": event,
            "matcher": matcher,
            "command": command,
            "source": scope,
            "path": str(path),
        },
    }


def _execute_remove(
    context: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Remove a hook configuration."""
    scope = (
        context.get("scope")
        or responses.get("scope", "project")
    )
    event = context.get("event")
    matcher = context.get("matcher", "*")

    if not event:
        return {
            "success": False,
            "message": (
                "Event type is required for removal"
            ),
        }

    path = SETTINGS_PATHS.get(scope)
    if not path:
        return {
            "success": False,
            "message": f"Invalid scope: {scope}",
        }

    settings = _load_settings(path)

    if (
        "hooks" not in settings
        or event not in settings["hooks"]
    ):
        return {
            "success": False,
            "message": (
                f"No {event} hooks found "
                f"in {scope} settings"
            ),
        }

    # Find and remove matching hooks
    original_count = len(settings["hooks"][event])
    settings["hooks"][event] = [
        h
        for h in settings["hooks"][event]
        if h.get("matcher") != matcher
    ]
    removed = original_count - len(
        settings["hooks"][event]
    )

    if removed == 0:
        return {
            "success": False,
            "message": (
                f"No hook found with matcher '{matcher}'"
            ),
        }

    # Clean up empty event arrays
    if not settings["hooks"][event]:
        del settings["hooks"][event]

    # Clean up empty hooks object
    if not settings["hooks"]:
        del settings["hooks"]

    # Save settings
    if not _save_settings(path, settings):
        return {
            "success": False,
            "message": (
                f"Failed to write settings to {path}"
            ),
        }

    return {
        "success": True,
        "message": (
            f"Removed {removed} hook(s) "
            f"from {scope} settings"
        ),
        "removed": {
            "event": event,
            "matcher": matcher,
            "count": removed,
        },
    }


def _execute_validate(scope: str) -> dict[str, Any]:
    """Validate hook configurations."""
    issues: list[dict[str, Any]] = []

    scopes_to_check = (
        list(SETTINGS_PATHS.keys())
        if scope == "all"
        else [scope]
    )

    for scope_name in scopes_to_check:
        path = SETTINGS_PATHS.get(scope_name)
        if not path or not path.exists():
            continue

        settings = _load_settings(path)
        hooks = settings.get("hooks", {})

        for event, configs in hooks.items():
            # Check event name
            if event not in VALID_EVENTS:
                valid = ", ".join(VALID_EVENTS)
                issues.append({
                    "severity": "error",
                    "source": scope_name,
                    "message": (
                        f"Invalid event '{event}'"
                    ),
                    "suggestion": (
                        f"Use one of: {valid}"
                    ),
                })
                continue

            if not isinstance(configs, list):
                issues.append({
                    "severity": "error",
                    "source": scope_name,
                    "message": (
                        f"Event '{event}' config "
                        "should be an array"
                    ),
                    "suggestion": (
                        "Wrap hook config in an array"
                    ),
                })
                continue

            for i, config in enumerate(configs):
                if "hooks" not in config:
                    issues.append({
                        "severity": "error",
                        "source": scope_name,
                        "message": (
                            f"{event}[{i}] missing "
                            "'hooks' array"
                        ),
                        "suggestion": (
                            "Add hooks array with "
                            "command objects"
                        ),
                    })
                    continue

                for j, hook in enumerate(
                    config.get("hooks", [])
                ):
                    if "command" not in hook:
                        issues.append({
                            "severity": "error",
                            "source": scope_name,
                            "message": (
                                f"{event}[{i}]"
                                f".hooks[{j}] "
                                "missing 'command'"
                            ),
                            "suggestion": (
                                "Add command field "
                                "with shell command"
                            ),
                        })

                    # Warn about dangerous commands
                    cmd = hook.get("command", "")
                    if (
                        "rm -rf" in cmd
                        or "sudo" in cmd
                    ):
                        issues.append({
                            "severity": "warning",
                            "source": scope_name,
                            "message": (
                                f"{event}[{i}]"
                                f".hooks[{j}] has "
                                "potentially "
                                "dangerous command"
                            ),
                            "suggestion": (
                                "Review command "
                                "for safety"
                            ),
                        })

    error_count = len(
        [i for i in issues if i["severity"] == "error"]
    )
    warning_count = len(
        [
            i
            for i in issues
            if i["severity"] == "warning"
        ]
    )

    return {
        "success": error_count == 0,
        "issues": issues,
        "error_count": error_count,
        "warning_count": warning_count,
        "message": (
            "Validation passed"
            if not issues
            else f"Found {len(issues)} issue(s)"
        ),
    }
