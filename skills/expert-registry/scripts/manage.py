#!/usr/bin/env python3
"""Expert Registry Script - Two-Phase API

Entry point for managing expert activation and panel configuration.
Supports list, configure, panel-create, and panel-remove operations.

Usage:
    python manage.py --get-questions \
        --context='{"operation": "list"}'
    python manage.py --execute \
        --context='{"operation": "configure"}' \
        --responses='{"active": ["alice", "bob"], "config_path": "global"}'

Exit codes:
    0   - Success
    1   - Error occurred
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

from operations.registry import (  # noqa: E402
    load_experts_config,
    filter_experts_by_role,
    resolve_active_experts,
    save_experts_config,
)

# Discover agents if aida utils are available
try:
    from utils.agents import discover_agents
except ImportError:
    discover_agents = None  # type: ignore[assignment]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default config paths
_GLOBAL_CONFIG = Path.home() / ".claude" / "aida.yml"
_PROJECT_CONFIG = Path.cwd() / ".claude" / "aida-project-context.yml"


def _resolve_paths(context: dict[str, Any]) -> tuple[Path, Path]:
    """Resolve global and project config paths from context overrides."""
    global_path = Path(context["global_path"]) if "global_path" in context else _GLOBAL_CONFIG
    project_path = Path(context["project_path"]) if "project_path" in context else _PROJECT_CONFIG
    return global_path, project_path


def _build_expert_list(
    global_path: Path,
    project_path: Path,
) -> dict[str, Any]:
    """Discover all experts and load config, returning a combined status dict."""
    config = load_experts_config(global_path=global_path, project_path=project_path)
    warnings: list[str] = list(config.get("warnings", []))

    all_experts: list[dict] = []
    if discover_agents is not None:
        try:
            agents = discover_agents()
            all_experts = filter_experts_by_role(agents)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Agent discovery failed: {exc}")
    else:
        warnings.append(
            "Agent discovery unavailable (utils.agents not in path);"
            " expert list may be incomplete."
        )

    active_experts, dangling = resolve_active_experts(all_experts, config)
    warnings.extend(dangling)

    # Annotate each expert with active status
    active_names = {e.get("name") for e in active_experts}
    experts_with_status = [
        {**e, "active": e.get("name") in active_names}
        for e in all_experts
    ]

    return {
        "experts": experts_with_status,
        "active": [e.get("name") for e in active_experts],
        "config": config,
        "warnings": warnings,
    }


def get_questions(context: dict[str, Any]) -> dict[str, Any]:
    """Phase 1: Analyze context and return questions.

    Supported operations:
        list      - Returns expert list with active status; no questions.
        configure - Returns expert list + selection question.

    Args:
        context: Operation context dict.

    Returns:
        Questions result dictionary with keys:
            questions (list), experts (list), warnings (list)
    """
    operation = context.get("operation", "list")
    global_path, project_path = _resolve_paths(context)

    if operation == "list":
        info = _build_expert_list(global_path, project_path)
        return {
            "questions": [],
            "experts": info["experts"],
            "active": info["active"],
            "source": info["config"].get("source"),
            "warnings": info["warnings"],
        }

    if operation == "configure":
        info = _build_expert_list(global_path, project_path)
        expert_names = [e.get("name") for e in info["experts"] if e.get("name")]
        questions = []
        if expert_names:
            questions.append(
                {
                    "id": "active",
                    "type": "multiselect",
                    "message": "Select experts to activate:",
                    "choices": expert_names,
                    "default": info["active"],
                }
            )
        questions.append(
            {
                "id": "config_path",
                "type": "select",
                "message": "Save to which config file?",
                "choices": ["global", "project"],
                "default": "global",
            }
        )
        return {
            "questions": questions,
            "experts": info["experts"],
            "active": info["active"],
            "source": info["config"].get("source"),
            "warnings": info["warnings"],
        }

    return {
        "questions": [],
        "experts": [],
        "active": [],
        "source": None,
        "warnings": [f"Unknown operation '{operation}' for get_questions."],
    }


def execute(context: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
    """Phase 2: Execute an expert-registry operation.

    Supported operations:
        configure    - Save selected active experts to config.
        panel-create - Create or update a named panel.
        panel-remove - Remove a named panel.

    Args:
        context:   Operation context dict.
        responses: User responses from Phase 1 questions.

    Returns:
        Execution result dictionary with key ``success`` (bool).
    """
    operation = context.get("operation", "configure")
    global_path, project_path = _resolve_paths(context)

    # ------------------------------------------------------------------
    # configure: save active expert selection
    # ------------------------------------------------------------------
    if operation == "configure":
        active = responses.get("active", context.get("active", []))
        config_choice = responses.get("config_path", context.get("config_path", "global"))
        save_path = project_path if config_choice == "project" else global_path

        # Preserve existing panels when updating
        existing_config = load_experts_config(
            global_path=global_path, project_path=project_path
        )
        panels = existing_config.get("panels") or None

        result = save_experts_config(path=save_path, active=active, panels=panels)
        return {
            "success": result["success"],
            "path": result["path"],
            "active": active,
            "message": f"Expert configuration saved to {result['path']}",
        }

    # ------------------------------------------------------------------
    # panel-create: create or replace a named panel
    # ------------------------------------------------------------------
    if operation == "panel-create":
        panel_name = context.get("panel_name") or responses.get("panel_name")
        members = context.get("members") or responses.get("members", [])

        if not panel_name:
            return {"success": False, "message": "panel_name is required for panel-create."}

        existing_config = load_experts_config(
            global_path=global_path, project_path=project_path
        )
        config_choice = context.get("config_path", "global")
        save_path = project_path if config_choice == "project" else global_path

        panels: dict = dict(existing_config.get("panels") or {})
        panels[panel_name] = members

        result = save_experts_config(
            path=save_path,
            active=existing_config.get("active", []),
            panels=panels,
        )
        return {
            "success": result["success"],
            "path": result["path"],
            "panel_name": panel_name,
            "members": members,
            "message": f"Panel '{panel_name}' saved to {result['path']}",
        }

    # ------------------------------------------------------------------
    # panel-remove: delete a named panel
    # ------------------------------------------------------------------
    if operation == "panel-remove":
        panel_name = context.get("panel_name") or responses.get("panel_name")

        if not panel_name:
            return {"success": False, "message": "panel_name is required for panel-remove."}

        existing_config = load_experts_config(
            global_path=global_path, project_path=project_path
        )
        config_choice = context.get("config_path", "global")
        save_path = project_path if config_choice == "project" else global_path

        panels = dict(existing_config.get("panels") or {})
        removed = panel_name in panels
        panels.pop(panel_name, None)

        result = save_experts_config(
            path=save_path,
            active=existing_config.get("active", []),
            panels=panels,
        )
        return {
            "success": result["success"],
            "path": result["path"],
            "panel_name": panel_name,
            "removed": removed,
            "message": (
                f"Panel '{panel_name}' removed from {result['path']}"
                if removed
                else f"Panel '{panel_name}' was not found (nothing changed)."
            ),
        }

    return {
        "success": False,
        "message": f"Unknown operation '{operation}'.",
    }


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Expert Registry - Two-Phase API"
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help=(
            "Phase 1: Analyze context and return questions"
            " (outputs JSON)"
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Phase 2: Execute operation with provided"
            " context/responses (outputs JSON)"
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
            "JSON string containing user responses"
            " for Phase 2"
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

            return 0 if result.get("success", False) else 1

        else:
            parser.print_help()
            return 1

    except ValueError as e:
        logger.error("Validation error: %s", e)
        print(
            json.dumps(
                {
                    "success": False,
                    "message": f"Validation error: {e}",
                }
            )
        )
        return 1

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        print(
            json.dumps(
                {
                    "success": False,
                    "message": f"Error: {e}",
                    "error_type": type(e).__name__,
                }
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
