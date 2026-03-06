#!/usr/bin/env python3
"""Backup Management Script - Two-Phase API

Provides a two-phase API for managing file backups with checksum dedup,
JSON metadata sidecars, git context capture, and configurable retention.

Phase 1: get_questions(context)
    - Validates inputs and returns questions if needed
    - For config operation: returns configuration questions

Phase 2: execute(context, responses)
    - Performs the requested operation
    - Returns success/failure with details

Operations:
    save     - Back up a file (with checksum dedup)
    restore  - Restore a file from a backup version
    diff     - Show differences between two versions
    list     - List backup versions for a file or all files
    status   - Show backup analytics and configuration
    config   - Configure backup settings interactively
    clean    - Clean old backups per retention policy

Usage:
    # Phase 1: Get questions for config
    python backup.py --get-questions --context='{"operation": "config"}'

    # Phase 2: Execute save
    python backup.py --execute --context='{"operation": "save", "file": "/path/to/file"}'

    # Direct operations (no questions)
    python backup.py --execute --context='{"operation": "list"}'
    python backup.py --execute --context='{"operation": "status"}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import sys
import json
import argparse
import logging
from pathlib import Path

import _paths  # noqa: F401

from shared.utils import safe_json_load
from operations.backup_ops import (
    load_backup_config,
    run_backup,
    run_restore,
    run_diff,
    run_list,
    run_status,
    builtin_clean,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_questions(context: dict) -> dict:
    """Phase 1: Analyze context and return questions if needed."""
    operation = context.get("operation", "")

    if operation == "save":
        file_path = context.get("file", "")
        if not file_path:
            return {
                "success": False,
                "error": "No file specified for backup",
            }
        if not Path(file_path).is_file():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
            }
        return {"success": True, "questions": []}

    if operation == "restore":
        file_path = context.get("file", "")
        if not file_path:
            return {
                "success": False,
                "error": "No file specified for restore",
            }
        # List available versions for selection
        result = run_list(Path(file_path))
        versions = result.get("versions", [])
        if not versions:
            return {
                "success": False,
                "error": f"No backups found for: {file_path}",
            }
        if len(versions) == 1:
            return {"success": True, "questions": []}
        return {
            "success": True,
            "questions": [
                {
                    "id": "version",
                    "type": "select",
                    "message": "Which version to restore?",
                    "choices": [
                        {
                            "label": (
                                f"{v.get('timestamp', 'unknown')}"
                                f" - {v.get('message', '')}"
                            ),
                            "value": (
                                Path(v["backup_path"]).name.split(
                                    ".aida-backup."
                                )[-1]
                                if v.get("backup_path")
                                else v.get("timestamp", "")
                            ),
                        }
                        for v in versions
                    ],
                    "default": "latest",
                },
            ],
        }

    if operation == "diff":
        return {"success": True, "questions": []}

    if operation in ("list", "status"):
        return {"success": True, "questions": []}

    if operation == "clean":
        return {"success": True, "questions": []}

    if operation == "config":
        config = load_backup_config()
        retention = config.get("retention", {})
        return {
            "success": True,
            "questions": [
                {
                    "id": "backup_enabled",
                    "type": "confirm",
                    "message": "Enable file backups?",
                    "default": config.get("enabled", True),
                },
                {
                    "id": "backup_scope",
                    "type": "select",
                    "message": "Backup scope?",
                    "choices": [
                        {
                            "label": "Always back up",
                            "value": "always",
                        },
                        {
                            "label": "Only outside git repos",
                            "value": "outside-git-only",
                        },
                    ],
                    "default": config.get("scope", "always"),
                    "when": "backup_enabled",
                },
                {
                    "id": "backup_storage",
                    "type": "select",
                    "message": "Storage location?",
                    "choices": [
                        {
                            "label": "Global (~/.claude/.backups/)",
                            "value": "global",
                        },
                        {
                            "label": "Local (next to file)",
                            "value": "local",
                        },
                        {
                            "label": "Custom path",
                            "value": "custom",
                        },
                    ],
                    "default": config.get("storage", "global"),
                    "when": "backup_enabled",
                },
                {
                    "id": "backup_retention_versions",
                    "type": "input",
                    "message": (
                        "Max versions per file (0 = unlimited)?"
                    ),
                    "default": str(retention.get("max_versions", 0)),
                    "when": "backup_enabled",
                },
                {
                    "id": "backup_retention_days",
                    "type": "input",
                    "message": (
                        "Max age in days (0 = unlimited)?"
                    ),
                    "default": str(retention.get("max_age_days", 0)),
                    "when": "backup_enabled",
                },
                {
                    "id": "backup_retention_auto_enforce",
                    "type": "confirm",
                    "message": (
                        "Enforce retention after every save?"
                    ),
                    "default": retention.get("auto_enforce", True),
                    "when": "backup_enabled",
                },
                {
                    "id": "backup_custom_command",
                    "type": "input",
                    "message": (
                        "Custom backup command (empty = use builtin)?"
                    ),
                    "default": config.get("custom_command", ""),
                    "when": "backup_enabled",
                },
            ],
        }

    return {
        "success": False,
        "error": f"Unknown operation: {operation}",
    }


def execute(context: dict, responses: dict) -> dict:
    """Phase 2: Execute the requested backup operation."""
    operation = context.get("operation", "")

    if operation == "save":
        file_path = context.get("file", "")
        message = context.get("message", "")
        if not file_path:
            return {"success": False, "error": "No file specified"}
        return run_backup(Path(file_path), message)

    if operation == "restore":
        file_path = context.get("file", "")
        version = (
            responses.get("version")
            or context.get("version", "latest")
        )
        if not file_path:
            return {"success": False, "error": "No file specified"}
        return run_restore(Path(file_path), version)

    if operation == "diff":
        file_path = context.get("file", "")
        version1 = context.get("version1", "latest")
        version2 = context.get("version2", "current")
        if not file_path:
            return {"success": False, "error": "No file specified"}
        return run_diff(Path(file_path), version1, version2)

    if operation == "list":
        file_path = context.get("file")
        path = Path(file_path) if file_path else None
        return run_list(path)

    if operation == "status":
        return run_status()

    if operation == "clean":
        dry_run = context.get("dry_run", False)
        config = load_backup_config()
        return builtin_clean(config, dry_run=dry_run)

    if operation == "config":
        return _execute_config(responses)

    return {"success": False, "error": f"Unknown operation: {operation}"}


def _execute_config(responses: dict) -> dict:
    """Write config responses to aida.yml backup section."""
    import yaml

    config_path = Path.home() / ".claude" / "aida.yml"

    # Read existing config
    data: dict = {}
    if config_path.is_file():
        try:
            with open(config_path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:
            data = {}

    if not isinstance(data, dict):
        data = {}

    # Build backup config from responses
    enabled = responses.get("backup_enabled", True)
    if isinstance(enabled, str):
        enabled = enabled.lower() in ("true", "yes", "1")

    backup_cfg: dict[str, object] = {"enabled": enabled}
    if enabled:
        scope = responses.get("backup_scope", "always")
        backup_cfg["scope"] = scope

        storage = responses.get("backup_storage", "global")
        backup_cfg["storage"] = storage

        custom_cmd = responses.get("backup_custom_command", "")
        if custom_cmd:
            backup_cfg["custom_command"] = custom_cmd

        max_v = responses.get("backup_retention_versions", "0")
        max_d = responses.get("backup_retention_days", "0")
        auto_e = responses.get("backup_retention_auto_enforce", True)
        if isinstance(auto_e, str):
            auto_e = auto_e.lower() in ("true", "yes", "1")

        try:
            max_v_int = int(max_v)
        except (ValueError, TypeError):
            max_v_int = 0
        try:
            max_d_int = int(max_d)
        except (ValueError, TypeError):
            max_d_int = 0

        backup_cfg["retention"] = {
            "max_versions": max_v_int,
            "max_age_days": max_d_int,
            "auto_enforce": auto_e,
        }

    data["backup"] = backup_cfg

    # Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False)

    return {
        "success": True,
        "message": f"Backup config saved to {config_path}",
        "config": backup_cfg,
    }


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Backup Management - Two-Phase API"
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help="Phase 1: Analyze context and return questions",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Phase 2: Execute operation with context/responses",
    )
    parser.add_argument(
        "--context",
        type=str,
        help="JSON string containing operation context",
    )
    parser.add_argument(
        "--responses",
        type=str,
        help="JSON string containing user responses",
    )

    args = parser.parse_args()

    try:
        if args.get_questions:
            context = safe_json_load(args.context) if args.context else {}
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0

        elif args.execute:
            context = (
                safe_json_load(args.context) if args.context else {}
            )
            responses = (
                safe_json_load(args.responses) if args.responses else {}
            )
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
            "message": f"Validation error: {e}",
        }))
        return 1

    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "message": f"Error: {e}",
            "error_type": type(e).__name__,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
