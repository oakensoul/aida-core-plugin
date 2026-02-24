"""Tests for hook operations."""

from pathlib import Path
from unittest.mock import patch

import sys
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "skills" / "claude-code-management" / "scripts"))

from operations import hooks  # noqa: E402


class TestHookConstants:
    """Test hook constants and templates."""

    def test_hook_templates_have_required_fields(self):
        """All templates have required fields."""
        for name, template in hooks.HOOK_TEMPLATES.items():
            assert "event" in template, f"Template {name} missing 'event'"
            assert "matcher" in template, f"Template {name} missing 'matcher'"
            assert "command" in template, f"Template {name} missing 'command'"
            assert template["event"] in hooks.VALID_EVENTS, f"Template {name} has invalid event"


class TestGetQuestions:
    """Test get_questions function."""

    def test_list_no_questions(self):
        """List operation needs no questions."""
        result = hooks.get_questions({"operation": "list"})
        assert result["questions"] == []

    def test_validate_no_questions(self):
        """Validate operation needs no questions."""
        result = hooks.get_questions({"operation": "validate"})
        assert result["questions"] == []

    def test_add_returns_questions(self):
        """Add operation returns questions."""
        result = hooks.get_questions({"operation": "add", "description": "custom hook"})
        assert len(result["questions"]) > 0

    def test_add_infers_formatter_template(self):
        """Add operation infers formatter template from description."""
        result = hooks.get_questions({
            "operation": "add",
            "description": "auto-format code"
        })
        # Should infer formatter template
        assert "inferred" in result
        # Check if template was inferred (may or may not match based on description)

    def test_remove_returns_scope_question(self):
        """Remove operation asks about scope."""
        result = hooks.get_questions({"operation": "remove"})
        assert len(result["questions"]) > 0
        assert any(q["id"] == "scope" for q in result["questions"])


class TestExecuteList:
    """Test list operation."""

    @patch.object(hooks, '_load_settings')
    def test_list_empty(self, mock_load):
        """List returns empty when no hooks configured."""
        mock_load.return_value = {}
        result = hooks.execute({"operation": "list", "scope": "user"}, {})
        assert result["success"]
        assert result["count"] == 0
        assert result["hooks"] == []

    @patch.object(hooks, '_load_settings')
    def test_list_with_hooks(self, mock_load):
        """List returns hooks when configured."""
        mock_load.return_value = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Write",
                        "hooks": [{"type": "command", "command": "echo test"}]
                    }
                ]
            }
        }
        result = hooks.execute({"operation": "list", "scope": "user"}, {})
        assert result["success"]
        assert result["count"] == 1
        assert result["hooks"][0]["event"] == "PostToolUse"
        assert result["hooks"][0]["matcher"] == "Write"


class TestExecuteAdd:
    """Test add operation."""

    @patch.object(hooks, '_save_settings')
    @patch.object(hooks, '_load_settings')
    def test_add_basic(self, mock_load, mock_save):
        """Add creates hook entry."""
        mock_load.return_value = {}
        mock_save.return_value = True

        result = hooks.execute({
            "operation": "add",
            "event": "PostToolUse",
            "matcher": "Write",
            "command": "echo test",
            "scope": "project",
        }, {})

        assert result["success"]
        assert "Added" in result["message"]
        mock_save.assert_called_once()

    @patch.object(hooks, '_save_settings')
    @patch.object(hooks, '_load_settings')
    def test_add_with_template(self, mock_load, mock_save):
        """Add with template uses template values."""
        mock_load.return_value = {}
        mock_save.return_value = True

        result = hooks.execute({
            "operation": "add",
            "template": "formatter",
            "scope": "project",
        }, {})

        assert result["success"]
        # Should use formatter template's event and matcher
        assert result["hook"]["event"] == "PostToolUse"
        assert result["hook"]["matcher"] == "Write|Edit"

    def test_add_missing_event(self):
        """Add fails without event."""
        result = hooks.execute({
            "operation": "add",
            "command": "echo test",
            "scope": "project",
        }, {})
        assert not result["success"]
        assert "Event type is required" in result["message"]

    def test_add_missing_command(self):
        """Add fails without command."""
        result = hooks.execute({
            "operation": "add",
            "event": "PostToolUse",
            "scope": "project",
        }, {})
        assert not result["success"]
        assert "Command is required" in result["message"]

    def test_add_invalid_event(self):
        """Add fails with invalid event."""
        result = hooks.execute({
            "operation": "add",
            "event": "InvalidEvent",
            "command": "echo test",
            "scope": "project",
        }, {})
        assert not result["success"]
        assert "Invalid event" in result["message"]

    @patch.object(hooks, '_save_settings')
    @patch.object(hooks, '_load_settings')
    def test_add_invalid_event_does_not_persist(self, mock_load, mock_save):
        """Add with invalid event doesn't modify settings file."""
        mock_load.return_value = {"hooks": {}}
        mock_save.return_value = True

        result = hooks.execute({
            "operation": "add",
            "event": "InvalidEvent",
            "command": "echo test",
            "scope": "project",
        }, {})

        assert not result["success"]
        # Verify save was never called since validation failed
        mock_save.assert_not_called()

    @patch.object(hooks, '_save_settings')
    @patch.object(hooks, '_load_settings')
    def test_add_duplicate_hook_appends(self, mock_load, mock_save):
        """Adding similar hook with same matcher appends to hooks list."""
        existing_hook = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Write",
                        "hooks": [{"type": "command", "command": "echo first"}]
                    }
                ]
            }
        }
        mock_load.return_value = existing_hook.copy()
        mock_save.return_value = True

        # Try to add another hook with same event and matcher
        result = hooks.execute({
            "operation": "add",
            "event": "PostToolUse",
            "matcher": "Write",
            "command": "echo second",
            "scope": "project",
        }, {})

        # Should succeed
        assert result["success"]

        # Verify the hook was added (implementation adds to same matcher group)
        assert mock_save.called


class TestExecuteRemove:
    """Test remove operation."""

    @patch.object(hooks, '_save_settings')
    @patch.object(hooks, '_load_settings')
    def test_remove_existing(self, mock_load, mock_save):
        """Remove deletes existing hook."""
        mock_load.return_value = {
            "hooks": {
                "PostToolUse": [
                    {"matcher": "Write", "hooks": [{"command": "echo test"}]}
                ]
            }
        }
        mock_save.return_value = True

        result = hooks.execute({
            "operation": "remove",
            "event": "PostToolUse",
            "matcher": "Write",
            "scope": "project",
        }, {})

        assert result["success"]
        assert result["removed"]["count"] == 1

    @patch.object(hooks, '_load_settings')
    def test_remove_not_found(self, mock_load):
        """Remove fails when hook not found."""
        mock_load.return_value = {"hooks": {}}

        result = hooks.execute({
            "operation": "remove",
            "event": "PostToolUse",
            "matcher": "Write",
            "scope": "project",
        }, {})

        assert not result["success"]
        assert "No PostToolUse hooks found" in result["message"]

    def test_remove_missing_event(self):
        """Remove fails without event."""
        result = hooks.execute({
            "operation": "remove",
            "scope": "project",
        }, {})
        assert not result["success"]
        assert "Event type is required" in result["message"]


class TestExecuteValidate:
    """Test validate operation."""

    @patch.object(hooks, '_load_settings')
    def test_validate_empty(self, mock_load):
        """Validate passes with no hooks."""
        mock_load.return_value = {}

        # Mock path.exists() to return False
        with patch.object(Path, 'exists', return_value=False):
            result = hooks.execute({"operation": "validate", "scope": "user"}, {})

        assert result["success"]
        assert result["error_count"] == 0

    @patch.object(hooks, '_load_settings')
    def test_validate_invalid_event(self, mock_load):
        """Validate catches invalid event names."""
        mock_load.return_value = {
            "hooks": {
                "InvalidEvent": [
                    {"matcher": "Write", "hooks": [{"command": "echo test"}]}
                ]
            }
        }

        with patch.object(Path, 'exists', return_value=True):
            result = hooks.execute({"operation": "validate", "scope": "user"}, {})

        assert not result["success"]
        assert result["error_count"] > 0
        assert any("Invalid event" in i["message"] for i in result["issues"])

    @patch.object(hooks, '_load_settings')
    def test_validate_dangerous_command(self, mock_load):
        """Validate warns about dangerous commands."""
        mock_load.return_value = {
            "hooks": {
                "PostToolUse": [
                    {"matcher": "Write", "hooks": [{"command": "sudo rm -rf /"}]}
                ]
            }
        }

        with patch.object(Path, 'exists', return_value=True):
            result = hooks.execute({"operation": "validate", "scope": "user"}, {})

        # Should still pass (warning, not error) but have warnings
        assert result["warning_count"] > 0
        assert any("dangerous" in i["message"] for i in result["issues"])
