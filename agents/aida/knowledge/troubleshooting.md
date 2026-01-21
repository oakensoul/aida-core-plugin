---
type: reference
title: AIDA Troubleshooting Guide
description: Common issues, root causes, and fixes for AIDA
---

# Troubleshooting Guide

Common AIDA issues and how to resolve them.

## Diagnostic Categories

### Health Levels

- **HEALTHY** - All components working correctly
- **DEGRADED** - Some features impaired but core functionality works
- **UNHEALTHY** - Core functionality broken

## Common Issues

### Plugin Not Loading

**Symptoms:**

- `/aida` command not recognized
- Skills not appearing in available skills list
- "Plugin not found" errors

**Possible Causes:**

1. Plugin not installed
2. Plugin not enabled in settings
3. Plugin path incorrect in known_marketplaces.json
4. marketplace.json missing or malformed

**Diagnostic Steps:**

1. Check `~/.claude/plugins/installed_plugins.json`
2. Check `~/.claude/settings.json` for `enabledPlugins`
3. Verify plugin directory exists at registered path
4. Validate `.claude-plugin/marketplace.json` exists

**Fixes:**

```bash
# Re-enable dev mode
make dev-mode-enable

# Restart Claude Code
# Then verify
/aida status
```

### Config Not Found

**Symptoms:**

- "AIDA not configured" messages
- Project context not detected
- `/aida status` shows missing config

**Possible Causes:**

1. Never ran `/aida config`
2. Config file deleted or moved
3. Running from wrong directory

**Diagnostic Steps:**

1. Check for `~/.claude/aida.yml` (global)
2. Check for `.claude/aida-project-context.yml` (project)
3. Verify current working directory

**Fixes:**

```bash
# Configure globally
/aida config
# Select "Set up AIDA globally"

# Configure project
/aida config
# Select "Configure this project"
```

### Skill Not Activating

**Symptoms:**

- Skill commands don't work
- "Skill not found" errors
- Skill appears in list but doesn't run

**Possible Causes:**

1. SKILL.md has syntax errors
2. Required scripts missing
3. Frontmatter invalid
4. File permissions

**Diagnostic Steps:**

1. Validate SKILL.md frontmatter
2. Check scripts directory exists
3. Verify Python scripts are executable
4. Check for syntax errors in SKILL.md

**Fixes:**

```bash
# Validate skill
/aida skill validate [skill-name]

# Check file permissions
ls -la skills/[skill-name]/scripts/

# Fix permissions if needed
chmod +x skills/[skill-name]/scripts/*.py
```

### Memento Operations Failing

**Symptoms:**

- Cannot create mementos
- Memento list empty when mementos exist
- Memento read fails

**Possible Causes:**

1. `.claude/mementos/` directory doesn't exist
2. Memento file has invalid frontmatter
3. File permissions

**Diagnostic Steps:**

1. Check `.claude/mementos/` exists
2. Validate memento YAML frontmatter
3. Check file is readable

**Fixes:**

```bash
# Create directory
mkdir -p .claude/mementos

# Validate memento
/aida memento validate [slug]
```

### Script Execution Errors

**Symptoms:**

- "Python not found" errors
- Script permission denied
- Module import errors

**Possible Causes:**

1. Python not installed or not in PATH
2. Missing dependencies
3. Wrong Python version
4. Script not executable

**Diagnostic Steps:**

1. Check Python: `which python3`
2. Check version: `python3 --version`
3. Check dependencies: `pip list`

**Fixes:**

```bash
# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.py

# Use explicit Python path if needed
/usr/bin/python3 scripts/status.py
```

## Diagnostic Commands

### Quick Health Check

```bash
/aida status   # Overview of installation
/aida doctor   # Detailed diagnostics
```

### Manual Checks

```bash
# Check plugin registration
cat ~/.claude/plugins/installed_plugins.json

# Check enabled plugins
cat ~/.claude/settings.json | grep enabledPlugins

# Check global config
cat ~/.claude/aida.yml

# Check project config
cat .claude/aida-project-context.yml
```

## Getting Help

If issues persist after troubleshooting:

1. Run `/aida doctor` and save output
2. Note exact error messages
3. Note steps to reproduce
4. Submit bug report: `/aida bug`
