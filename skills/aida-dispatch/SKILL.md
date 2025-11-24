---
name: aida-dispatch
description: This skill should be used when the user invokes /aida commands (status, doctor, config, upgrade, feedback, bug, feature-request, help) to route them to appropriate action handlers with context awareness and progressive workflow execution.
---

# AIDA Dispatch

Routes `/aida` commands to appropriate action handlers, managing AIDA's configuration, diagnostics, and feedback systems.

## Activation

This skill activates when:
- User invokes `/aida` command with any action
- AIDA functionality is needed (configuration, status checks, diagnostics)
- Command routing and execution orchestration is required

## Command Routing

When this skill activates, check the `<command-args>` tag to determine which action to route:

### Diagnostic Commands
For `status`, `doctor`, or `upgrade` commands:
- Read `references/diagnostics.md` for execution workflow
- These are non-interactive commands that execute Python scripts directly

### Configuration Commands
For `config` command:
- Read `references/config.md` for YAML-based configuration workflow
- This is an interactive command with:
  - Dynamic menu generation based on installation state
  - Auto-detection of project facts (saved to YAML)
  - Minimal questions (0-3) for unknown preferences only
  - Automatic skill generation from YAML config

### Feedback Commands
For `feedback`, `bug`, or `feature-request` commands:
- Read `references/feedback.md` for feedback collection workflow
- These are interactive commands that collect and submit user input

### Help Command
For `help` or no arguments:
- Display the help text inline (see Help Text section below)
- No additional files need to be loaded

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>` tags containing the skill base directory.

**Script Execution:** Construct full paths from base directory:
```
{base_directory}/scripts/status.py
{base_directory}/scripts/doctor.py
{base_directory}/scripts/upgrade.py
{base_directory}/scripts/detect.py
{base_directory}/scripts/configure.py
{base_directory}/scripts/install.py
{base_directory}/scripts/feedback.py
```

**Reference Loading:** Reference files are located in `references/` subdirectory:
```
{base_directory}/references/diagnostics.md
{base_directory}/references/config.md
{base_directory}/references/feedback.md
```

## Help Text

When displaying help (for `help` command or no arguments), show:

```markdown
## Available AIDA Commands

### Configuration & Setup
- `/aida config` - Configure AIDA settings (global or project-level)
- `/aida status` - Check AIDA installation and configuration status
- `/aida doctor` - Run diagnostics to troubleshoot AIDA issues

### Maintenance
- `/aida upgrade` - Check for and install AIDA updates

### Feedback & Support
- `/aida feedback` - Submit feedback about AIDA
- `/aida bug` - Report a bug in AIDA
- `/aida feature-request` - Request a new AIDA feature

### Help
- `/aida help` or `/aida` - Show this help message

## Getting Started

If you haven't configured AIDA yet: `/aida config`
To check if AIDA is working: `/aida status`
If you encounter issues: `/aida doctor`
```

## Resources

### scripts/
Executable Python scripts for AIDA operations:
- **status.py** - Display current installation and configuration state
- **doctor.py** - Run health checks and diagnostics
- **upgrade.py** - Check for and install updates
- **detect.py** - Detect current installation state (used by config)
- **configure.py** - Interactive project configuration
- **install.py** - Global installation setup
- **feedback.py** - Submit feedback, bugs, and feature requests
- **utils/** - Shared utilities (paths, files, version, questionnaire, etc.)

### references/
Detailed workflow guides loaded as needed:
- **diagnostics.md** - Workflow for status/doctor/upgrade commands
- **config.md** - YAML-based configuration flow with auto-detection
- **feedback.md** - Feedback collection and submission workflow
- **config-driven-approach.md** - Architecture documentation for config system
- **project-facts.md** - Comprehensive taxonomy of detectable project facts
