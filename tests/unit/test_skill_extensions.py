"""Unit tests for skill-manager extension CRUD operations.

Tests the skill-manager's operations/extensions.py module which
provides find, create, validate, version, list, and dispatch
operations for skills.  These functions are thin wrappers around
shared.extension_utils parameterised with SKILL_CONFIG.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# ------------------------------------------------------------------
# Path / module setup
# ------------------------------------------------------------------

# Clear cached modules to prevent cross-manager conflicts in pytest
for _mod_name in list(sys.modules):
    if (
        _mod_name == "operations"
        or _mod_name.startswith("operations.")
        or _mod_name == "_paths"
    ):
        del sys.modules[_mod_name]

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(
    0,
    str(
        _project_root / "skills" / "skill-manager" / "scripts"
    ),
)

from operations.extensions import (  # noqa: E402
    SKILL_CONFIG,
    component_exists,
    execute,
    execute_create,
    execute_list,
    execute_validate,
    execute_version,
    find_components,
    get_questions,
    validate_file_frontmatter,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_VALID_SKILL_FRONTMATTER = """\
---
type: skill
name: {name}
description: {description}
version: {version}
---

# {name}

Body content.
"""


def _write_skill(base_dir, name, description=None, version="0.1.0"):
    """Create a minimal SKILL.md inside base_dir/skills/{name}/."""
    if description is None:
        description = f"Test skill {name}"
    skill_dir = base_dir / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        _VALID_SKILL_FRONTMATTER.format(
            name=name,
            description=description,
            version=version,
        ),
        encoding="utf-8",
    )
    return skill_file


# ==================================================================
# 1. find_components
# ==================================================================


class TestFindComponents:
    """Test skill discovery via find_components()."""

    def test_finds_skills_in_project_location(self, tmp_path):
        """Skills in the project .claude/skills/ are discovered."""
        project_claude = tmp_path / ".claude"
        _write_skill(project_claude, "my-skill")

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=project_claude,
        ):
            result = find_components(location="project")

        assert len(result) == 1
        assert result[0]["name"] == "my-skill"
        assert result[0]["location"] == "project"

    def test_finds_skills_in_user_location(self, tmp_path):
        """Skills in the user ~/.claude/skills/ are discovered."""
        user_claude = tmp_path / ".claude"
        _write_skill(user_claude, "user-skill")

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=user_claude,
        ):
            result = find_components(location="user")

        assert len(result) == 1
        assert result[0]["name"] == "user-skill"
        assert result[0]["location"] == "user"

    def test_returns_empty_when_no_skills(self, tmp_path):
        """Empty skills directory yields empty list."""
        empty_claude = tmp_path / ".claude"
        (empty_claude / "skills").mkdir(parents=True)

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=empty_claude,
        ):
            result = find_components(location="project")

        assert result == []

    def test_handles_missing_directory_gracefully(self, tmp_path):
        """Non-existent skills directory yields empty list."""
        no_skills = tmp_path / ".claude"
        no_skills.mkdir(parents=True)
        # Deliberately do NOT create a skills/ subdirectory

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=no_skills,
        ):
            result = find_components(location="project")

        assert result == []


# ==================================================================
# 2. component_exists
# ==================================================================


class TestComponentExists:
    """Test skill existence check via component_exists()."""

    def test_returns_true_for_existing_skill(self, tmp_path):
        """Returns True when skill directory contains a match."""
        claude_dir = tmp_path / ".claude"
        _write_skill(claude_dir, "existing-skill")

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            assert component_exists("existing-skill", "project")

    def test_returns_false_for_nonexistent_skill(self, tmp_path):
        """Returns False when no matching skill is found."""
        claude_dir = tmp_path / ".claude"
        (claude_dir / "skills").mkdir(parents=True)

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            assert not component_exists("ghost", "project")


# ==================================================================
# 3. get_questions
# ==================================================================


class TestGetQuestions:
    """Test Phase 1 question generation."""

    def test_create_returns_description_question(self):
        """Create without description asks for one."""
        ctx = {"operation": "create"}
        result = get_questions(ctx)

        ids = [q["id"] for q in result["questions"]]
        assert "description" in ids

    def test_create_with_description_infers_metadata(self):
        """Create with description infers name and version."""
        ctx = {
            "operation": "create",
            "description": "Handles database migrations",
        }
        result = get_questions(ctx)

        assert "inferred" in result
        assert "name" in result["inferred"]
        assert result["inferred"]["version"] == "0.1.0"

    def test_validate_without_name_asks(self):
        """Validate without name asks for it."""
        ctx = {"operation": "validate"}
        result = get_questions(ctx)

        ids = [q["id"] for q in result["questions"]]
        assert "name" in ids

    def test_validate_with_all_flag_no_name_question(self):
        """Validate --all does not ask for a name."""
        ctx = {"operation": "validate", "all": True}
        result = get_questions(ctx)

        ids = [q["id"] for q in result["questions"]]
        assert "name" not in ids

    def test_version_without_name_asks(self):
        """Version without name asks for it."""
        ctx = {"operation": "version"}
        result = get_questions(ctx)

        ids = [q["id"] for q in result["questions"]]
        assert "name" in ids

    def test_list_no_questions(self):
        """List operation needs no questions."""
        ctx = {"operation": "list"}
        result = get_questions(ctx)

        assert len(result["questions"]) == 0
        assert result["inferred"]["location"] == "user"

    def test_unknown_operation_returns_empty(self):
        """Unknown operation returns default result."""
        ctx = {"operation": "frobnicate"}
        result = get_questions(ctx)

        # Should still return a valid result structure
        assert "questions" in result
        assert "inferred" in result
        assert "validation" in result


# ==================================================================
# 4. execute_create
# ==================================================================


class TestExecuteCreate:
    """Test skill creation via execute_create()."""

    def test_creates_skill_directory_and_file(self, tmp_path):
        """Creates SKILL.md from template in correct path."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )
        base = tmp_path / ".claude"

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=base,
        ):
            result = execute_create(
                name="my-new-skill",
                description="A brand new skill for testing",
                version="0.1.0",
                tags=["custom"],
                location="project",
                templates_dir=templates,
            )

        assert result["success"]
        assert "path" in result
        created = Path(result["path"])
        assert created.exists()
        assert created.name == "SKILL.md"
        assert "my-new-skill" in str(created)

    def test_creates_subdirectories(self, tmp_path):
        """References/ and scripts/ subdirs are created."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )
        base = tmp_path / ".claude"

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=base,
        ):
            result = execute_create(
                name="sub-test",
                description="Testing subdirectory creation",
                version="0.1.0",
                tags=["custom"],
                location="project",
                templates_dir=templates,
            )

        assert result["success"]
        skill_dir = Path(result["path"]).parent
        assert (skill_dir / "references").is_dir()
        assert (skill_dir / "scripts").is_dir()

    def test_rejects_duplicate_via_get_questions(
        self, tmp_path
    ):
        """get_questions flags when inferred name already exists."""
        claude_dir = tmp_path / ".claude"
        # Create a skill whose name matches what
        # infer_from_description will produce from the
        # description below ("duplicate skill" -> "duplicate-skill")
        _write_skill(claude_dir, "duplicate-skill")

        ctx = {
            "operation": "create",
            "description": "duplicate skill",
            "location": "project",
        }

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            questions = get_questions(ctx)

        # Should ask for a different name because one exists
        ids = [q["id"] for q in questions["questions"]]
        assert "name" in ids
        question_text = next(
            q["question"]
            for q in questions["questions"]
            if q["id"] == "name"
        )
        assert "already exists" in question_text

    def test_rejects_invalid_name_via_execute(self, tmp_path):
        """Execute dispatcher rejects invalid names."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        ctx = {
            "operation": "create",
            "name": "Invalid Name!",
            "description": "Test skill for testing purposes",
        }

        result = execute(ctx, {}, templates)
        assert not result["success"]
        assert "Invalid name" in result["message"]


# ==================================================================
# 5. execute_validate
# ==================================================================


class TestExecuteValidate:
    """Test skill validation via execute_validate()."""

    def test_validates_valid_skill(self, tmp_path):
        """Valid skill frontmatter passes validation."""
        claude_dir = tmp_path / ".claude"
        _write_skill(
            claude_dir,
            "valid-skill",
            description="A perfectly valid skill",
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_validate(
                name="valid-skill", location="project"
            )

        assert result["success"]
        assert result["operation"] == "validate"
        assert result["summary"]["valid"] == 1
        assert result["summary"]["invalid"] == 0
        assert result["results"][0]["valid"]

    def test_catches_missing_required_fields(self, tmp_path):
        """Skill with missing description fails validation."""
        claude_dir = tmp_path / ".claude"
        skill_dir = claude_dir / "skills" / "bad-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\ntype: skill\nname: bad-skill\n"
            "version: 0.1.0\n---\n# Bad\n",
            encoding="utf-8",
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_validate(
                name="bad-skill", location="project"
            )

        assert result["success"]
        assert result["summary"]["invalid"] == 1
        errors = result["results"][0]["errors"]
        assert any("Description" in e for e in errors)

    def test_catches_wrong_type_field(self, tmp_path):
        """Skill with wrong type in frontmatter is noted."""
        claude_dir = tmp_path / ".claude"
        skill_dir = claude_dir / "skills" / "wrong-type"
        skill_dir.mkdir(parents=True)
        # Use type "agent" instead of "skill"
        (skill_dir / "SKILL.md").write_text(
            "---\ntype: agent\nname: wrong-type\n"
            "description: Wrong type skill\n"
            "version: 0.1.0\n---\n# Wrong\n",
            encoding="utf-8",
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            # find_extensions only returns items matching the
            # expected frontmatter_type, so a "wrong type" file
            # won't appear in results at all.
            result = execute_validate(
                name="wrong-type", location="project"
            )

        # The skill is not found because type doesn't match
        assert not result["success"]
        assert "not found" in result["message"]

    def test_returns_standardized_response_shape(self, tmp_path):
        """Validate response has success, operation, results, summary."""
        claude_dir = tmp_path / ".claude"
        _write_skill(claude_dir, "shape-test")

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_validate(
                name="shape-test", location="project"
            )

        assert "success" in result
        assert "operation" in result
        assert "results" in result
        assert "summary" in result
        assert isinstance(result["results"], list)
        assert "total" in result["summary"]
        assert "valid" in result["summary"]
        assert "invalid" in result["summary"]

    def test_validate_file_frontmatter_valid(self):
        """validate_file_frontmatter passes on valid content."""
        content = (
            "---\n"
            "type: skill\n"
            "name: my-skill\n"
            "description: A valid skill description\n"
            "version: 0.1.0\n"
            "---\n\n# Body\n"
        )
        result = validate_file_frontmatter(content)
        assert result["valid"]
        assert result["errors"] == []

    def test_validate_file_frontmatter_missing_fields(self):
        """validate_file_frontmatter catches missing fields."""
        content = (
            "---\n"
            "type: skill\n"
            "name: my-skill\n"
            "---\n\n# Body\n"
        )
        result = validate_file_frontmatter(content)
        assert not result["valid"]
        assert any(
            "description" in e.lower()
            for e in result["errors"]
        )
        assert any(
            "version" in e.lower() for e in result["errors"]
        )

    def test_validate_file_frontmatter_wrong_type(self):
        """validate_file_frontmatter catches wrong type."""
        content = (
            "---\n"
            "type: agent\n"
            "name: my-skill\n"
            "description: A valid skill description\n"
            "version: 0.1.0\n"
            "---\n\n# Body\n"
        )
        result = validate_file_frontmatter(content)
        assert not result["valid"]
        assert any("type" in e.lower() for e in result["errors"])


# ==================================================================
# 6. execute_version
# ==================================================================


class TestExecuteVersion:
    """Test version bumping via execute_version()."""

    def test_bumps_patch_version(self, tmp_path):
        """Patch bump increments the third number."""
        claude_dir = tmp_path / ".claude"
        _write_skill(
            claude_dir, "ver-skill", version="1.2.3"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_version(
                name="ver-skill",
                bump_type="patch",
                location="project",
            )

        assert result["success"]
        assert result["old_version"] == "1.2.3"
        assert result["new_version"] == "1.2.4"

    def test_bumps_minor_version(self, tmp_path):
        """Minor bump increments the second number."""
        claude_dir = tmp_path / ".claude"
        _write_skill(
            claude_dir, "ver-skill", version="1.2.3"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_version(
                name="ver-skill",
                bump_type="minor",
                location="project",
            )

        assert result["success"]
        assert result["old_version"] == "1.2.3"
        assert result["new_version"] == "1.3.0"

    def test_bumps_major_version(self, tmp_path):
        """Major bump increments the first number."""
        claude_dir = tmp_path / ".claude"
        _write_skill(
            claude_dir, "ver-skill", version="1.2.3"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_version(
                name="ver-skill",
                bump_type="major",
                location="project",
            )

        assert result["success"]
        assert result["old_version"] == "1.2.3"
        assert result["new_version"] == "2.0.0"

    def test_version_file_is_rewritten(self, tmp_path):
        """Version bump actually changes the file on disk."""
        claude_dir = tmp_path / ".claude"
        skill_file = _write_skill(
            claude_dir, "disk-skill", version="0.5.0"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            execute_version(
                name="disk-skill",
                bump_type="patch",
                location="project",
            )

        content = skill_file.read_text(encoding="utf-8")
        assert "version: 0.5.1" in content
        assert "version: 0.5.0" not in content

    def test_handles_missing_skill(self, tmp_path):
        """Version bump on nonexistent skill returns failure."""
        claude_dir = tmp_path / ".claude"
        (claude_dir / "skills").mkdir(parents=True)

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_version(
                name="nonexistent",
                bump_type="patch",
                location="project",
            )

        assert not result["success"]
        assert "not found" in result["message"]


# ==================================================================
# 7. execute_list
# ==================================================================


class TestExecuteList:
    """Test skill listing via execute_list()."""

    def test_lists_skills_found_in_project(self, tmp_path):
        """Lists skills present in a location."""
        claude_dir = tmp_path / ".claude"
        _write_skill(claude_dir, "list-skill-a")
        _write_skill(claude_dir, "list-skill-b")

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_list(location="project")

        assert result["success"]
        assert result["count"] == 2
        names = {c["name"] for c in result["components"]}
        assert "list-skill-a" in names
        assert "list-skill-b" in names

    def test_returns_empty_list_message(self, tmp_path):
        """Returns count 0 when no skills found."""
        claude_dir = tmp_path / ".claude"
        (claude_dir / "skills").mkdir(parents=True)

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_list(location="project")

        assert result["success"]
        assert result["count"] == 0
        assert result["components"] == []

    def test_returns_standardized_response(self, tmp_path):
        """List result has success, components, count, format."""
        claude_dir = tmp_path / ".claude"
        (claude_dir / "skills").mkdir(parents=True)

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute_list(location="project")

        assert "success" in result
        assert "components" in result
        assert "count" in result
        assert "format" in result


# ==================================================================
# 8. execute (main dispatcher)
# ==================================================================


class TestExecuteDispatcher:
    """Test the main execute() dispatcher."""

    def test_routes_to_list(self, tmp_path):
        """Dispatcher routes list operation correctly."""
        claude_dir = tmp_path / ".claude"
        (claude_dir / "skills").mkdir(parents=True)
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute(
                {"operation": "list", "location": "project"},
                {},
                templates,
            )

        assert result["success"]
        assert "components" in result

    def test_routes_to_validate(self, tmp_path):
        """Dispatcher routes validate operation correctly."""
        claude_dir = tmp_path / ".claude"
        _write_skill(claude_dir, "val-skill")
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute(
                {
                    "operation": "validate",
                    "name": "val-skill",
                    "location": "project",
                },
                {},
                templates,
            )

        assert result["success"]
        assert result["operation"] == "validate"

    def test_routes_to_version(self, tmp_path):
        """Dispatcher routes version operation correctly."""
        claude_dir = tmp_path / ".claude"
        _write_skill(
            claude_dir, "ver-skill", version="0.1.0"
        )
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        with patch(
            "shared.extension_utils.get_location_path",
            return_value=claude_dir,
        ):
            result = execute(
                {
                    "operation": "version",
                    "name": "ver-skill",
                    "bump": "minor",
                    "location": "project",
                },
                {},
                templates,
            )

        assert result["success"]
        assert result["new_version"] == "0.2.0"

    def test_handles_unknown_operation(self):
        """Dispatcher returns error for unknown operation."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        result = execute(
            {"operation": "frobnicate"},
            {},
            templates,
        )

        assert not result["success"]
        assert "Unknown operation" in result["message"]

    def test_version_missing_name_returns_error(self):
        """Version operation without name returns error."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        result = execute(
            {"operation": "version", "bump": "patch"},
            {},
            templates,
        )

        assert not result["success"]
        assert "Name is required" in result["message"]

    def test_create_invalid_description_returns_error(self):
        """Create with too-short description returns error."""
        templates = (
            _project_root
            / "skills"
            / "skill-manager"
            / "templates"
        )

        result = execute(
            {
                "operation": "create",
                "name": "valid-name",
                "description": "Short",
            },
            {},
            templates,
        )

        assert not result["success"]
        assert "description" in result["message"].lower()


# ==================================================================
# 9. SKILL_CONFIG sanity checks
# ==================================================================


class TestSkillConfig:
    """Verify SKILL_CONFIG has expected structure."""

    def test_entity_label(self):
        assert SKILL_CONFIG["entity_label"] == "skill"

    def test_directory(self):
        assert SKILL_CONFIG["directory"] == "skills"

    def test_file_pattern(self):
        assert "{name}" in SKILL_CONFIG["file_pattern"]
        assert "SKILL.md" in SKILL_CONFIG["file_pattern"]

    def test_frontmatter_type(self):
        assert SKILL_CONFIG["frontmatter_type"] == "skill"

    def test_create_subdirs(self):
        assert "references" in SKILL_CONFIG["create_subdirs"]
        assert "scripts" in SKILL_CONFIG["create_subdirs"]

    def test_main_file_filter(self):
        filt = SKILL_CONFIG["main_file_filter"]
        assert filt("skills/my-skill/SKILL.md")
        assert not filt("skills/my-skill/README.md")
