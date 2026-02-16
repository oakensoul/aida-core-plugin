#!/usr/bin/env python3
"""AIDA Doctor Script

Run comprehensive health check and diagnostics.

Usage:
    python doctor.py

Exit codes:
    0 - All healthy
    1 - Issues found
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python 3.8+ is installed."""
    version = sys.version_info
    print("Checking Python version...")
    if version >= (3, 8):
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro} (>= 3.8 required)")
        return True
    else:
        print(f"✗ Python version: {version.major}.{version.minor}.{version.micro}")
        print("  → Install Python 3.8+ from https://www.python.org/downloads/")
        return False

def check_directory(path, name, should_exist=True):
    """Check if directory exists and is writable."""
    print(f"Checking {name}...")
    if path.exists():
        if path.is_dir():
            # Check if writable
            test_file = path / ".test_write"
            try:
                test_file.touch()
                test_file.unlink()
                print(f"✓ {name}: {path} (exists, writable)")
                return True
            except (OSError, PermissionError):
                print(f"✗ {name}: {path} (exists, not writable)")
                print(f"  → Fix permissions: chmod u+w {path}")
                return False
        else:
            print(f"✗ {name}: {path} (exists but not a directory)")
            return False
    else:
        if should_exist:
            print(f"✗ {name}: {path} (not found)")
            print("  → Run /aida config to create")
            return False
        else:
            print(f"• {name}: Not configured (optional)")
            return True

def check_git():
    """Check if Git is installed."""
    print("Checking Git...")
    try:
        result = subprocess.run(['git', '--version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ {version}")
            return True
        else:
            print("✗ Git: not working")
            return False
    except FileNotFoundError:
        print("✗ Git: not found")
        print("  → Install: https://git-scm.com/downloads")
        return False
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        print(f"✗ Git: error checking ({e})")
        return False

def check_github_cli():
    """Check if GitHub CLI (gh) is installed."""
    print("Checking GitHub CLI...")
    try:
        result = subprocess.run(['gh', '--version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"✓ {version}")

            # Check if authenticated
            auth_result = subprocess.run(['gh', 'auth', 'status'],
                                         capture_output=True, text=True, timeout=5)
            if auth_result.returncode == 0:
                print("✓ GitHub CLI: authenticated")
            else:
                print("⚠ GitHub CLI: not authenticated")
                print("  → Run: gh auth login")
            return True
        else:
            print("✗ GitHub CLI: not working")
            return False
    except FileNotFoundError:
        print("⚠ GitHub CLI: not found (optional for feedback)")
        print("  → Install: brew install gh (macOS)")
        return True  # Not required, just warning
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        print(f"⚠ GitHub CLI: error checking ({e})")
        return True  # Not required

def validate_yaml_file(path, name):
    """Validate a YAML file."""
    if not path.exists():
        return True  # Not an error if doesn't exist yet

    try:
        # Try to import yaml, but if not available, just check if file is readable
        try:
            import yaml
            with open(path, 'r') as f:
                yaml.safe_load(f)
        except ImportError:
            # yaml not installed, just check file is readable
            with open(path, 'r') as f:
                f.read()
        return True
    except (FileNotFoundError, PermissionError):
        # File doesn't exist or can't be read
        return False
    except yaml.YAMLError as e:
        print(f"✗ {name}: Invalid YAML - {e}")
        return False

def validate_config_files():
    """Validate configuration files."""
    print("Checking configuration files...")

    all_valid = True

    # Global config
    global_config = Path.home() / ".claude" / "config" / "settings.yaml"
    if global_config.exists():
        if validate_yaml_file(global_config, "Global config"):
            print("✓ Global config: valid YAML")
        else:
            all_valid = False

    # Project config
    project_config = Path.cwd() / ".claude" / "config" / "project-settings.yaml"
    if project_config.exists():
        if validate_yaml_file(project_config, "Project config"):
            print("✓ Project config: valid YAML")
        else:
            all_valid = False

    if all_valid:
        print("✓ Configuration files: valid")

    return all_valid

def count_and_validate_skills(claude_dir, name):
    """Count and validate skills."""
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return True

    total = 0
    valid = 0

    for item in skills_dir.iterdir():
        if item.is_dir():
            skill_file = item / "SKILL.md"
            if skill_file.exists():
                total += 1
                # Basic validation - file exists and readable
                try:
                    with open(skill_file, 'r') as f:
                        content = f.read()
                        if len(content) > 0:
                            valid += 1
                except (FileNotFoundError, PermissionError, UnicodeDecodeError):
                    # Can't read skill file - skip it
                    pass

    if total > 0:
        print(f"✓ {name} skills: {valid}/{total} valid")
        return valid == total
    return True

def main():
    print("AIDA Health Check")
    print("=" * 40)
    print()

    issues = []
    warnings = []

    # Run all checks
    if not check_python_version():
        issues.append("Python version")

    print()

    claude_dir = Path.home() / ".claude"
    if not check_directory(claude_dir, "AIDA directory", should_exist=False):
        warnings.append("AIDA not installed")

    print()

    if not check_git():
        issues.append("Git")

    print()

    if not check_github_cli():
        # gh is optional, already handles its own messaging
        pass

    print()

    if not validate_config_files():
        issues.append("Configuration files")

    print()

    if claude_dir.exists():
        if not count_and_validate_skills(claude_dir, "Global"):
            issues.append("Global skills")

    project_claude = Path.cwd() / ".claude"
    if project_claude.exists():
        if not count_and_validate_skills(project_claude, "Project"):
            issues.append("Project skills")

    # Summary
    print()
    print("=" * 40)
    print("Summary")
    print("=" * 40)

    if not issues and not warnings:
        print("✓ All checks passed!")
        print()
        print("AIDA is healthy and ready to use. 🚀")
        return 0
    elif issues:
        print(f"✗ {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"  • {issue}")
        print()
        print("Recommendation: Address issues above")
        print("Need help? Run /aida bug to report issues")
        return 1
    else:
        print(f"⚠ {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  • {warning}")
        print()
        print("AIDA is functional but has warnings.")
        print("Run /aida config to complete setup")
        return 0

if __name__ == "__main__":
    sys.exit(main())
