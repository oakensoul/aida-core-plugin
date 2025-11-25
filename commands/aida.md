---
type: command
name: aida
description: AIDA command dispatcher - routes to aida-dispatch skill (status, doctor, config, upgrade, feedback, bug, feature-request, help)
version: 0.2.0
tags:
  - core
args: ""
allowed-tools: "*"
argument-hint: "[command]"
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

- **config** - Use the aida dispatcher to guide the user through AIDA configuration setup
- **status** - Use the aida dispatcher to display current AIDA installation and configuration status
- **doctor** - Use the aida dispatcher to run diagnostics and display health check results
- **upgrade** - Use the aida dispatcher to check for and install AIDA updates
- **feedback** - Use the aida dispatcher to collect and submit general feedback
- **bug** - Use the aida dispatcher to collect and submit a bug report
- **feature-request** - Use the aida dispatcher to collect and submit a feature request
- **help** - Use the aida dispatcher to show help message (default if no command given)

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
```
