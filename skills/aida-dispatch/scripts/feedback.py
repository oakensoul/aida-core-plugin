#!/usr/bin/env python3
"""AIDA Feedback System

This script handles user feedback submission to GitHub:
- /aida feedback - General feedback with category selection
- /aida bug - Structured bug report with environment info
- /aida feature-request - Feature request with use case and priority

All feedback is submitted as GitHub issues to the aida-marketplace repository.

Usage:
    python feedback.py feedback
    python feedback.py bug
    python feedback.py feature-request

Exit codes:
    0   - Success
    1   - Error occurred
    130 - User cancelled (Ctrl+C)
"""

import sys
import subprocess
import platform
import shutil
import time
import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import argparse


# Security constants
MAX_INPUT_LENGTH = 5000  # Maximum characters for feedback/description
MIN_INPUT_LENGTH = 10    # Minimum characters to prevent spam
MIN_SUBMISSION_INTERVAL = 60  # Minimum seconds between submissions
RATE_LIMIT_FILE = Path.home() / ".claude" / ".aida_feedback_last"


def detect_system_context() -> Dict[str, str]:
    """Detect basic system context for bug reports.

    Returns:
        Dictionary of system information useful for debugging

    Security:
        - Only captures non-sensitive system information
        - Sanitizes paths to prevent PII leakage
    """
    context = {}

    try:
        # OS information
        context['os'] = platform.system()
        context['os_version'] = platform.release()
        context['architecture'] = platform.machine()

        # Python version
        context['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Shell
        shell = os.getenv('SHELL', '')
        context['shell'] = Path(shell).name if shell else 'unknown'

        # Git version (if available)
        try:
            result = subprocess.run(['git', '--version'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                context['git_version'] = result.stdout.strip()
        except Exception:
            context['git_version'] = 'not installed'

        # AIDA version (if available)
        context['aida_version'] = get_aida_version()

    except Exception as e:
        # Best effort - don't fail if we can't detect
        context['detection_error'] = str(e)

    return context


def format_system_context(context: Dict[str, str]) -> str:
    """Format system context for display or inclusion in bug report.

    Args:
        context: Dictionary of system information

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("**System Context:**")
    lines.append(f"- OS: {context.get('os', 'unknown')} {context.get('os_version', '')}")
    lines.append(f"- Architecture: {context.get('architecture', 'unknown')}")
    lines.append(f"- Python: {context.get('python_version', 'unknown')}")
    lines.append(f"- Shell: {context.get('shell', 'unknown')}")
    lines.append(f"- Git: {context.get('git_version', 'not installed')}")
    lines.append(f"- AIDA: {context.get('aida_version', 'unknown')}")

    return '\n'.join(lines)


def sanitize_gh_input(text: str, max_length: int = MAX_INPUT_LENGTH,
                      allow_multiline: bool = True) -> str:
    """Sanitize input for gh CLI to prevent injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        allow_multiline: Whether to allow newlines

    Returns:
        Sanitized text safe for gh CLI

    Raises:
        ValueError: If input is too long or contains dangerous patterns

    Security:
        - Enforces length limits to prevent DoS
        - Removes argument injection patterns
        - Validates character content
    """
    # Enforce length limit
    if len(text) > max_length:
        raise ValueError(f"Input too long (max {max_length} chars)")

    # Enforce minimum length
    if len(text.strip()) < MIN_INPUT_LENGTH:
        raise ValueError(f"Input too short (min {MIN_INPUT_LENGTH} chars)")

    # Check for null bytes
    if '\x00' in text:
        raise ValueError("Invalid characters in input")

    # Handle multiline
    if not allow_multiline:
        text = text.replace('\n', ' ').replace('\r', ' ')

    # Prevent argument injection - escape lines starting with --
    lines = text.split('\n')
    sanitized_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('--'):
            # Add spaces to prevent gh CLI from interpreting as argument
            sanitized_lines.append('  ' + line)
        else:
            sanitized_lines.append(line)

    return '\n'.join(sanitized_lines)


def sanitize_paths(text: str) -> str:
    """Replace sensitive paths in text.

    Args:
        text: Text that may contain sensitive paths

    Returns:
        Text with paths sanitized

    Security:
        - Replaces home directory with ~
        - Replaces username
        - Prevents PII leakage
    """
    try:
        home = str(Path.home())
        text = text.replace(home, "~")

        # Try to get username and replace it
        import os
        username = os.getlogin()
        text = text.replace(username, "<user>")
    except Exception:
        # Best effort sanitization
        pass

    return text


def check_rate_limit() -> bool:
    """Check if enough time has passed since last submission.

    Returns:
        True if submission allowed, False if rate limited

    Security:
        - Prevents spam and abuse
        - Limits DoS on GitHub API
    """
    if not RATE_LIMIT_FILE.exists():
        return True

    try:
        last_time = float(RATE_LIMIT_FILE.read_text())
        elapsed = time.time() - last_time

        if elapsed < MIN_SUBMISSION_INTERVAL:
            remaining = int(MIN_SUBMISSION_INTERVAL - elapsed)
            print(f"\n⚠️  Rate limit: Please wait {remaining}s before submitting again")
            print("This prevents spam and ensures the system stays responsive.")
            return False

        return True
    except Exception:
        # If we can't read the file, allow submission
        return True


def record_submission() -> None:
    """Record timestamp of successful submission."""
    try:
        # Ensure parent directory exists
        RATE_LIMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        RATE_LIMIT_FILE.write_text(str(time.time()))
    except Exception:
        # Best effort - don't fail if we can't record
        pass


def show_pii_warning() -> None:
    """Display PII and security warning before submission."""
    print("\n" + "=" * 70)
    print("⚠️  PRIVACY & SECURITY NOTICE")
    print("=" * 70)
    print("\nThis feedback will be submitted as a PUBLIC GitHub issue.")
    print("\nSystem information that will be included:")
    print(f"  • Operating System: {platform.system()} {platform.release()}")
    print(f"  • Python Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("\n⚠️  DO NOT include in your feedback:")
    print("  • Passwords, API keys, or authentication tokens")
    print("  • Private file paths or usernames (we'll sanitize what we can)")
    print("  • Company-specific or confidential information")
    print("  • Personal Identifiable Information (PII)")
    print("\nYour feedback helps improve AIDA for everyone!")
    print("=" * 70)


def return_json_result(success: bool, message: str, **extra) -> int:
    """Return result as JSON (for non-interactive mode)

    Args:
        success: Whether operation succeeded
        message: Human-readable message
        **extra: Additional data to include in response

    Returns:
        0 if success, 1 if failure
    """
    result = {
        "success": success,
        "message": message,
        **extra
    }
    print(json.dumps(result, indent=2))
    return 0 if success else 1


def create_github_issue_json(title: str, body: str, labels: List[str]) -> Tuple[bool, str, Optional[str], Optional[int]]:
    """Create GitHub issue and return structured data

    Args:
        title: Issue title (will be sanitized)
        body: Issue body (will be sanitized)
        labels: List of labels

    Returns:
        Tuple of (success, message, issue_url, issue_number)

    Security: Same security measures as create_github_issue but without interactive prompts
    """
    # Security: Check rate limit
    if not check_rate_limit():
        return (False, "Rate limit: Please wait before submitting another issue", None, None)

    # Check if gh CLI is installed
    if not check_gh_cli():
        return (False, "GitHub CLI (gh) not installed. Install with: brew install gh", None, None)

    # Check gh authentication
    if not check_gh_auth():
        return (False, "GitHub CLI not authenticated. Run: gh auth login", None, None)

    # Security: Sanitize inputs
    try:
        sanitized_title = sanitize_gh_input(title, max_length=200, allow_multiline=False)
        sanitized_body = sanitize_gh_input(body, max_length=MAX_INPUT_LENGTH, allow_multiline=True)
        sanitized_body = sanitize_paths(sanitized_body)
    except ValueError as e:
        return (False, f"Input validation error: {e}", None, None)

    # Create issue
    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", "oakensoul/aida-marketplace",
                "--title", sanitized_title,
                "--body", sanitized_body,
                "--label", ",".join(labels)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            return (False, f"Failed to create issue: {error_msg}", None, None)

        # Get issue URL from output
        issue_url = result.stdout.strip()

        # Validate URL format
        if not issue_url.startswith("https://github.com/"):
            return (False, "Issue may have been created, but received unexpected response format", None, None)

        # Extract issue number from URL
        issue_number = None
        match = re.search(r'/issues/(\d+)', issue_url)
        if match:
            issue_number = int(match.group(1))

        # Security: Record submission for rate limiting
        record_submission()

        return (True, "Issue created successfully", issue_url, issue_number)

    except subprocess.TimeoutExpired:
        return (False, "GitHub CLI timed out. Check your internet connection.", None, None)
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}", None, None)


def submit_feedback_json(json_str: str) -> int:
    """Submit feedback in JSON mode (non-interactive)

    Expected JSON format:
    {
        "message": "Your feedback here",
        "category": "User Experience",  # Optional, defaults to "Other"
        "context": "Additional context"  # Optional
    }
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return return_json_result(False, f"Invalid JSON: {e}")

    # Validate required fields
    if 'message' not in data:
        return return_json_result(False, "Missing required field: message")

    message = data['message']
    category = data.get('category', 'Other')
    context = data.get('context', '')

    # Build issue body
    issue_body = f"""**Feedback Category:** {category}

**Feedback:**
{message}

**Context:**
{context if context else "None provided"}

---
*Created via /aida feedback*"""

    # Submit
    success, msg, issue_url, issue_number = create_github_issue_json(
        title=f"[Feedback] {message[:50]}{'...' if len(message) > 50 else ''}",
        body=issue_body,
        labels=["feedback"]
    )

    return return_json_result(success, msg, issue_url=issue_url, issue_number=issue_number)


def submit_bug_json(json_str: str) -> int:
    """Submit bug report in JSON mode (non-interactive)

    Expected JSON format:
    {
        "description": "Bug description",
        "steps": "Steps to reproduce",
        "expected": "Expected behavior",
        "actual": "Actual behavior",
        "severity": "Major",  # Optional: Critical, Major, Minor
        "include_context": true  # Optional: whether to include system context
    }
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return return_json_result(False, f"Invalid JSON: {e}")

    # Validate required fields
    required = ['description', 'steps', 'expected', 'actual']
    missing = [f for f in required if f not in data]
    if missing:
        return return_json_result(False, f"Missing required fields: {', '.join(missing)}")

    description = data['description']
    steps = data['steps']
    expected = data['expected']
    actual = data['actual']
    severity = data.get('severity', 'Not specified')
    include_context = data.get('include_context', True)  # Default to including context

    # Detect system context
    system_context = detect_system_context()

    # Build environment section
    if include_context:
        env_section = f"""
**Environment:**
- OS: {system_context.get('os', 'unknown')} {system_context.get('os_version', '')}
- Architecture: {system_context.get('architecture', 'unknown')}
- Python: {system_context.get('python_version', 'unknown')}
- Shell: {system_context.get('shell', 'unknown')}
- Git: {system_context.get('git_version', 'not installed')}
- AIDA: {system_context.get('aida_version', 'unknown')}"""
    else:
        env_section = """
**Environment:**
- Context not shared by user"""

    # Build issue body
    issue_body = f"""**Bug Description:**
{description}

**Severity:** {severity}

**Steps to Reproduce:**
{steps}

**Expected Behavior:**
{expected}

**Actual Behavior:**
{actual}
{env_section}

---
*Created via /aida bug*"""

    # Submit
    success, msg, issue_url, issue_number = create_github_issue_json(
        title=f"[Bug] {description[:50]}{'...' if len(description) > 50 else ''}",
        body=issue_body,
        labels=["bug"]
    )

    return return_json_result(success, msg, issue_url=issue_url, issue_number=issue_number)


def submit_feature_request_json(json_str: str) -> int:
    """Submit feature request in JSON mode (non-interactive)

    Expected JSON format:
    {
        "title": "Feature title",
        "use_case": "I need this because...",
        "solution": "It should work like...",  # Optional
        "priority": "Medium",  # Optional: High, Medium, Low
        "alternatives": "I considered..."  # Optional
    }
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return return_json_result(False, f"Invalid JSON: {e}")

    # Validate required fields
    required = ['title', 'use_case']
    missing = [f for f in required if f not in data]
    if missing:
        return return_json_result(False, f"Missing required fields: {', '.join(missing)}")

    title = data['title']
    use_case = data['use_case']
    solution = data.get('solution', '')
    priority = data.get('priority', 'Not specified')
    alternatives = data.get('alternatives', '')

    # Build issue body
    issue_body = f"""**Feature Request**

**Title:** {title}

**Priority:** {priority}

**Use Case:**
{use_case}

**Proposed Solution:**
{solution if solution else "Not specified"}

**Alternatives Considered:**
{alternatives if alternatives else "None"}

---
*Created via /aida feature-request*"""

    # Submit
    success, msg, issue_url, issue_number = create_github_issue_json(
        title=f"[Feature] {title[:50]}{'...' if len(title) > 50 else ''}",
        body=issue_body,
        labels=["enhancement"]
    )

    return return_json_result(success, msg, issue_url=issue_url, issue_number=issue_number)


def main() -> int:
    """
    Main entry point for feedback commands.

    Subcommands:
        feedback - General feedback
        bug - Bug report
        feature-request - Feature request

    Flags:
        --json='{...}' - Non-interactive mode with JSON input (for Claude Code)

    Returns:
        0 on success, non-zero on error
    """
    parser = argparse.ArgumentParser(
        description='AIDA Feedback System',
        add_help=False  # We'll handle help manually
    )
    parser.add_argument('feedback_type', nargs='?', help='Type of feedback')
    parser.add_argument('--json', type=str, help='JSON input for non-interactive mode')
    parser.add_argument('--detect-context', action='store_true', help='Detect and output system context as JSON')

    args = parser.parse_args()

    # Handle --detect-context flag
    if args.detect_context:
        context = detect_system_context()
        print(json.dumps(context, indent=2))
        return 0

    if not args.feedback_type:
        print("❌ Error: feedback type required")
        print("Usage: /aida {feedback|bug|feature-request}")
        return 1

    feedback_type = args.feedback_type

    # Determine if we're in JSON mode (non-interactive)
    json_mode = args.json is not None

    if feedback_type == "feedback":
        if json_mode:
            return submit_feedback_json(args.json)
        else:
            return submit_feedback()
    elif feedback_type == "bug":
        if json_mode:
            return submit_bug_json(args.json)
        else:
            return submit_bug()
    elif feedback_type == "feature-request":
        if json_mode:
            return submit_feature_request_json(args.json)
        else:
            return submit_feature_request()
    else:
        print(f"❌ Error: Unknown feedback type '{feedback_type}'")
        return 1


def submit_feedback() -> int:
    """Submit general feedback"""
    print("\n" + "="*60)
    print("Submit Feedback")
    print("="*60 + "\n")

    print("This will create a public GitHub issue in oakensoul/aida-marketplace.")
    print("Your feedback will be visible to everyone.\n")

    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return 0

    print("\nShare your thoughts about AIDA!\n")

    # Collect feedback
    feedback = input("Your feedback:\n> ").strip()
    if not feedback:
        print("Feedback cancelled.")
        return 0

    # Category
    print("\nCategory:")
    print("1. Setup/Installation")
    print("2. Skills")
    print("3. Commands")
    print("4. Documentation")
    print("5. User Experience")
    print("6. Other")
    category = input("> ").strip()

    categories = {
        "1": "Setup/Installation",
        "2": "Skills",
        "3": "Commands",
        "4": "Documentation",
        "5": "User Experience",
        "6": "Other"
    }
    category_name = categories.get(category, "Other")

    # Additional context
    context = input("\nAdditional context (optional):\n> ").strip()

    # Build issue body
    issue_body = f"""**Feedback Category:** {category_name}

**Feedback:**
{feedback}

**Context:**
{context if context else "None provided"}

---
*Created via /aida feedback*"""

    # Submit
    return create_github_issue(
        title=f"[Feedback] {feedback[:50]}{'...' if len(feedback) > 50 else ''}",
        body=issue_body,
        labels=["feedback"]
    )


def submit_bug() -> int:
    """Submit bug report"""
    print("\n" + "="*60)
    print("Submit Bug Report")
    print("="*60 + "\n")

    print("This will create a public GitHub issue in oakensoul/aida-marketplace.")
    print("The issue will include your system information (OS, Python version).\n")

    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return 0

    print()

    # Description
    description = input("Bug description:\n> ").strip()
    if not description:
        print("Bug report cancelled.")
        return 0

    # Steps to reproduce
    print("\nSteps to reproduce (one per line, empty line to finish):")
    steps = []
    step_num = 1
    while True:
        step = input(f"{step_num}. ").strip()
        if not step:
            break
        steps.append(step)
        step_num += 1

    # Expected behavior
    expected = input("\nExpected behavior:\n> ").strip()

    # Actual behavior
    actual = input("\nActual behavior:\n> ").strip()

    # Environment
    os_name = platform.system()
    os_version = platform.release()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Build issue body
    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)]) if steps else "No steps provided"

    issue_body = f"""**Bug Description:**
{description}

**Steps to Reproduce:**
{steps_text}

**Expected Behavior:**
{expected if expected else "Not specified"}

**Actual Behavior:**
{actual if actual else "Not specified"}

**Environment:**
- OS: {os_name} {os_version}
- Python: {python_version}
- AIDA: {get_aida_version()}

---
*Created via /aida bug*"""

    return create_github_issue(
        title=f"[Bug] {description[:50]}{'...' if len(description) > 50 else ''}",
        body=issue_body,
        labels=["bug", "needs-triage"]
    )


def submit_feature_request() -> int:
    """Submit feature request"""
    print("\n" + "="*60)
    print("Submit Feature Request")
    print("="*60 + "\n")

    print("This will create a public GitHub issue in oakensoul/aida-marketplace.")
    print("Your feature request will be visible to everyone.\n")

    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return 0

    print()

    # Problem/Use case
    problem = input("Problem or use case:\n> ").strip()
    if not problem:
        print("Feature request cancelled.")
        return 0

    # Proposed solution
    solution = input("\nProposed solution:\n> ").strip()

    # Alternatives
    alternatives = input("\nAlternatives considered (optional):\n> ").strip()

    # Priority
    print("\nPriority:")
    print("1. Nice to have")
    print("2. Would improve my workflow")
    print("3. Critical for my use case")
    priority = input("> ").strip()

    priorities = {
        "1": "Nice to have",
        "2": "Would improve my workflow",
        "3": "Critical for my use case"
    }
    priority_name = priorities.get(priority, "Nice to have")

    # Build issue body
    issue_body = f"""**Problem / Use Case:**
{problem}

**Proposed Solution:**
{solution if solution else "Not specified"}

**Alternatives Considered:**
{alternatives if alternatives else "None"}

**Priority:**
{priority_name}

---
*Created via /aida feature-request*"""

    return create_github_issue(
        title=f"[Feature] {problem[:50]}{'...' if len(problem) > 50 else ''}",
        body=issue_body,
        labels=["enhancement", "needs-review"]
    )


def create_github_issue(title: str, body: str, labels: List[str]) -> int:
    """
    Create GitHub issue using gh CLI with security validation.

    Args:
        title: Issue title (will be sanitized)
        body: Issue body (will be sanitized)
        labels: List of labels

    Returns:
        0 on success, 1 on error

    Security:
        - Validates input length and content
        - Sanitizes for argument injection
        - Enforces rate limiting
        - Shows PII warning
        - Sanitizes paths in output
    """
    # Security: Check rate limit
    if not check_rate_limit():
        return 1

    # Check if gh CLI is installed
    if not check_gh_cli():
        print("\n❌ GitHub CLI (gh) not installed")
        print("\nInstall gh CLI:")
        print("  macOS:   brew install gh")
        print("  Linux:   See https://github.com/cli/cli#installation")
        print("\nAfter installing, authenticate with: gh auth login")
        return 1

    # Check gh authentication
    if not check_gh_auth():
        print("\n❌ GitHub CLI not authenticated")
        print("Run: gh auth login")
        return 1

    # Show PII and privacy warning
    show_pii_warning()

    # Confirm submission
    print("\n" + "=" * 70)
    confirm = input("\nDo you want to proceed with this submission? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\nFeedback cancelled.")
        return 0

    # Security: Sanitize inputs
    try:
        sanitized_title = sanitize_gh_input(title, max_length=200, allow_multiline=False)
        sanitized_body = sanitize_gh_input(body, max_length=MAX_INPUT_LENGTH, allow_multiline=True)

        # Sanitize paths in body to prevent PII leakage
        sanitized_body = sanitize_paths(sanitized_body)

    except ValueError as e:
        print(f"\n❌ Input validation error: {e}")
        return 1

    # Create issue
    try:
        print("\nCreating GitHub issue...")

        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", "oakensoul/aida-marketplace",
                "--title", sanitized_title,
                "--body", sanitized_body,
                "--label", ",".join(labels)
            ],
            capture_output=True,
            text=True,
            timeout=10  # Reduced from 30s
        )

        if result.returncode != 0:
            # Sanitize error message
            error_msg = result.stderr.strip()
            # Remove ANSI escape codes
            error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            # Truncate if too long
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            print(f"\n❌ Failed to create issue: {error_msg}")
            return 1

        # Get issue URL from output
        issue_url = result.stdout.strip()

        # Validate URL format
        if not issue_url.startswith("https://github.com/"):
            print("\n⚠️  Issue may have been created, but received unexpected response format")
            return 1

        print(f"\n✓ Issue created: {issue_url}")
        print("\nThank you for your feedback!")

        # Security: Record submission for rate limiting
        record_submission()

        return 0

    except subprocess.TimeoutExpired:
        print("\n❌ Error: Request timed out. Please check your network connection.")
        return 1
    except Exception as e:
        print(f"\n❌ Error creating issue: {e}")
        return 1


def check_gh_cli() -> bool:
    """Check if gh CLI is installed"""
    return shutil.which("gh") is not None


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise

    Security:
        - Prevents failed submissions due to auth issues
        - Provides better error messages
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_aida_version() -> str:
    """Get AIDA version from plugin.json"""
    try:
        plugin_json = Path.home() / ".claude" / "plugins" / "aida-core-plugin" / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            data = json.loads(plugin_json.read_text())
            return data.get("version", "unknown")
    except Exception:
        # If reading or parsing plugin.json fails, return "unknown" version
        pass

    return "unknown"


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelled")
        sys.exit(130)
