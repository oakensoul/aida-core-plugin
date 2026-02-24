#!/usr/bin/env python3
"""Hook Manager - Two-Phase API entry point.

Manages Claude Code hook configurations in settings.json
files. Supports list, add, remove, and validate operations.

Usage:
    # Phase 1: Get questions
    python manage.py --get-questions \
      --context='{"operation": "add", "description": "..."}'

    # Phase 2: Execute
    python manage.py --execute \
      --context='{"operation": "list", "scope": "all"}'

Exit codes:
    0 - Success
    1 - Error occurred
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Path setup - must come before local imports
import _paths  # noqa: F401

from shared.utils import safe_json_load  # noqa: E402

from operations import hooks  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent


def get_questions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get questions for a hook operation.

    Args:
        context: Operation context with 'operation'
            and optional parameters

    Returns:
        Questions result dictionary
    """
    return hooks.get_questions(context)


def execute(
    context: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Execute a hook operation.

    Args:
        context: Operation context
        responses: User responses to questions

    Returns:
        Execution result dictionary
    """
    return hooks.execute(context, responses)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Hook Manager - Two-Phase API"
        )
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help=(
            "Phase 1: Analyze context and return "
            "questions (outputs JSON)"
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Phase 2: Execute operation with "
            "context/responses (outputs JSON)"
        ),
    )

    parser.add_argument(
        "--context",
        type=str,
        help="JSON string containing operation context",
    )

    parser.add_argument(
        "--responses",
        type=str,
        help=(
            "JSON string containing user responses "
            "for Phase 2"
        ),
    )

    args = parser.parse_args()

    try:
        if args.get_questions:
            context = (
                safe_json_load(args.context)
                if args.context
                else {}
            )
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0

        elif args.execute:
            context = (
                safe_json_load(args.context)
                if args.context
                else {}
            )
            responses = (
                safe_json_load(args.responses)
                if args.responses
                else {}
            )

            result = execute(context, responses)
            print(json.dumps(result, indent=2))

            return (
                0 if result.get("success", False) else 1
            )

        else:
            parser.print_help()
            return 1

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(
            json.dumps({
                "success": False,
                "message": f"Validation error: {e}",
            })
        )
        return 1

    except Exception as e:
        logger.error(
            f"Unexpected error: {e}", exc_info=True
        )
        print(
            json.dumps({
                "success": False,
                "message": f"Error: {e}",
                "error_type": type(e).__name__,
            })
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
