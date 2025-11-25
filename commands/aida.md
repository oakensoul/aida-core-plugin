---
type: command
name: aida
description: AIDA command dispatcher - routes to aida-dispatch skill for configuration, diagnostics, feedback, and extension management (agent, command, skill, plugin)
version: 0.3.0
tags:
  - core
args: ""
allowed-tools: "*"
argument-hint: "[command] [subcommand] [options]"
---

# AIDA Command Dispatcher

Unified command interface for all AIDA functionality.

## Usage

```bash
/aida [action] [arguments]
```

## Process

**IMPORTANT:** This command does NOT implement logic directly. It MUST invoke the `aida-dispatch` skill.

1. **Check command arguments:**
   - If no arguments OR `help` → Invoke `aida-dispatch` skill to display help
   - If any other command → Invoke `aida-dispatch` skill to handle it

2. **Invoke the skill:**

   ```text
   Use Skill tool with command: aida-dispatch
   ```

The `aida-dispatch` skill will handle all routing, script execution, and user interaction.

## Available Commands

When you invoke the `aida-dispatch` skill, it handles these commands:

### Configuration & Diagnostics

- **config** - Guide user through AIDA configuration setup
- **status** - Display current AIDA installation and configuration status
- **doctor** - Run diagnostics and display health check results
- **upgrade** - Check for and install AIDA updates

### Feedback & Support

- **feedback** - Collect and submit general feedback
- **bug** - Collect and submit a bug report
- **feature-request** - Collect and submit a feature request
- **help** - Show help message (default if no command given)

### Extension Management

- **agent** - Manage AIDA agents
  - `create "description"` - Create new agent from description
  - `validate [name|--all]` - Validate agent(s) against schema
  - `version <name> [major|minor|patch]` - Bump agent version
  - `list [--location user|project|all]` - List agents

- **command** - Manage AIDA commands
  - `create "description"` - Create new command from description
  - `validate [name|--all]` - Validate command(s) against schema
  - `version <name> [major|minor|patch]` - Bump command version
  - `list [--location user|project|all]` - List commands

- **skill** - Manage AIDA skills
  - `create "description"` - Create new skill from description
  - `validate [name|--all]` - Validate skill(s) against schema
  - `version <name> [major|minor|patch]` - Bump skill version
  - `list [--location user|project|all]` - List skills

- **plugin** - Manage Claude Code plugins
  - `create "description"` - Create new plugin with directory structure
  - `validate [name|--all]` - Validate plugin(s) against schema
  - `version <name> [major|minor|patch]` - Bump plugin version
  - `list [--location user|project|all]` - List plugins
  - `add <type> "description"` - Add agent/command/skill to plugin
  - `remove <type> <name>` - Remove component from plugin

## Examples

```bash
# Help & Status
/aida              # Show help via aida-dispatch skill
/aida help         # Show help via aida-dispatch skill
/aida status       # Check installation and configuration status

# Configuration
/aida config       # Configure AIDA (dynamic menu based on current state)

# Diagnostics & Maintenance
/aida doctor       # Run health checks and diagnostics
/aida upgrade      # Check for and install AIDA updates

# Feedback & Support
/aida feedback     # Submit general feedback about AIDA
/aida bug          # Report a bug with structured information
/aida feature-request  # Request a new feature

# Extension Management - Agents
/aida agent create "handles database migrations"
/aida agent validate my-agent
/aida agent validate --all
/aida agent version my-agent patch
/aida agent list

# Extension Management - Commands
/aida command create "runs project tests"
/aida command validate --all
/aida command list --location project

# Extension Management - Skills
/aida skill create "manages API integrations"
/aida skill validate --all
/aida skill version my-skill minor

# Extension Management - Plugins
/aida plugin create "my-awesome-plugin"
/aida plugin add agent "handles authentication"
/aida plugin validate my-plugin
/aida plugin list
```
