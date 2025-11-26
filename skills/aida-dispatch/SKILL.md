---
type: skill
name: aida-dispatch
description: This skill routes /aida commands to appropriate handlers - configuration, diagnostics, feedback, extension management, session persistence (memento operations), and CLAUDE.md management.
version: 0.5.0
tags:
  - core
  - dispatcher
  - commands
---

# AIDA Dispatch

Routes `/aida` commands to appropriate action handlers, managing AIDA's configuration,
diagnostics, feedback systems, and extension management (agents, commands, skills, plugins).

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

### Extension Management Commands

For `agent`, `command`, `skill`, `plugin`, or `hook` commands:

- **Invoke the `claude-code-management` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, validate, version, list, and plugin-specific operations
- For hooks: handles list, add, remove, validate (hooks are settings.json config, not files)

**Process:**

1. Parse the command to extract:
   - Component type: `agent`, `command`, `skill`, `plugin`, or `hook`
   - Operation: `create`, `validate`, `version`, `list`, `add`, `remove`
   - Arguments: name, description, options

2. Invoke `claude-code-management` skill with the parsed context

**Examples:**

```text
/aida agent create "description"     → claude-code-management skill
/aida command validate --all         → claude-code-management skill
/aida skill version my-skill patch   → claude-code-management skill
/aida plugin list                    → claude-code-management skill
/aida hook list                      → claude-code-management skill
/aida hook add "auto-format"         → claude-code-management skill
/aida hook remove my-hook            → claude-code-management skill
```

### Memento Commands

For `memento` commands:

- **Invoke the `memento` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, read, list, update, complete, and remove operations

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `read`, `list`, `update`, `complete`, `remove`
   - Arguments: description, slug, source, filter options

2. Invoke `memento` skill with the parsed context

**Examples:**

```text
/aida memento create "description"   → memento skill
/aida memento create from-pr         → memento skill (source=from-pr)
/aida memento create from-changes    → memento skill (source=from-changes)
/aida memento read my-memento        → memento skill
/aida memento list                   → memento skill
/aida memento list --filter active   → memento skill
/aida memento update my-memento      → memento skill
/aida memento complete my-memento    → memento skill
/aida memento remove my-memento      → memento skill
```

### CLAUDE.md Management Commands

For `claude` commands:

- **Invoke the `claude-md` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, optimize, validate, and list operations

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `optimize`, `validate`, `list`
   - Arguments: scope (project/user/plugin), path, options

2. Invoke `claude-md` skill with the parsed context

**Examples:**

```text
/aida claude create                  → claude-md skill (auto-detect scope)
/aida claude create --scope project  → claude-md skill (scope=project)
/aida claude create --scope user     → claude-md skill (scope=user)
/aida claude optimize                → claude-md skill (audit current)
/aida claude optimize ./CLAUDE.md    → claude-md skill (audit specific)
/aida claude validate                → claude-md skill
/aida claude list                    → claude-md skill
```

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>` tags containing the skill base directory.

**Script Execution:** Construct full paths from base directory:

```text
{base_directory}/scripts/status.py
{base_directory}/scripts/doctor.py
{base_directory}/scripts/upgrade.py
{base_directory}/scripts/detect.py
{base_directory}/scripts/configure.py
{base_directory}/scripts/install.py
{base_directory}/scripts/feedback.py
```

**Reference Loading:** Reference files are located in `references/` subdirectory:

```text
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

### Extension Management
- `/aida agent [create|validate|version|list]` - Manage agents
- `/aida command [create|validate|version|list]` - Manage commands
- `/aida skill [create|validate|version|list]` - Manage skills
- `/aida plugin [create|validate|version|list|add|remove]` - Manage plugins
- `/aida hook [list|add|remove|validate]` - Manage hooks (settings.json)

### Session Persistence
- `/aida memento create "description"` - Save current work context
- `/aida memento create from-pr` - Create from current PR
- `/aida memento create from-changes` - Create from file changes
- `/aida memento read <slug>` - Load memento into context
- `/aida memento list` - List active mementos
- `/aida memento update <slug>` - Update memento sections
- `/aida memento complete <slug>` - Archive completed memento

### CLAUDE.md Management
- `/aida claude create` - Create CLAUDE.md with auto-detection
- `/aida claude create --scope user` - Create user-level CLAUDE.md
- `/aida claude optimize` - Full audit with scoring and findings
- `/aida claude validate` - Validate CLAUDE.md structure
- `/aida claude list` - List all CLAUDE.md files in hierarchy

### Help
- `/aida help` or `/aida` - Show this help message

## Getting Started

If you haven't configured AIDA yet: `/aida config`
To check if AIDA is working: `/aida status`
If you encounter issues: `/aida doctor`
To create an agent: `/aida agent create "description"`
To save work context: `/aida memento create "description"`
To optimize your CLAUDE.md: `/aida claude optimize`
To list hooks: `/aida hook list`
To add a hook: `/aida hook add "auto-format on write"`
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
