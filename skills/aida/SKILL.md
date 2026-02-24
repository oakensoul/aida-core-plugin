---
type: skill
name: aida
description: This skill routes /aida commands to appropriate handlers - configuration,
  diagnostics, feedback, extension management (agent-manager, skill-manager,
  plugin-manager, hook-manager, claude-md-manager), and session persistence
  (memento).
version: 0.8.0
tags:
  - core
user-invocable: true
allowed-tools: "*"
argument-hint: "[command] [subcommand] [options]"
---

# AIDA Dispatch

Routes `/aida` commands to appropriate action handlers, managing AIDA's configuration,
diagnostics, feedback systems, and extension management (agents, skills, plugins).

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

### Permissions Commands

For `config permissions` or `permissions` commands:

- **Invoke the `permissions` skill** to handle these operations
- The skill handles interactive permission setup and audit mode

**Process:**

1. Parse the command to detect:
   - `--audit` flag for audit mode
   - No flags for interactive setup

2. Invoke `permissions` skill with the parsed context

**Examples:**

```text
/aida config permissions           → permissions skill
/aida config permissions --audit   → permissions skill (audit)
```

### Feedback Commands

For `feedback`, `bug`, or `feature-request` commands:

- Read `references/feedback.md` for feedback collection workflow
- These are interactive commands that collect and submit user input

### Help Command

For `help` or no arguments:

- Display the help text inline (see Help Text section below)
- No additional files need to be loaded

### Agent Management Commands

For `agent` commands:

- **Invoke the `agent-manager` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, validate, version, and list operations

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `validate`, `version`, `list`
   - Arguments: name, description, options

2. Invoke `agent-manager` skill with the parsed context

**Examples:**

```text
/aida agent create "description"     → agent-manager skill
/aida agent validate --all           → agent-manager skill
/aida agent version my-agent patch   → agent-manager skill
/aida agent list                     → agent-manager skill
```

### Skill Management Commands

For `skill` commands:

- **Invoke the `skill-manager` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, validate, version, and list operations

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `validate`, `version`, `list`
   - Arguments: name, description, options

2. Invoke `skill-manager` skill with the parsed context

**Examples:**

```text
/aida skill create "description"     → skill-manager skill
/aida skill validate --all           → skill-manager skill
/aida skill version my-skill patch   → skill-manager skill
/aida skill list                     → skill-manager skill
```

### Plugin Management Commands

For `plugin` commands (including `plugin scaffold`):

- **Invoke the `plugin-manager` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, validate, version, list, and scaffold operations
- Scaffold creates a NEW plugin project (not an extension inside an existing
  project)

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `validate`, `version`, `list`, `scaffold`
   - Arguments: name, description, options

2. Invoke `plugin-manager` skill with the parsed context

**Examples:**

```text
/aida plugin create "description"        → plugin-manager skill
/aida plugin validate --all              → plugin-manager skill
/aida plugin list                        → plugin-manager skill
/aida plugin scaffold "my-new-plugin"    → plugin-manager skill
/aida plugin scaffold                    → plugin-manager skill (will ask)
```

### Hook Management Commands

For `hook` commands:

- **Invoke the `hook-manager` skill** to handle these operations
- Pass the full command arguments to the skill
- Hooks are settings.json config, not files
- The skill handles list, add, remove, and validate operations

**Process:**

1. Parse the command to extract:
   - Operation: `list`, `add`, `remove`, `validate`
   - Arguments: event, matcher, command, scope

2. Invoke `hook-manager` skill with the parsed context

**Examples:**

```text
/aida hook list                      → hook-manager skill
/aida hook add "auto-format"         → hook-manager skill
/aida hook remove my-hook            → hook-manager skill
/aida hook validate                  → hook-manager skill
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
/aida memento list --all             → memento skill (all_projects=true)
/aida memento list --project foo     → memento skill (project_filter=foo)
/aida memento update my-memento      → memento skill
/aida memento complete my-memento    → memento skill
/aida memento remove my-memento      → memento skill
```

### CLAUDE.md Management Commands

For `claude` commands:

- **Invoke the `claude-md-manager` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles create, optimize, validate, and list operations

**Process:**

1. Parse the command to extract:
   - Operation: `create`, `optimize`, `validate`, `list`
   - Arguments: scope (project/user/plugin), path, options

2. Invoke `claude-md-manager` skill with the parsed context

**Examples:**

```text
/aida claude create                  → claude-md-manager skill (auto-detect scope)
/aida claude create --scope project  → claude-md-manager skill (scope=project)
/aida claude create --scope user     → claude-md-manager skill (scope=user)
/aida claude optimize                → claude-md-manager skill (audit current)
/aida claude optimize ./CLAUDE.md    → claude-md-manager skill (audit specific)
/aida claude validate                → claude-md-manager skill
/aida claude list                    → claude-md-manager skill
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
- `/aida config permissions` - Configure Claude Code permissions from plugin recommendations
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
- `/aida skill [create|validate|version|list]` - Manage skills
- `/aida plugin [scaffold|create|validate|version|list]` - Manage plugins
- `/aida hook [list|add|remove|validate]` - Manage hooks (settings.json)

### Session Persistence
- `/aida memento create "description"` - Save current work context
- `/aida memento create from-pr` - Create from current PR
- `/aida memento create from-changes` - Create from file changes
- `/aida memento read <slug>` - Load memento into context
- `/aida memento list` - List active mementos
- `/aida memento list --all` - List mementos from all projects
- `/aida memento list --project <name>` - List mementos for specific project
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
