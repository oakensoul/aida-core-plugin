#!/usr/bin/env python3
"""Claude Code Management Script - Unified Two-Phase API

This script provides a unified entry point for managing Claude Code artifacts:
- Extensions: agents, skills, plugins
- Hooks: lifecycle automation (settings.json)
- Configuration: CLAUDE.md files

It dispatches to the appropriate operations module based on context.

Usage:
    # Extension operations
    python manage.py --get-questions --context='{"type": "agent", "operation": "create", ...}'
    python manage.py --execute --context='{"type": "agent", "operation": "create", ...}'

    # Hook operations
    python manage.py --get-questions --context='{"target": "hook", "operation": "add", ...}'
    python manage.py --execute --context='{"target": "hook", "operation": "list", ...}'

    # CLAUDE.md operations
    python manage.py --get-questions --context='{"target": "claude", "operation": "create", ...}'
    python manage.py --execute --context='{"target": "claude", "operation": "optimize", ...}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Add operations and shared scripts to path (must be before local imports)
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from operations.utils import safe_json_load  # noqa: E402
from operations import extensions  # noqa: E402
from operations import claude_md  # noqa: E402
from operations import hooks  # noqa: E402


def is_hook_operation(context: dict[str, Any]) -> bool:
    """Determine if this is a hook operation.

    Args:
        context: Operation context

    Returns:
        True if this is a hook operation
    """
    # Explicit target
    if context.get("target") == "hook":
        return True

    # Type is hook
    if context.get("type") == "hook":
        return True

    return False


def is_claude_md_operation(context: dict[str, Any]) -> bool:
    """Determine if this is a CLAUDE.md operation.

    Args:
        context: Operation context

    Returns:
        True if this is a CLAUDE.md operation
    """
    # Explicit target
    if context.get("target") == "claude":
        return True

    # Has scope (CLAUDE.md specific)
    if "scope" in context and context.get("type") not in [
        "agent", "skill", "plugin", "hook"
    ]:
        return True

    # Operation type is CLAUDE.md specific
    if context.get("operation") in ["optimize"]:
        return True

    return False


def get_questions(context: dict[str, Any]) -> dict[str, Any]:
    """Route to appropriate get_questions based on context.

    Args:
        context: Operation context

    Returns:
        Questions result dictionary
    """
    if is_hook_operation(context):
        return hooks.get_questions(context)
    elif is_claude_md_operation(context):
        return claude_md.get_questions(context)
    else:
        return extensions.get_questions(context)


def execute(context: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
    """Route to appropriate execute based on context.

    Args:
        context: Operation context
        responses: User responses

    Returns:
        Execution result dictionary
    """
    if is_hook_operation(context):
        return hooks.execute(context, responses, TEMPLATES_DIR)
    elif is_claude_md_operation(context):
        return claude_md.execute(context, responses, TEMPLATES_DIR)
    else:
        return extensions.execute(context, responses, TEMPLATES_DIR)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Code Management - Unified Two-Phase API"
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help="Phase 1: Analyze context and return questions (outputs JSON)"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Phase 2: Execute operation with provided context/responses (outputs JSON)"
    )

    parser.add_argument(
        "--context",
        type=str,
        help="JSON string containing operation context"
    )

    parser.add_argument(
        "--responses",
        type=str,
        help="JSON string containing user responses for Phase 2"
    )

    args = parser.parse_args()

    try:
        # Phase 1: Get Questions
        if args.get_questions:
            context = safe_json_load(args.context) if args.context else {}
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0

        # Phase 2: Execute
        elif args.execute:
            context = safe_json_load(args.context) if args.context else {}
            responses = safe_json_load(args.responses) if args.responses else {}

            result = execute(context, responses)
            print(json.dumps(result, indent=2))

            return 0 if result.get("success", False) else 1

        else:
            parser.print_help()
            return 1

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(json.dumps({
            "success": False,
            "message": f"Validation error: {e}"
        }))
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "message": f"Error: {e}",
            "error_type": type(e).__name__
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
