#!/usr/bin/env python3
"""Skill Manager Script - Two-Phase API

Entry point for managing Claude Code skill definitions.
Supports create, validate, version, and list operations.

The component type is always "skill" - this is a focused manager
that does not handle agents, plugins, or hooks.

Usage:
    python manage.py --get-questions \
      --context='{"operation": "create", "description": "..."}'

    python manage.py --execute \
      --context='{"operation": "create", "name": "my-skill", ...}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Add operations and shared scripts to path
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from operations import extensions  # noqa: E402
from operations.utils import safe_json_load  # noqa: E402


def get_questions(
    context: dict[str, object],
) -> dict[str, object]:
    """Route to skill get_questions.

    Ensures component_type is always "skill".

    Args:
        context: Operation context

    Returns:
        Questions result dictionary
    """
    # Force component type to skill
    context["type"] = "skill"
    return extensions.get_questions(context)


def execute(
    context: dict[str, object],
    responses: dict[str, object],
) -> dict[str, object]:
    """Route to skill execute.

    Ensures component_type is always "skill".

    Args:
        context: Operation context
        responses: User responses

    Returns:
        Execution result dictionary
    """
    # Force component type to skill
    context["type"] = "skill"
    return extensions.execute(context, responses, TEMPLATES_DIR)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Skill Manager - Two-Phase API"
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help=(
            "Phase 1: Analyze context and return questions "
            "(outputs JSON)"
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

            return 0 if result.get("success", False) else 1

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
