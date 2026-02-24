"""Unit tests for plugin-manager extension CRUD operations.

This test suite covers the plugin-manager extensions.py module,
which handles create, validate, version, and list operations for
Claude Code plugins. Plugins use JSON metadata (plugin.json)
rather than YAML frontmatter like agents and skills.

Tested functions:
    - find_components: plugin discovery via .claude-plugin/plugin.json
    - component_exists: existence check by name
    - get_questions: Phase 1 question generation for all operations
    - execute_create: plugin directory/file creation
    - execute_validate: plugin.json validation
    - execute_version: JSON-based version bumping
    - execute_list: plugin listing
    - execute: main dispatcher routing
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch

# Add scripts directories to path for imports
_project_root = Path(__file__).parent.parent.parent
_plugin_scripts = (
    _project_root / "skills" / "plugin-manager" / "scripts"
)
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_plugin_scripts))

# Clear cached operations modules to avoid cross-manager conflicts
# when pytest runs multiple test files in a single session.
# Only operations.* is cleared; shared.* is left intact to avoid
# breaking subsequent test files that depend on shared imports.
for _mod_name in list(sys.modules):
    if (
        _mod_name == "operations"
        or _mod_name.startswith("operations.")
    ):
        del sys.modules[_mod_name]
sys.modules.pop("manage", None)
sys.modules.pop("_paths", None)

# Import the module objects so we can use patch.object
import operations.extensions as _ext_mod  # noqa: E402
import shared.extension_utils as _shared_ext_mod  # noqa: E402

from operations.extensions import (  # noqa: E402
    PLUGIN_CONFIG,
    component_exists,
    execute,
    execute_create,
    execute_list,
    execute_validate,
    execute_version,
    find_components,
    get_questions,
)

# Templates directory for execute_create tests
_EXTENSION_TEMPLATES = (
    _project_root
    / "skills"
    / "plugin-manager"
    / "templates"
    / "extension"
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _patch_location(base):
    """Patch get_location_path in both extensions and shared modules.

    This ensures that regardless of test ordering in the full
    suite, the correct function reference is patched using
    patch.object on the actual module objects.
    """
    return [
        patch.object(
            _ext_mod, "get_location_path", return_value=base
        ),
        patch.object(
            _shared_ext_mod,
            "get_location_path",
            return_value=base,
        ),
    ]


class _PatchedTestCase(unittest.TestCase):
    """Mixin providing location-patched context manager."""

    def _with_patched_location(self, base):
        """Return a context manager that patches both modules."""
        patches = _patch_location(base)
        # Start both patches
        for p in patches:
            p.start()
        # Return a cleanup function
        return patches

    def _stop_patches(self, patches):
        """Stop all active patches."""
        for p in patches:
            p.stop()


def _create_plugin(
    base: Path,
    name: str,
    *,
    version: str = "0.1.0",
    description: str = "A test plugin",
    extra_fields: Optional[dict] = None,
) -> Path:
    """Create a minimal plugin directory structure for tests.

    Args:
        base: Parent directory (the 'location' path).
        name: Plugin name (becomes a subdirectory).
        version: Semver string written to plugin.json.
        description: Description written to plugin.json.
        extra_fields: Additional JSON fields to merge.

    Returns:
        Path to the plugin root directory (base/name).
    """
    plugin_root = base / name
    plugin_meta = plugin_root / ".claude-plugin"
    plugin_meta.mkdir(parents=True, exist_ok=True)

    data = {
        "name": name,
        "version": version,
        "description": description,
    }
    if extra_fields:
        data.update(extra_fields)

    (plugin_meta / "plugin.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
    return plugin_root


# ------------------------------------------------------------------
# find_components
# ------------------------------------------------------------------


class TestFindComponents(_PatchedTestCase):
    """Test plugin discovery via find_components."""

    def test_finds_plugins_at_location(self):
        """Discover plugins with valid .claude-plugin/plugin.json."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "alpha-plugin", version="1.0.0"
            )
            _create_plugin(
                base, "beta-plugin", version="2.3.4"
            )

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(len(result), 2)
        names = {c["name"] for c in result}
        self.assertEqual(
            names, {"alpha-plugin", "beta-plugin"}
        )

        for comp in result:
            self.assertIn("name", comp)
            self.assertIn("version", comp)
            self.assertIn("description", comp)
            self.assertIn("location", comp)
            self.assertIn("path", comp)

    def test_returns_empty_when_no_plugins(self):
        """Return empty list when directory has no plugins."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "not-a-plugin").mkdir()

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(result, [])

    def test_handles_missing_directory_gracefully(self):
        """Return empty list when search dir does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "nonexistent"

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(result, [])

    def test_skips_invalid_json(self):
        """Skip plugins with invalid plugin.json JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin_root = base / "broken-plugin"
            meta = plugin_root / ".claude-plugin"
            meta.mkdir(parents=True)
            (meta / "plugin.json").write_text(
                "{invalid json", encoding="utf-8"
            )

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(result, [])

    def test_reads_name_version_description(self):
        """Populate name, version, description from JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base,
                "detail-plugin",
                version="3.2.1",
                description="Detailed description",
            )

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "detail-plugin")
        self.assertEqual(result[0]["version"], "3.2.1")
        self.assertEqual(
            result[0]["description"], "Detailed description"
        )

    def test_defaults_when_fields_missing(self):
        """Use fallback values when JSON fields are absent."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin_root = base / "sparse-plugin"
            meta = plugin_root / ".claude-plugin"
            meta.mkdir(parents=True)
            (meta / "plugin.json").write_text(
                "{}", encoding="utf-8"
            )

            patches = self._with_patched_location(base)
            try:
                result = find_components(location="project")
            finally:
                self._stop_patches(patches)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "sparse-plugin")
        self.assertEqual(result[0]["version"], "0.0.0")
        self.assertEqual(result[0]["description"], "")


# ------------------------------------------------------------------
# component_exists
# ------------------------------------------------------------------


class TestComponentExists(_PatchedTestCase):
    """Test plugin existence check."""

    def test_returns_true_for_existing_plugin(self):
        """Return True when plugin with given name is found."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(base, "existing-plugin")

            patches = self._with_patched_location(base)
            try:
                result = component_exists(
                    "existing-plugin", "project"
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result)

    def test_returns_false_for_nonexisting_plugin(self):
        """Return False when plugin name is not found."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = component_exists(
                    "no-such-plugin", "project"
                )
            finally:
                self._stop_patches(patches)

        self.assertFalse(result)


# ------------------------------------------------------------------
# get_questions
# ------------------------------------------------------------------


class TestGetQuestions(_PatchedTestCase):
    """Test Phase 1 question generation."""

    @patch.object(
        _shared_ext_mod,
        "detect_project_context",
        return_value={},
    )
    def test_create_without_description_asks_for_it(
        self, _mock_ctx
    ):
        """Create without description asks for it."""
        context = {"operation": "create"}
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("description", question_ids)

    @patch.object(
        _shared_ext_mod,
        "detect_project_context",
        return_value={},
    )
    @patch.object(
        _shared_ext_mod,
        "get_location_path",
        return_value=Path("/tmp/fake"),
    )
    def test_create_with_description_infers_metadata(
        self, _mock_loc, _mock_ctx
    ):
        """Create with description populates inferred values."""
        context = {
            "operation": "create",
            "description": "A plugin for managing webhooks",
        }
        result = get_questions(context)

        self.assertIn("inferred", result)
        self.assertIn("name", result["inferred"])
        self.assertEqual(result["inferred"]["version"], "0.1.0")

    def test_validate_without_name_asks_for_it(self):
        """Validate without name returns name question."""
        context = {"operation": "validate"}
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("name", question_ids)

    def test_validate_with_all_flag_no_name_question(self):
        """Validate with all=True does not ask for name."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                context = {
                    "operation": "validate",
                    "all": True,
                }
                result = get_questions(context)
            finally:
                self._stop_patches(patches)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertNotIn("name", question_ids)

    def test_version_without_name_asks_for_it(self):
        """Version without name returns name question."""
        context = {"operation": "version"}
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("name", question_ids)

    def test_list_returns_no_questions(self):
        """List operation requires no questions."""
        context = {"operation": "list"}
        result = get_questions(context)

        self.assertEqual(len(result["questions"]), 0)
        self.assertIn("inferred", result)
        self.assertIn("location", result["inferred"])


# ------------------------------------------------------------------
# execute_create
# ------------------------------------------------------------------


class TestExecuteCreate(_PatchedTestCase):
    """Test plugin creation."""

    def test_creates_plugin_directory_structure(self):
        """Create .claude-plugin, plugin.json, agents/, skills/."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_create(
                    name="test-plugin",
                    description=(
                        "A plugin for automated testing"
                    ),
                    version="0.1.0",
                    tags=["test"],
                    location="project",
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

            self.assertTrue(
                result["success"], result.get("message")
            )

            output_dir = base / "test-plugin"
            self.assertTrue(output_dir.exists())
            self.assertTrue(
                (output_dir / ".claude-plugin").is_dir()
            )
            self.assertTrue(
                (
                    output_dir
                    / ".claude-plugin"
                    / "plugin.json"
                ).exists()
            )
            self.assertTrue(
                (output_dir / "agents").is_dir()
            )
            self.assertTrue(
                (output_dir / "skills").is_dir()
            )

    def test_creates_gitignore(self):
        """Create .gitignore from template."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_create(
                    name="gitignore-plugin",
                    description=(
                        "A plugin to test gitignore creation"
                    ),
                    version="0.1.0",
                    tags=[],
                    location="project",
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

            self.assertTrue(
                result["success"], result.get("message")
            )
            self.assertTrue(
                (
                    base / "gitignore-plugin" / ".gitignore"
                ).exists()
            )

    def test_plugin_json_contains_correct_metadata(self):
        """Rendered plugin.json has correct metadata fields."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_create(
                    name="meta-plugin",
                    description=(
                        "Metadata test plugin for validation"
                    ),
                    version="1.2.3",
                    tags=["test"],
                    location="project",
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

            self.assertTrue(
                result["success"], result.get("message")
            )

            plugin_json_path = (
                base
                / "meta-plugin"
                / ".claude-plugin"
                / "plugin.json"
            )
            data = json.loads(
                plugin_json_path.read_text(encoding="utf-8")
            )
            self.assertEqual(data["name"], "meta-plugin")
            self.assertEqual(data["version"], "1.2.3")
            self.assertEqual(
                data["description"],
                "Metadata test plugin for validation",
            )

    def test_result_contains_path_and_files(self):
        """Result dict includes path and files_created keys."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_create(
                    name="keys-plugin",
                    description=(
                        "Plugin to check result keys shape"
                    ),
                    version="0.1.0",
                    tags=[],
                    location="project",
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertIn("path", result)
        self.assertIn("files_created", result)
        self.assertIsInstance(result["files_created"], list)
        self.assertGreater(len(result["files_created"]), 0)


# ------------------------------------------------------------------
# execute_validate
# ------------------------------------------------------------------


class TestExecuteValidate(_PatchedTestCase):
    """Test plugin validation."""

    def test_validates_valid_plugin(self):
        """Valid plugin.json passes validation with no errors."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base,
                "valid-plugin",
                version="1.0.0",
                description="A fully valid plugin for tests",
            )

            patches = self._with_patched_location(base)
            try:
                result = execute_validate(
                    name="valid-plugin", location="project"
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "validate")
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["results"][0]["valid"])
        self.assertEqual(result["results"][0]["errors"], [])

    def test_catches_missing_required_fields(self):
        """Plugin with bad name or missing description fails."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin_root = base / "x"
            meta = plugin_root / ".claude-plugin"
            meta.mkdir(parents=True)
            (meta / "plugin.json").write_text(
                json.dumps(
                    {
                        "name": "x",
                        "version": "1.0.0",
                        "description": "",
                    }
                ),
                encoding="utf-8",
            )

            patches = self._with_patched_location(base)
            try:
                result = execute_validate(
                    name="x", location="project"
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 1)
        self.assertFalse(result["results"][0]["valid"])
        self.assertGreater(
            len(result["results"][0]["errors"]), 0
        )

    def test_returns_standardized_response_shape(self):
        """Response has success, operation, results, summary."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base,
                "shape-plugin",
                description="Plugin to test response shape",
            )

            patches = self._with_patched_location(base)
            try:
                result = execute_validate(
                    name="shape-plugin", location="project"
                )
            finally:
                self._stop_patches(patches)

        self.assertIn("success", result)
        self.assertIn("operation", result)
        self.assertIn("results", result)
        self.assertIn("summary", result)
        self.assertIn("total", result["summary"])
        self.assertIn("valid", result["summary"])
        self.assertIn("invalid", result["summary"])

    def test_validate_all_finds_multiple_plugins(self):
        """Validate all plugins in a location."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base,
                "first-plugin",
                description=(
                    "First plugin for batch validation"
                ),
            )
            _create_plugin(
                base,
                "second-plugin",
                description=(
                    "Second plugin for batch validation"
                ),
            )

            patches = self._with_patched_location(base)
            try:
                result = execute_validate(
                    validate_all=True, location="project"
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["total"], 2)

    def test_validate_nonexistent_plugin(self):
        """Validate nonexistent plugin returns failure."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_validate(
                    name="ghost-plugin", location="project"
                )
            finally:
                self._stop_patches(patches)

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])


# ------------------------------------------------------------------
# execute_version
# ------------------------------------------------------------------


class TestExecuteVersion(_PatchedTestCase):
    """Test JSON-based version bumping in plugin.json."""

    def _run_version_bump(self, base, name, bump_type):
        """Helper to run version bump with patched location."""
        patches = self._with_patched_location(base)
        try:
            return execute_version(
                name=name,
                bump_type=bump_type,
                location="project",
            )
        finally:
            self._stop_patches(patches)

    def test_bump_patch(self):
        """Bump patch version: 1.2.3 -> 1.2.4."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "patch-plugin", version="1.2.3"
            )
            result = self._run_version_bump(
                base, "patch-plugin", "patch"
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["old_version"], "1.2.3")
        self.assertEqual(result["new_version"], "1.2.4")

    def test_bump_minor(self):
        """Bump minor version: 1.2.3 -> 1.3.0."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "minor-plugin", version="1.2.3"
            )
            result = self._run_version_bump(
                base, "minor-plugin", "minor"
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["old_version"], "1.2.3")
        self.assertEqual(result["new_version"], "1.3.0")

    def test_bump_major(self):
        """Bump major version: 1.2.3 -> 2.0.0."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "major-plugin", version="1.2.3"
            )
            result = self._run_version_bump(
                base, "major-plugin", "major"
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["old_version"], "1.2.3")
        self.assertEqual(result["new_version"], "2.0.0")

    def test_version_persisted_to_json(self):
        """Verify bumped version is written to plugin.json."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "persist-plugin", version="0.1.0"
            )
            self._run_version_bump(
                base, "persist-plugin", "patch"
            )

            json_path = (
                base
                / "persist-plugin"
                / ".claude-plugin"
                / "plugin.json"
            )
            data = json.loads(
                json_path.read_text(encoding="utf-8")
            )

        self.assertEqual(data["version"], "0.1.1")

    def test_version_nonexistent_plugin_fails(self):
        """Bumping version for nonexistent plugin fails."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = self._run_version_bump(
                base, "no-plugin", "patch"
            )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])


# ------------------------------------------------------------------
# execute_list
# ------------------------------------------------------------------


class TestExecuteList(_PatchedTestCase):
    """Test plugin listing."""

    def test_lists_discovered_plugins(self):
        """Return list of discovered plugins with count."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(base, "list-alpha")
            _create_plugin(base, "list-beta")

            patches = self._with_patched_location(base)
            try:
                result = execute_list(location="project")
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)
        self.assertIn("components", result)
        names = {c["name"] for c in result["components"]}
        self.assertEqual(names, {"list-alpha", "list-beta"})

    def test_empty_list_when_none_found(self):
        """Return count=0 when no plugins exist."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_list(location="project")
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["components"], [])

    def test_list_includes_format(self):
        """Result includes the requested output format."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute_list(
                    location="project",
                    output_format="json",
                )
            finally:
                self._stop_patches(patches)

        self.assertEqual(result["format"], "json")


# ------------------------------------------------------------------
# execute (main dispatcher)
# ------------------------------------------------------------------


class TestExecuteDispatcher(_PatchedTestCase):
    """Test the main execute() dispatcher routing."""

    def test_routes_to_list(self):
        """Dispatch list operation correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(base, "routed-plugin")

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "list",
                        "location": "project",
                    },
                    responses={},
                    templates_dir=Path("/unused"),
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertIn("components", result)

    def test_routes_to_validate(self):
        """Dispatch validate operation correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base,
                "val-plugin",
                description=(
                    "A plugin for validate routing tests"
                ),
            )

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "validate",
                        "name": "val-plugin",
                        "location": "project",
                    },
                    responses={},
                    templates_dir=Path("/unused"),
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertIn("results", result)

    def test_routes_to_version(self):
        """Dispatch version operation correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "ver-plugin", version="0.5.0"
            )

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "version",
                        "name": "ver-plugin",
                        "bump": "minor",
                        "location": "project",
                    },
                    responses={},
                    templates_dir=Path("/unused"),
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["new_version"], "0.6.0")

    def test_routes_to_create(self):
        """Dispatch create operation correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "create",
                        "name": "dispatch-plugin",
                        "description": (
                            "Plugin created via dispatcher"
                        ),
                        "location": "project",
                    },
                    responses={},
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(
            result["success"], result.get("message")
        )
        self.assertIn("path", result)

    def test_unknown_operation_fails(self):
        """Unknown operation returns failure."""
        result = execute(
            context={"operation": "unknown"},
            responses={},
            templates_dir=Path("/unused"),
        )

        self.assertFalse(result["success"])
        self.assertIn("Unknown operation", result["message"])

    def test_version_without_name_fails(self):
        """Version without name returns failure."""
        result = execute(
            context={"operation": "version", "bump": "patch"},
            responses={},
            templates_dir=Path("/unused"),
        )

        self.assertFalse(result["success"])
        self.assertIn("Name is required", result["message"])

    def test_create_with_invalid_name_fails(self):
        """Create with invalid name returns failure."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "create",
                        "name": "Invalid Name!",
                        "description": (
                            "Plugin with invalid name"
                        ),
                        "location": "project",
                    },
                    responses={},
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

        self.assertFalse(result["success"])
        self.assertIn("Invalid name", result["message"])

    def test_create_with_invalid_description_fails(self):
        """Create with too-short description returns failure."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "create",
                        "name": "valid-name",
                        "description": "Short",
                        "location": "project",
                    },
                    responses={},
                    templates_dir=_EXTENSION_TEMPLATES,
                )
            finally:
                self._stop_patches(patches)

        self.assertFalse(result["success"])
        self.assertIn("description", result["message"].lower())

    def test_responses_merged_into_context(self):
        """Responses dict is merged into context for execution."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_plugin(
                base, "merge-plugin", version="1.0.0"
            )

            patches = self._with_patched_location(base)
            try:
                result = execute(
                    context={
                        "operation": "version",
                        "location": "project",
                    },
                    responses={
                        "name": "merge-plugin",
                        "bump": "patch",
                    },
                    templates_dir=Path("/unused"),
                )
            finally:
                self._stop_patches(patches)

        self.assertTrue(result["success"])
        self.assertEqual(result["new_version"], "1.0.1")


# ------------------------------------------------------------------
# PLUGIN_CONFIG
# ------------------------------------------------------------------


class TestPluginConfig(unittest.TestCase):
    """Test the PLUGIN_CONFIG constant."""

    def test_entity_label(self):
        """Entity label is 'plugin'."""
        self.assertEqual(
            PLUGIN_CONFIG["entity_label"], "plugin"
        )

    def test_directory(self):
        """Directory is '.claude-plugin'."""
        self.assertEqual(
            PLUGIN_CONFIG["directory"], ".claude-plugin"
        )

    def test_file_pattern(self):
        """File pattern is 'plugin.json'."""
        self.assertEqual(
            PLUGIN_CONFIG["file_pattern"], "plugin.json"
        )

    def test_no_frontmatter_type(self):
        """Frontmatter type is None (plugins use JSON)."""
        self.assertIsNone(PLUGIN_CONFIG["frontmatter_type"])

    def test_no_main_file_filter(self):
        """Main file filter is None (skip frontmatter check)."""
        self.assertIsNone(PLUGIN_CONFIG["main_file_filter"])


if __name__ == "__main__":
    unittest.main()
