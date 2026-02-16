"""Plugin discovery and configuration utilities.

Scans installed plugins for configuration sections and generates
interactive questions for the setup wizard.
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path

from .errors import ConfigurationError
from .json_utils import safe_json_load
from .paths import get_home_dir

logger = logging.getLogger(__name__)

VALID_PREFERENCE_TYPES = {"boolean", "choice", "string"}

PREFERENCE_TYPE_MAP = {
    "boolean": "boolean",
    "choice": "choice",
    "string": "text",
}


def discover_installed_plugins() -> list[dict]:
    """Scan installed plugins and return their metadata.

    Looks for plugin.json files in the standard plugin cache
    directory (~/.claude/plugins/cache/*/*/.claude-plugin/plugin.json).

    Returns:
        List of dicts with keys: name, version, config,
        recommendedPermissions, plugin_dir.
    """
    claude_dir = get_home_dir() / ".claude"
    pattern = str(
        claude_dir
        / "plugins"
        / "cache"
        / "*"
        / "*"
        / ".claude-plugin"
        / "plugin.json"
    )
    plugins = []
    for manifest_path in sorted(glob.glob(pattern)):
        try:
            # Check file size before reading to prevent memory
            # exhaustion (safe_json_load checks after read)
            manifest_file = Path(manifest_path)
            if manifest_file.stat().st_size > 1024 * 1024:
                logger.warning(
                    "Plugin manifest too large: %s",
                    manifest_path,
                )
                continue
            with open(manifest_path, encoding="utf-8") as f:
                raw = f.read()
            data = safe_json_load(raw)
            plugin_dir = str(Path(manifest_path).parent.parent)
            plugins.append(
                {
                    "name": data.get("name", "unknown"),
                    "version": data.get("version", "0.0.0"),
                    "config": data.get("config", {}),
                    "recommendedPermissions": data.get(
                        "recommendedPermissions", {}
                    ),
                    "plugin_dir": plugin_dir,
                }
            )
        except Exception:
            logger.warning(
                "Failed to load plugin manifest: %s",
                manifest_path,
                exc_info=True,
            )
    return plugins


def get_plugins_with_config(plugins: list[dict]) -> list[dict]:
    """Filter plugins that have a non-empty config section.

    Args:
        plugins: List of plugin dicts from discover_installed_plugins.

    Returns:
        Filtered list of plugins with config sections.
    """
    return [p for p in plugins if p.get("config")]


def validate_plugin_config(config: dict, plugin_name: str) -> None:
    """Validate a plugin's config section structure.

    Args:
        config: The config dict from plugin.json.
        plugin_name: Plugin name for error messages.

    Raises:
        ConfigurationError: If config is invalid.
    """
    for field in ("label", "description", "preferences"):
        if field not in config:
            raise ConfigurationError(
                f"Plugin '{plugin_name}' config missing "
                f"required field: {field}"
            )

    if not isinstance(config["label"], str):
        raise ConfigurationError(
            f"Plugin '{plugin_name}' config 'label' "
            "must be a string"
        )
    if not isinstance(config["description"], str):
        raise ConfigurationError(
            f"Plugin '{plugin_name}' config 'description' "
            "must be a string"
        )
    if not isinstance(config["preferences"], list):
        raise ConfigurationError(
            f"Plugin '{plugin_name}' config 'preferences' "
            "must be a list"
        )

    for i, pref in enumerate(config["preferences"]):
        for req in ("key", "type", "label"):
            if req not in pref:
                raise ConfigurationError(
                    f"Plugin '{plugin_name}' preference [{i}] "
                    f"missing required field: {req}"
                )
            if not isinstance(pref[req], str):
                raise ConfigurationError(
                    f"Plugin '{plugin_name}' preference [{i}] "
                    f"'{req}' must be a string"
                )

        if pref["type"] not in VALID_PREFERENCE_TYPES:
            raise ConfigurationError(
                f"Plugin '{plugin_name}' preference [{i}] "
                f"has invalid type '{pref['type']}'. "
                f"Must be one of: "
                f"{', '.join(sorted(VALID_PREFERENCE_TYPES))}"
            )

        if pref["type"] == "choice" and "options" not in pref:
            raise ConfigurationError(
                f"Plugin '{plugin_name}' preference [{i}] "
                "is type 'choice' but missing 'options'"
            )
        if (
            pref["type"] == "choice"
            and not isinstance(pref.get("options"), list)
        ):
            raise ConfigurationError(
                f"Plugin '{plugin_name}' preference [{i}] "
                "'options' must be a list"
            )


def generate_plugin_checklist(plugins: list[dict]) -> dict | None:
    """Generate a multi-select question for plugin selection.

    Args:
        plugins: List of plugins with config sections.

    Returns:
        A question dict for multi-select, or None if empty.
    """
    if not plugins:
        return None

    options = []
    for plugin in plugins:
        config = plugin.get("config", {})
        try:
            validate_plugin_config(config, plugin["name"])
        except ConfigurationError:
            logger.warning(
                "Skipping plugin with invalid config: %s",
                plugin["name"],
                exc_info=True,
            )
            continue
        options.append(
            {
                "label": config["label"],
                "value": plugin["name"],
                "description": config["description"],
            }
        )

    if not options:
        return None

    return {
        "id": "selected_plugins",
        "question": "Which plugins would you like to configure?",
        "type": "multiselect",
        "options": options,
        "required": False,
    }


def generate_plugin_preference_questions(
    selected_plugin_names: list[str],
    plugins: list[dict],
) -> list[dict]:
    """Generate preference questions for selected plugins.

    Args:
        selected_plugin_names: Names of plugins user selected.
        plugins: Full list of plugins with config sections.

    Returns:
        Flat list of question dicts for plugin preferences.
    """
    questions = []
    plugin_map = {p["name"]: p for p in plugins}

    for name in selected_plugin_names:
        plugin = plugin_map.get(name)
        if not plugin:
            continue

        config = plugin.get("config", {})
        preferences = config.get("preferences", [])

        for pref in preferences:
            key = pref.get("key", "")
            # Use __ as delimiter between name and key to avoid
            # collisions with underscores in plugin names or keys
            question_id = f"plugin_{name}__{key.replace('.', '_')}"
            q_type = PREFERENCE_TYPE_MAP.get(pref.get("type", ""), "text")

            question: dict = {
                "id": question_id,
                "question": pref.get("label", key),
                "type": q_type,
                "_plugin_name": name,
            }

            if "default" in pref:
                question["default"] = pref["default"]

            if q_type == "choice" and "options" in pref:
                question["options"] = pref["options"]

            if "description" in pref:
                question["description"] = pref["description"]

            questions.append(question)

    return questions
