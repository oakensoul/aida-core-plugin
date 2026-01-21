---
type: documentation
title: "Command Examples"
description: "Real-world examples of using AIDA commands in different scenarios"
audience: users
---

# AIDA Command Examples

Real-world examples of using AIDA commands in different scenarios.

## Scenario 1: New Developer Setup

### Sarah is a new developer setting up AIDA for the first time

```bash
# Day 1: Check if AIDA is working
/aida doctor
# Output: Shows AIDA not installed (warning, not error)
#         Python and Git checks pass
#         Suggests running /aida config

# Set up AIDA globally
/aida config
# Menu shows: "Set up AIDA globally"
# Select this option
# Answers 2-3 preference questions
# AIDA creates ~/.claude/ with configuration

# Verify installation
/aida status
# Output: ✓ Global Installation: /Users/sarah/.claude
#         ✓ Global Skills: 1 loaded (user-context)
#         Plugin Version: 0.5.0

# Run health check
/aida doctor
# Output: ✓ All checks passed!
#         AIDA is healthy and ready to use. 🚀
```

**Result**: Sarah has AIDA installed and ready to use globally.

---

## Scenario 2: Starting a New Project

### Alex is starting a new Python CLI project with AIDA

```bash
# Create project directory
mkdir my-cli-tool
cd my-cli-tool
git init

# Configure AIDA for this project
/aida config
# Menu shows: "Configure this project" (since global is installed)
# Select this option
# AIDA auto-detects:
#   - Git repository ✓
#   - No README, LICENSE, tests (offers to create them)
#   - Python project (based on directory structure)
# Asks 2 questions:
#   - Branching model? → "GitHub Flow"
#   - Project conventions? → "Standard Python package"
# Creates:
#   - .claude/aida-project-context.yml (all detected facts)
#   - .claude/skills/project-context/SKILL.md (auto-generated)

# Verify project setup
/aida status
# Output: ✓ Global Installation: ~/.claude
#         ✓ Project Configuration: /Users/alex/my-cli-tool/.claude
#         ✓ Project: my-cli-tool
#         ✓ Project Skills: 1 loaded (project-context)
```

**Result**: Alex has project-specific AIDA configuration with auto-detected facts.

---

## Scenario 3: Updating Preferences

### Jordan changed jobs and needs to update settings

```bash
# Check current settings
/aida config
# Select "View current configuration"
# Output: Shows current global preferences

# Update global preferences for new work environment
/aida config
# Select "Update global preferences"
# AIDA shows current values in menu
# Jordan changes:
#   - Coding standards: PEP 8 → Company Style Guide
#   - Work hours: Flexible → 9-5 EST
# Settings updated

# Verify changes persisted
/aida status
# Output: Shows updated preferences
```

**Result**: Jordan's preferences reflect new work environment.

---

## Scenario 4: Working with Multiple Projects

### Casey works on several projects with different configurations

```bash
# Project 1: Django web app
cd ~/work/django-project
/aida config
# Select "Configure this project"
# AIDA detects: Django, PostgreSQL, Docker
# Asks about: Branching model, conventions
# Creates project-specific .claude/

/aida status
# Output: Shows Django project configuration

# Project 2: React frontend
cd ~/work/react-app
/aida config
# Select "Configure this project"
# AIDA detects: Node.js, npm, Jest, GitHub Actions
# Asks about: Branching model, conventions
# Creates separate .claude/ for this project

/aida status
# Output: Shows React project configuration

# Switch back to Django project
cd ~/work/django-project
/aida status
# Output: Shows Django configuration (not React)
```

**Result**: Each project has its own configuration, AIDA switches automatically.

---

## Scenario 5: Troubleshooting Issues

### Morgan is having issues with AIDA

```bash
# Something seems wrong
/aida doctor
# Output: ✓ Python version: 3.9.6
#         ✓ AIDA directory: ~/.claude (exists, writable)
#         ✓ Git: version 2.39.5
#         ✗ GitHub CLI: not authenticated
#           → Fix: Run 'gh auth login'
#         ✓ Configuration files: valid
#
# Summary: 1 issue found
# Recommendation: Run 'gh auth login' to enable feedback features

# Follow the suggestion
gh auth login
# Completes GitHub authentication

# Verify fix
/aida doctor
# Output: ✓ All checks passed!
#         AIDA is healthy and ready to use. 🚀

# Test feedback feature now works
/aida feedback
# Opens feedback form successfully
```

**Result**: Morgan diagnosed and fixed the authentication issue.

---

## Scenario 6: Viewing Project Configuration

### Taylor wants to see what AIDA knows about their project

```bash
cd ~/my-monorepo

# View configuration without changing anything
/aida config
# Select "View current configuration"
# Output:
# Global Configuration: ~/.claude/aida.yml
#   Version: 0.5.0
#   Skills: user-context
#
# Project Configuration: .claude/aida-project-context.yml
#   Project: my-monorepo
#   VCS: git (uses worktrees)
#   Branching: GitHub Flow
#   Languages: Python
#   Files: README ✓, LICENSE ✓, .gitignore ✓
#   Issue Tracking: GitHub Issues
#   Conventions: Python monorepo with packages
```

**Result**: Taylor sees all detected facts and preferences at a glance.

---

## Scenario 7: Reporting a Bug

### Sam found a bug in AIDA

```bash
# Report the bug with automatic environment info
/aida bug
# AIDA automatically collects:
#   - Python version: 3.11.2
#   - AIDA version: 0.5.0
#   - OS: macOS 14.1
#   - Active skills: user-context, project-context
#   - Git status (if in repo)

# Sam fills in:
#   - Title: "Config fails on projects without git"
#   - Description: Steps to reproduce
#   - Expected behavior
#   - Actual behavior
#   - Severity: Major

# AIDA creates GitHub issue
# Output: ✓ Bug report submitted!
#         Issue: https://github.com/oakensoul/aida-core-plugin/issues/123
```

**Result**: Bug reported with all necessary context included automatically.

---

## Scenario 8: Checking for Updates

### Riley wants to know if there's a new version

```bash
# Check for updates
/aida upgrade
# Output: AIDA Upgrade Check
#         ====================================
#         Current version: 0.5.0
#         Latest version: 0.5.1
#
#         ✓ New version available!
#
#         Changes in 0.5.1:
#         • Enhanced language detection
#         • Bug fixes for Windows paths
#         • Improved error messages
#
#         To upgrade:
#         1. Backup your config (optional): cp -r ~/.claude ~/.claude.backup
#         2. Run: /plugin marketplace update
#         3. Reinstall: /plugin install aida-core
#
#         Note: Your configuration will be preserved
```

**Result**: Riley knows a new version is available and how to upgrade.

---

## Scenario 9: Fresh Project with Auto-Detection

### Jordan creates a new project and AIDA detects everything automatically

```bash
# Create a typical Python project structure
mkdir awesome-tool
cd awesome-tool
git init
echo "# Awesome Tool" > README.md
touch LICENSE
echo "*.pyc" > .gitignore
git remote add origin git@github.com:jordan/awesome-tool.git

# Configure AIDA
/aida config
# Select "Configure this project"
# AIDA auto-detects:
#   ✓ Git repository with GitHub remote
#   ✓ Has README (104 chars - Minimal)
#   ✓ Has LICENSE
#   ✓ Has .gitignore
#   ✓ No tests, CI/CD, Docker yet
#   ✓ Solo project (1 contributor)
#   ✓ Issue tracking: GitHub Issues (inferred from remote)
#
# AIDA asks only 2 questions:
#   1. Branching model? → "GitHub Flow"
#   2. Project conventions? → "Standard Python CLI tool"
#
# Creates:
#   - .claude/aida-project-context.yml (all facts)
#   - .claude/skills/project-context/SKILL.md (auto-generated)

# Check what AIDA knows
cat .claude/aida-project-context.yml
# Shows all detected facts and preferences in YAML
```

**Result**: Jordan answered 2 questions, AIDA detected 15+ facts automatically!

---

## Scenario 10: Updating Project Configuration

### Casey's project evolved and needs config update

```bash
# Project now has tests and CI/CD
cd ~/my-project
ls -d tests .github/workflows
# tests/ and .github/workflows/ now exist

# Update project configuration
/aida config
# Select "Update project settings"
# AIDA re-detects:
#   ✓ Now has tests directory
#   ✓ Now has GitHub Actions CI/CD
#   ✓ Still uses GitHub Flow
# Asks about:
#   - Testing approach updated? → "pytest with coverage"
# Updates YAML and regenerates skill

# Verify update
/aida status
# Output: Shows updated project facts including tests
```

**Result**: AIDA's knowledge of the project stays current as it evolves.

---

## Quick Reference

### First-Time User Journey

```bash
/aida config              # Set up globally (2-3 questions)
/aida status              # Verify installation
/aida doctor              # Check health
cd ~/my-project
/aida config              # Configure project (2-3 questions)
/aida status              # See both global + project
```

### Daily Usage

```bash
/aida status              # Quick status check
/aida doctor              # If something seems wrong
/aida config              # Update settings as needed
/aida bug                 # Report issues
/aida feature-request     # Suggest improvements
```

### Maintenance

```bash
/aida upgrade             # Check for updates
/aida doctor              # Verify health after upgrade
/aida config              # Update settings if needed
```

---

## Tips

1. **Run `/aida doctor` first** if you encounter any issues
2. **Use `/aida status`** to quickly see your current setup
3. **Config is idempotent** - safe to run `/aida config` multiple times
4. **YAML is editable** - you can manually edit `.claude/aida-project-context.yml`
5. **Each project is independent** - config in one project doesn't affect others

---

For more details, see:

- [README.md](../README.md) - Overview and quick start
- [USER_GUIDE_INSTALL.md](USER_GUIDE_INSTALL.md) - Installation guide
- [USER_GUIDE_CONFIGURE.md](USER_GUIDE_CONFIGURE.md) - Configuration guide
