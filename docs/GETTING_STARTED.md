---
type: guide
title: "Getting Started"
description: "Quick onboarding guide for new AIDA users"
audience: users
---

# Getting Started with AIDA

Go from zero to productive in under 10 minutes.

## Prerequisites

Before installing AIDA, ensure you have:

- **Claude Code CLI** - Latest version installed
- **Python 3.8+** - Check with `python3 --version`
- **GitHub CLI** (optional) - For feedback features, install with `brew install gh`

## Installation

### Step 1: Add AIDA Marketplace

```bash
/plugin marketplace add oakensoul/aida-marketplace
```

This is a one-time setup that adds the AIDA plugin registry to your Claude Code.

### Step 2: Install Core Plugin

```bash
/plugin install core@aida
```

### Step 3: Run Initial Setup

```bash
/aida config
```

Select "Set up AIDA globally" from the menu. AIDA will:

- Auto-detect your environment (OS, tools, git config)
- Create your user context skill
- Configure Claude Code settings

That's it! AIDA is now ready to use.

## Your First Commands

### Check Status

See what AIDA knows about your setup:

```bash
/aida status
```

### Configure a Project

Navigate to a project and set up project-specific context:

```bash
cd your-project/
/aida config
```

Select "Configure this project" to create project-specific skills.

### Run Diagnostics

If something seems wrong:

```bash
/aida doctor
```

### Save Your Work Context

Before ending a session, save context for later:

```bash
/aida memento create "Working on auth feature"
```

Resume later with:

```bash
/aida memento restore
```

## Key Concepts

AIDA extends Claude Code with specialized capabilities organized into three types:

### Agents

**WHO** - Specialized expert personas that Claude can become:

- `aida` - AIDA assistant for configuration and management
- `claude-code-expert` - Expert on Claude Code extension patterns

### Commands

**WHAT** - User-invoked actions via `/aida [action]`:

- `/aida config` - Configure AIDA settings
- `/aida status` - Check installation status
- `/aida doctor` - Run diagnostics
- `/aida memento` - Manage session persistence

### Skills

**HOW** - Background knowledge that Claude automatically uses:

- `user-context` - Your environment and preferences
- `project-context` - Project-specific patterns and conventions

## Next Steps

### Learn Mementos

Save and restore context across sessions:

- [How to Use Mementos](HOWTO_MEMENTO.md)

### Create Custom Extensions

Build your own agents, commands, and skills:

- [Creating Agents](HOWTO_CREATE_AGENT.md) - Expert personas
- [Creating Commands](HOWTO_CREATE_COMMAND.md) - Workflows and procedures
- [Creating Skills](HOWTO_CREATE_SKILL.md) - Execution capabilities
- [Using Hooks](HOWTO_HOOKS.md) - Lifecycle automation

### Explore Examples

See real-world usage scenarios in [EXAMPLES.md](EXAMPLES.md).

### Contribute

- Report bugs: `/aida bug`
- Request features: `/aida feature-request`
- Submit feedback: `/aida feedback`

## Getting Help

### Quick Diagnostics

```bash
/aida doctor      # Check for issues
/aida status      # View current configuration
```

### Command Reference

```bash
/aida help        # Show available commands
```

### Documentation

- [Full Installation Guide](USER_GUIDE_INSTALL.md)
- [Configuration Guide](USER_GUIDE_CONFIGURE.md)
- [Extension Framework](EXTENSION_FRAMEWORK.md) - Architecture reference

### Community

- [GitHub Issues](https://github.com/oakensoul/aida-core-plugin/issues)
- [GitHub Discussions](https://github.com/oakensoul/aida-core-plugin/discussions)

---

**Ready to dive deeper?** Check out the [Configuration Guide](USER_GUIDE_CONFIGURE.md) for
project-specific setup.
