#!/usr/bin/env python3
"""CLAUDE.md Manager - Two-Phase API Entry Point.

Manages CLAUDE.md configuration files across project, user, and
plugin scopes.

Usage:
    # Phase 1: Get questions
    python manage.py --get-questions \
      --context='{"operation": "create", "scope": "project"}'

    # Phase 2: Execute
    python manage.py --execute \
      --context='{"operation": "create", "scope": "project"}' \
      --responses='{"name": "my-project"}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import argparse
import json
import logging
import sys
from typing import Any

import _paths  # noqa: F401 (sets up sys.path)

from operations import claude_md
from operations.utils import safe_json_load

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
)
logger = logging.getLogger(__name__)


def get_questions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Gather questions for the given operation.

    Args:
        context: Operation context

    Returns:
        Questions result dictionary
    """
    return claude_md.get_questions(context)


def execute(
    context: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Execute the given operation.

    Args:
        context: Operation context
        responses: User responses

    Returns:
        Execution result dictionary
    """
    return claude_md.execute(
        context, responses, _paths.TEMPLATES_DIR
    )


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "CLAUDE.md Manager - Two-Phase API"
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
            "Phase 2: Execute operation with provided "
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
        # Phase 1: Get Questions
        if args.get_questions:
            context = (
                safe_json_load(args.context)
                if args.context
                else {}
            )
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0

        # Phase 2: Execute
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
        print(json.dumps({
            "success": False,
            "message": f"Validation error: {e}",
        }))
        return 1

    except Exception as e:
        logger.error(
            f"Unexpected error: {e}", exc_info=True
        )
        print(json.dumps({
            "success": False,
            "message": f"Error: {e}",
            "error_type": type(e).__name__,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
