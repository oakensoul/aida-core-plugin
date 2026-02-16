"""Unit tests for AIDA feedback system.

This test suite covers all functionality in the feedback.py script including
general feedback, bug reports, feature requests, and GitHub integration.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "aida-dispatch" / "scripts"))

import feedback


class TestMainEntryPoint(unittest.TestCase):
    """Test main() entry point routing."""

    def test_main_no_arguments(self):
        """Test main() with no arguments shows error."""
        with patch('sys.argv', ['feedback.py']):
            result = feedback.main()
            self.assertEqual(result, 1)

    def test_main_unknown_feedback_type(self):
        """Test main() with unknown feedback type."""
        with patch('sys.argv', ['feedback.py', 'unknown']):
            result = feedback.main()
            self.assertEqual(result, 1)

    @patch('feedback.submit_feedback', return_value=0)
    def test_main_routes_to_feedback(self, mock_submit):
        """Test main() routes to submit_feedback()."""
        with patch('sys.argv', ['feedback.py', 'feedback']):
            result = feedback.main()
            self.assertEqual(result, 0)
            mock_submit.assert_called_once()

    @patch('feedback.submit_bug', return_value=0)
    def test_main_routes_to_bug(self, mock_submit):
        """Test main() routes to submit_bug()."""
        with patch('sys.argv', ['feedback.py', 'bug']):
            result = feedback.main()
            self.assertEqual(result, 0)
            mock_submit.assert_called_once()

    @patch('feedback.submit_feature_request', return_value=0)
    def test_main_routes_to_feature_request(self, mock_submit):
        """Test main() routes to submit_feature_request()."""
        with patch('sys.argv', ['feedback.py', 'feature-request']):
            result = feedback.main()
            self.assertEqual(result, 0)
            mock_submit.assert_called_once()


class TestSubmitFeedback(unittest.TestCase):
    """Test submit_feedback() function."""

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm privacy notice
        'Great tool!',  # feedback
        '5',  # category (UX)
        'Works perfectly'  # context
    ])
    def test_submit_feedback_success(self, mock_input, mock_create):
        """Test successful feedback submission."""
        result = feedback.submit_feedback()

        self.assertEqual(result, 0)
        mock_create.assert_called_once()

        # Verify the call arguments
        call_args = mock_create.call_args
        self.assertIn('[Feedback]', call_args[1]['title'])
        self.assertIn('User Experience', call_args[1]['body'])
        self.assertIn('Great tool!', call_args[1]['body'])
        self.assertIn('Works perfectly', call_args[1]['body'])
        self.assertEqual(call_args[1]['labels'], ['feedback'])

    @patch('builtins.input', side_effect=['n'])
    def test_submit_feedback_cancelled_privacy(self, mock_input):
        """Test feedback submission cancelled at privacy notice."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

    @patch('builtins.input', side_effect=['y', ''])
    def test_submit_feedback_cancelled_empty(self, mock_input):
        """Test feedback submission cancelled with empty input."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'This is a very long feedback message that exceeds fifty characters',
        '1',  # category
        ''  # no context
    ])
    def test_submit_feedback_long_title(self, mock_input, mock_create):
        """Test feedback with title truncation."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        title = call_args[1]['title']
        self.assertIn('...', title)
        self.assertLess(len(title), 65)  # [Feedback] + 50 chars + ...

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'Feedback',
        'invalid',  # invalid category
        ''
    ])
    def test_submit_feedback_invalid_category(self, mock_input, mock_create):
        """Test feedback with invalid category defaults to 'Other'."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        self.assertIn('Other', call_args[1]['body'])


class TestSubmitBug(unittest.TestCase):
    """Test submit_bug() function."""

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'App crashes on startup',  # description
        'Step 1',  # reproduce step 1
        'Step 2',  # reproduce step 2
        '',  # end of steps
        'App should start',  # expected
        'App crashes'  # actual
    ])
    def test_submit_bug_success(self, mock_input, mock_create):
        """Test successful bug report submission."""
        result = feedback.submit_bug()

        self.assertEqual(result, 0)
        mock_create.assert_called_once()

        # Verify the call arguments
        call_args = mock_create.call_args
        self.assertIn('[Bug]', call_args[1]['title'])
        self.assertIn('App crashes on startup', call_args[1]['body'])
        self.assertIn('Step 1', call_args[1]['body'])
        self.assertIn('Step 2', call_args[1]['body'])
        self.assertIn('App should start', call_args[1]['body'])
        self.assertIn('App crashes', call_args[1]['body'])
        self.assertIn('OS:', call_args[1]['body'])
        self.assertIn('Python:', call_args[1]['body'])
        self.assertIn('AIDA:', call_args[1]['body'])
        self.assertEqual(call_args[1]['labels'], ['bug', 'needs-triage'])

    @patch('builtins.input', side_effect=['n'])
    def test_submit_bug_cancelled_privacy(self, mock_input):
        """Test bug report cancelled at privacy notice."""
        result = feedback.submit_bug()
        self.assertEqual(result, 0)

    @patch('builtins.input', side_effect=['y', ''])
    def test_submit_bug_cancelled_empty(self, mock_input):
        """Test bug report cancelled with empty input."""
        result = feedback.submit_bug()
        self.assertEqual(result, 0)

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'Bug description',
        '',  # no steps
        '',  # no expected
        ''   # no actual
    ])
    def test_submit_bug_minimal_info(self, mock_input, mock_create):
        """Test bug report with minimal information."""
        result = feedback.submit_bug()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        self.assertIn('No steps provided', call_args[1]['body'])
        self.assertIn('Not specified', call_args[1]['body'])


class TestSubmitFeatureRequest(unittest.TestCase):
    """Test submit_feature_request() function."""

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'Need dark mode',  # problem
        'Add theme toggle',  # solution
        'CSS variables',  # alternatives
        '2'  # priority
    ])
    def test_submit_feature_request_success(self, mock_input, mock_create):
        """Test successful feature request submission."""
        result = feedback.submit_feature_request()

        self.assertEqual(result, 0)
        mock_create.assert_called_once()

        # Verify the call arguments
        call_args = mock_create.call_args
        self.assertIn('[Feature]', call_args[1]['title'])
        self.assertIn('Need dark mode', call_args[1]['body'])
        self.assertIn('Add theme toggle', call_args[1]['body'])
        self.assertIn('CSS variables', call_args[1]['body'])
        self.assertIn('Would improve my workflow', call_args[1]['body'])
        self.assertEqual(call_args[1]['labels'], ['enhancement', 'needs-review'])

    @patch('builtins.input', side_effect=['n'])
    def test_submit_feature_request_cancelled_privacy(self, mock_input):
        """Test feature request cancelled at privacy notice."""
        result = feedback.submit_feature_request()
        self.assertEqual(result, 0)

    @patch('builtins.input', side_effect=['y', ''])
    def test_submit_feature_request_cancelled_empty(self, mock_input):
        """Test feature request cancelled with empty input."""
        result = feedback.submit_feature_request()
        self.assertEqual(result, 0)

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'Feature request',
        '',  # no solution
        '',  # no alternatives
        'invalid'  # invalid priority
    ])
    def test_submit_feature_request_defaults(self, mock_input, mock_create):
        """Test feature request with default values."""
        result = feedback.submit_feature_request()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        self.assertIn('Not specified', call_args[1]['body'])
        self.assertIn('None', call_args[1]['body'])
        self.assertIn('Nice to have', call_args[1]['body'])


class TestCreateGitHubIssue(unittest.TestCase):
    """Test create_github_issue() function."""

    @patch('builtins.input', return_value='yes')
    @patch('feedback.check_rate_limit', return_value=True)
    @patch('feedback.check_gh_cli', return_value=True)
    @patch('subprocess.run')
    def test_create_issue_success(self, mock_run, mock_check, mock_rate, mock_input):
        """Test successful GitHub issue creation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://github.com/oakensoul/aida-marketplace/issues/123\n',
            stderr=''
        )

        result = feedback.create_github_issue(
            title='Test Issue',
            body='Test body for the GitHub issue creation test',
            labels=['test']
        )

        self.assertEqual(result, 0)
        self.assertEqual(mock_run.call_count, 2)  # auth check + issue create

        # Verify subprocess call (last call is the issue creation)
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], 'gh')
        self.assertEqual(call_args[1], 'issue')
        self.assertEqual(call_args[2], 'create')
        self.assertIn('--repo', call_args)
        self.assertIn('oakensoul/aida-marketplace', call_args)
        self.assertIn('--title', call_args)
        self.assertIn('Test Issue', call_args)
        self.assertIn('--label', call_args)
        self.assertIn('test', call_args)

    @patch('feedback.check_gh_cli', return_value=False)
    def test_create_issue_gh_not_installed(self, mock_check):
        """Test issue creation when gh CLI not installed."""
        result = feedback.create_github_issue(
            title='Test',
            body='Body',
            labels=['test']
        )

        self.assertEqual(result, 1)

    @patch('feedback.check_gh_cli', return_value=True)
    @patch('subprocess.run')
    def test_create_issue_gh_error(self, mock_run, mock_check):
        """Test issue creation when gh CLI returns error."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Error: not authenticated'
        )

        result = feedback.create_github_issue(
            title='Test',
            body='Body',
            labels=['test']
        )

        self.assertEqual(result, 1)

    @patch('feedback.check_gh_cli', return_value=True)
    @patch('subprocess.run')
    def test_create_issue_timeout(self, mock_run, mock_check):
        """Test issue creation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('gh', 30)

        result = feedback.create_github_issue(
            title='Test',
            body='Body',
            labels=['test']
        )

        self.assertEqual(result, 1)

    @patch('feedback.check_gh_cli', return_value=True)
    @patch('subprocess.run')
    def test_create_issue_exception(self, mock_run, mock_check):
        """Test issue creation with unexpected exception."""
        mock_run.side_effect = Exception('Unexpected error')

        result = feedback.create_github_issue(
            title='Test',
            body='Body',
            labels=['test']
        )

        self.assertEqual(result, 1)

    @patch('builtins.input', return_value='yes')
    @patch('feedback.check_rate_limit', return_value=True)
    @patch('feedback.check_gh_cli', return_value=True)
    @patch('subprocess.run')
    def test_create_issue_command_structure(self, mock_run, mock_check, mock_rate, mock_input):
        """Test that subprocess command has correct structure."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://github.com/oakensoul/aida-marketplace/issues/1\n',
            stderr=''
        )

        feedback.create_github_issue(
            title='Test Title',
            body='Test body content for structure verification test',
            labels=['label1', 'label2']
        )

        # Get the actual issue creation call (second call)
        self.assertEqual(mock_run.call_count, 2)
        call_args = mock_run.call_args_list[1][0][0]

        # Verify command structure
        self.assertEqual(call_args[0], 'gh')
        self.assertEqual(call_args[1], 'issue')
        self.assertEqual(call_args[2], 'create')
        self.assertIn('--repo', call_args)
        self.assertIn('oakensoul/aida-marketplace', call_args)
        self.assertIn('--title', call_args)
        self.assertIn('Test Title', call_args)
        self.assertIn('--body', call_args)
        self.assertIn('--label', call_args)
        # Verify labels are in the command (may be comma-separated)
        labels_str = ','.join(call_args)
        self.assertIn('label1', labels_str)
        self.assertIn('label2', labels_str)

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'A' * 200,  # very long title
        '1',  # category
        ''
    ])
    def test_submit_feedback_very_long_title_truncated(self, mock_input, mock_create):
        """Test feedback with very long title is truncated."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        title = call_args[1]['title']
        # Title should be truncated
        self.assertLess(len(title), 100)
        self.assertIn('...', title)

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',  # confirm
        'Feedback with <script>alert("xss")</script>',  # special chars
        '1',
        'Context with "quotes" and \'apostrophes\''
    ])
    def test_submit_feedback_special_characters(self, mock_input, mock_create):
        """Test feedback with special characters is handled."""
        result = feedback.submit_feedback()
        self.assertEqual(result, 0)

        call_args = mock_create.call_args
        # Verify body contains the special characters (not stripped)
        self.assertIn('<script>', call_args[1]['body'])
        self.assertIn('"quotes"', call_args[1]['body'])
        self.assertIn("'apostrophes'", call_args[1]['body'])

    @patch('feedback.create_github_issue', return_value=0)
    @patch('builtins.input', side_effect=[
        'y',
        '',  # empty body - should cancel
    ])
    def test_submit_bug_empty_body_cancels(self, mock_input, mock_create):
        """Test bug report with empty body cancels submission."""
        result = feedback.submit_bug()
        self.assertEqual(result, 0)
        # Should not call create_github_issue
        mock_create.assert_not_called()


class TestCheckGhCli(unittest.TestCase):
    """Test check_gh_cli() function."""

    @patch('shutil.which', return_value='/usr/local/bin/gh')
    def test_check_gh_cli_installed(self, mock_which):
        """Test check when gh CLI is installed."""
        result = feedback.check_gh_cli()
        self.assertTrue(result)
        mock_which.assert_called_once_with('gh')

    @patch('shutil.which', return_value=None)
    def test_check_gh_cli_not_installed(self, mock_which):
        """Test check when gh CLI is not installed."""
        result = feedback.check_gh_cli()
        self.assertFalse(result)


class TestGetAidaVersion(unittest.TestCase):
    """Test get_aida_version() function."""

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', return_value='{"version": "1.0.0"}')
    def test_get_version_success(self, mock_read, mock_exists):
        """Test getting version from plugin.json."""
        version = feedback.get_aida_version()
        self.assertEqual(version, '1.0.0')

    @patch('pathlib.Path.exists', return_value=False)
    def test_get_version_file_not_found(self, mock_exists):
        """Test getting version when plugin.json doesn't exist."""
        version = feedback.get_aida_version()
        self.assertEqual(version, 'unknown')

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', return_value='invalid json')
    def test_get_version_invalid_json(self, mock_read, mock_exists):
        """Test getting version with invalid JSON."""
        version = feedback.get_aida_version()
        self.assertEqual(version, 'unknown')

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', return_value='{"name": "test"}')
    def test_get_version_missing_field(self, mock_read, mock_exists):
        """Test getting version when version field is missing."""
        version = feedback.get_aida_version()
        self.assertEqual(version, 'unknown')


if __name__ == '__main__':
    unittest.main()
