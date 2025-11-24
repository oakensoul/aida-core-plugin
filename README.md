# AIDA Core Plugin

**Foundation plugin for AIDA - Agentic Intelligence Digital Assistant**

> Configuration management and GitHub integration for Claude Code workflows

## Overview

**Current Status (v0.2.0)**: Smart configuration with auto-detection and GitHub workflow integration
**Vision**: A full-featured AI assistant with persistent memory, personal context management, and workflow automation

### What Works Today

AIDA Core currently provides:
- **Smart Configuration**: Interactive setup for global and project-specific settings
- **GitHub Integration**: Built-in feedback, bug reporting, and feature requests
- **Health Checks**: Diagnostics to ensure everything is working correctly
- **Progressive Disclosure**: Guided setup that only asks relevant questions

### What's Coming

Future releases will add:
- **Memory Management**: Persistent context across conversations and projects
- **Personal Context**: Your coding standards, preferences, and work patterns
- **Workflow Automation**: Custom commands, agents, and skills
- **Team Collaboration**: Shareable configurations and team standards

**This is not a standalone tool.** AIDA Core is a Claude Code plugin that extends Claude with configuration and workflow capabilities.

## Features

### Configuration Management
- **Global Setup**: One-time configuration stored in `~/.claude/`
- **Project Setup**: Per-project configuration in `.claude/`
- **Auto-Detection**: Detects 90% of project facts automatically (VCS, files, languages, tools)
- **YAML Configuration**: Single source of truth in `.claude/aida-project-context.yml`
- **Minimal Questions**: Asks only 2-3 preference questions instead of 22!
- **Smart Detection**: Auto-detects what's already configured
- **Progressive Setup**: Only shows relevant options based on current state

### GitHub Integration
- **Bug Reports**: `/aida bug` creates GitHub issues with environment details
- **Feature Requests**: `/aida feature-request` for new ideas
- **General Feedback**: `/aida feedback` for anything else
- **Auto-Context**: Automatically includes system info, versions, and logs

### Diagnostics
- **Health Checks**: `/aida doctor` verifies installation and dependencies
- **Status Reports**: `/aida status` shows current configuration
- **Troubleshooting**: Clear error messages and suggestions

## Requirements

- **Claude Code**: Latest version
- **Python**: 3.8 or higher
- **gh CLI**: GitHub CLI installed and authenticated (for feedback features)
- **Git**: For project detection

### Checking Requirements

```bash
python3 --version    # Should be 3.8+
gh --version         # Should be installed (optional, for feedback)
git --version        # Should be installed
```

Or use the built-in health check:

```bash
/aida doctor
```

## Installation

### Step 1: Install the Plugin

```bash
/plugin install oakensoul/aida-core-plugin
```

### Step 2: Configure AIDA

```bash
/aida config
```

This will:
1. Detect if AIDA is already configured
2. Show you relevant configuration options
3. Guide you through setup (global or project-specific)
4. Create necessary configuration files

**Time to complete**: ~2-3 minutes

See the [Installation Guide](docs/USER_GUIDE_INSTALL.md) for detailed walkthrough.

## Commands Reference

AIDA Core provides all commands under the `/aida` namespace:

### `/aida` or `/aida help`
Show help message and available commands.

```bash
/aida
# Displays available commands and quick start guide
```

### `/aida config`
**Interactive configuration wizard.** Sets up AIDA for global or project use.

```bash
/aida config
```

**What it does:**
- Detects current installation state
- Shows dynamic menu based on what's configured
- Guides you through setup or updates
- Creates configuration files in appropriate locations

**Configuration Options (shown based on state):**
- Set up AIDA globally (if not installed)
- Configure this project (if global exists, project doesn't)
- Update global preferences (if global exists)
- Update project settings (if project configured)
- View current configuration (always available)

**When to use:**
- First time using AIDA
- Starting work on a new project
- Updating your configuration
- Troubleshooting configuration issues

### `/aida status`
Show current AIDA configuration state.

```bash
/aida status
```

**Output includes:**
- Global installation status (`~/.claude/`)
- Project configuration status (`./.claude/`)
- Loaded skills (global and project)
- Plugin version
- Directory locations

### `/aida doctor`
Run health check and diagnostics.

```bash
/aida doctor
```

**Checks:**
- ✓ Python version (3.8+)
- ✓ Directory structure
- ✓ File permissions
- ✓ Required dependencies (gh CLI, git)
- ✓ Configuration file validity
- ✓ Skill syntax validation

**When to use:**
- Installation issues
- Configuration not working
- Before reporting a bug

### `/aida upgrade`
Check for and install updates to aida-core-plugin.

```bash
/aida upgrade
```

**What it does:**
- Checks for available updates
- Shows changelog and version info
- Guides you through upgrade process
- Preserves your configuration

### `/aida feedback`
Submit general feedback via GitHub.

```bash
/aida feedback
```

**Collects:**
- Feedback message
- Category (Setup, Skills, Commands, Documentation, UX, Other)
- Optional additional context

**Creates:**
- GitHub issue in aida-marketplace repo
- Auto-tags with "feedback" label
- Returns issue URL for tracking

### `/aida bug`
Report a bug with detailed information.

```bash
/aida bug
```

**Collects:**
- Bug description
- Steps to reproduce
- Expected vs actual behavior
- Severity level

**Auto-includes:**
- Environment info (OS, Python version, AIDA version)
- Git status (if in git repo)
- Recent error logs (if available)

**Creates:**
- GitHub issue with "bug" label
- Formatted bug report template
- Returns issue URL

### `/aida feature-request`
Request a new feature.

```bash
/aida feature-request
```

**Collects:**
- Feature title
- Use case description
- Proposed solution (optional)
- Priority level
- Alternatives considered (optional)

**Creates:**
- GitHub issue with "enhancement" label
- Formatted feature request template
- Returns issue URL

## Directory Structure

### Global Configuration

```
~/.claude/
├── skills/                          # Global skills
│   └── aida-core/                   # AIDA core skill (auto-installed)
│       ├── SKILL.md
│       └── scripts/                 # Python scripts for commands
└── plugins/
    └── aida-core@aida/              # This plugin
```

### Project Configuration

```
your-project/
└── .claude/
    └── skills/                      # Project-specific skills
        └── (project skills here)
```

## Use Cases

### First-Time Setup

**Scenario**: New AIDA user setting up for the first time.

```bash
# Install plugin
/plugin install oakensoul/aida-core-plugin

# Run configuration
/aida config
# → Selects "Set up AIDA globally"
# → Answers configuration questions
# → AIDA ready to use!

# Check status
/aida status
# → Shows global installation confirmed
```

### Project Configuration

**Scenario**: AIDA user starting work on a new project.

```bash
cd new-project/

# Configure for this project
/aida config
# → Selects "Configure this project"
# → Answers project-specific questions
# → Project configured!

# Verify
/aida status
# → Shows both global and project configuration
```

### Reporting a Bug

**Scenario**: User encounters an issue and wants to report it.

```bash
# Check health first
/aida doctor
# → Identifies the issue

# Report the bug
/aida bug
# → Describes the problem
# → System info auto-included
# → GitHub issue created
```

### Requesting a Feature

**Scenario**: User has an idea for improving AIDA.

```bash
/aida feature-request
# → Describes the feature idea
# → Explains use case
# → GitHub issue created for tracking
```

## Troubleshooting

### Common Issues

#### "Python version not supported"

**Problem**: AIDA requires Python 3.8+

**Solution**:
```bash
python3 --version    # Check version
# If < 3.8, install/upgrade Python
# https://www.python.org/downloads/
```

#### "gh CLI not found"

**Problem**: GitHub CLI not installed (needed for feedback features)

**Solution**:
```bash
# Install gh CLI
# https://cli.github.com/

# Authenticate
gh auth login
```

#### "Permission denied"

**Problem**: Cannot write to `~/.claude/` directory

**Solution**:
```bash
ls -la ~/.claude/         # Check ownership
chmod -R u+w ~/.claude/   # Fix permissions if needed
/aida doctor              # Verify fix
```

#### Configuration Issues

**Problem**: Configuration not working as expected

**Solutions**:
1. Check status: `/aida status`
2. Run diagnostics: `/aida doctor`
3. Reconfigure: `/aida config` → "View current configuration"
4. Report bug: `/aida bug`

### Getting Help

1. **Run diagnostics**: `/aida doctor`
2. **Check status**: `/aida status`
3. **Report bug**: `/aida bug`
4. **Ask for help**: `/aida feedback`

### Debug Mode

Set environment variable for verbose logging:

```bash
export AIDA_DEBUG=1
/aida config
# See detailed debug output
```

## Architecture

AIDA uses a simple, progressive disclosure pattern:

1. **Commands** (`/aida [action]`) - User-facing commands
2. **Agent** (aida) - Orchestrates interactive flows
3. **Skill** (aida-core) - Provides script execution patterns
4. **Scripts** (Python) - Do the actual work

**Flow Example** (`/aida config`):
```
User runs /aida config
  ↓
Command file routes to agent (interactive flow needed)
  ↓
Agent uses skill to detect installation state
  ↓
Agent builds dynamic menu based on state
  ↓
Agent collects user input via AskUserQuestion
  ↓
Agent passes data to Python script
  ↓
Script creates configuration files
  ↓
Agent displays success message
```

**Flow Example** (`/aida status`):
```
User runs /aida status
  ↓
Command file routes directly to script (no agent needed)
  ↓
Script checks directories and files
  ↓
Script outputs status information
  ↓
Claude displays output to user
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Development

### Project Structure

```
aida-core-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── .github/
│   └── workflows/
│       └── ci.yml               # CI pipeline
├── commands/
│   └── aida.md                  # /aida command definition
├── agents/
│   └── aida.md                  # AIDA agent (orchestrator)
├── skills/
│   └── aida-dispatch/
│       ├── SKILL.md             # Core skill knowledge
│       └── scripts/             # Python scripts
│           ├── detect.py
│           ├── install.py
│           ├── configure.py
│           ├── status.py
│           ├── doctor.py
│           ├── upgrade.py
│           └── feedback.py
├── scripts/
│   └── dev-mode.sh              # Development mode helper
├── templates/                   # Configuration templates
├── tests/                       # Test suite
└── docs/
    ├── ARCHITECTURE.md
    ├── USER_GUIDE_INSTALL.md
    └── USER_GUIDE_CONFIGURE.md
```

### Key Concepts

**Commands**: User-facing `/aida [action]` commands defined in markdown
**Agent**: Orchestrates complex flows with user interaction
**Skill**: Teaches Claude how to work with AIDA scripts
**Scripts**: Python code that does the actual work

### Development Mode

To test local changes immediately in Claude Code:

```bash
./scripts/dev-mode.sh
```

This shows instructions for switching between the released and development versions.

### For Contributors

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for:
- Development setup
- Code style guidelines
- Testing procedures
- Contribution workflow

## Roadmap

### Current: v0.1.x - Foundation ✅
- ✅ `/aida config` - Configuration wizard
- ✅ `/aida status` - Status reporting
- ✅ `/aida doctor` - Health checks
- ✅ `/aida feedback/bug/feature-request` - GitHub integration
- ✅ Progressive disclosure pattern
- ✅ Agent-based orchestration
- ✅ Python script foundation

### Next: v0.2.x - Core Assistant Features
- ⏳ Memory management system (persistent context)
- ⏳ Personal preferences and coding standards
- ⏳ Project-specific knowledge management
- ⏳ `/aida upgrade` - Self-update capability
- ⏳ Enhanced project detection

### Future: v0.3.x - Workflow Automation
- 📋 Custom command creation (`/aida command create`)
- 📋 Custom skill creation (`/aida skill create`)
- 📋 Custom agent creation (`/aida agent create`)
- 📋 Export/import for sharing

### Future: v0.4.x+ - Team & Advanced Features
- 📋 Team collaboration capabilities
- 📋 Plugin marketplace integration
- 📋 Advanced diagnostics and analytics
- 📋 Workflow templates

## Troubleshooting

### AIDA won't install

**Problem**: `/aida config` fails when trying to install globally

**Solutions**:
1. Check Python version (must be 3.8+):
   ```bash
   python3 --version
   ```
2. Check permissions on home directory:
   ```bash
   ls -ld ~/
   ```
3. Run diagnostics:
   ```bash
   /aida doctor
   ```
4. Check error messages in the output

---

### Plugin not loading

**Problem**: `/aida` command not found

**Solutions**:
1. Verify plugin is installed in Claude Code
2. Restart Claude Code
3. Check for plugin errors in console
4. Verify `.claude-plugin/plugin.json` is valid JSON

---

### Configuration not persisting

**Problem**: Settings don't save or get lost

**Solutions**:
1. Check directory permissions:
   ```bash
   ls -ld ~/.claude
   chmod u+w ~/.claude
   ```
2. Verify config files exist:
   ```bash
   ls ~/.claude/
   ```
3. Run doctor to check file integrity:
   ```bash
   /aida doctor
   ```

---

### Script execution errors

**Problem**: Commands fail with "Permission denied" or "No such file"

**Solutions**:
1. Check script permissions:
   ```bash
   ls -la ~/.claude/plugins/*/skills/aida-dispatch/scripts/
   ```
2. Verify Python is available:
   ```bash
   which python3
   ```
3. Run diagnostics:
   ```bash
   /aida doctor
   ```

---

### GitHub CLI issues

**Problem**: Feedback/bug commands fail

**Solutions**:
1. Install GitHub CLI:
   ```bash
   # macOS
   brew install gh

   # Linux
   # See https://github.com/cli/cli#installation
   ```
2. Authenticate:
   ```bash
   gh auth login
   ```
3. Verify:
   ```bash
   gh auth status
   ```

---

### Getting Help

If you're still having issues:

1. **Run diagnostics**:
   ```bash
   /aida doctor
   ```

2. **Check status**:
   ```bash
   /aida status
   ```

3. **Report a bug**:
   ```bash
   /aida bug
   ```
   Include output from `/aida doctor` and `/aida status`

## Contributing

We welcome contributions! To contribute:

1. Report bugs: `/aida bug`
2. Request features: `/aida feature-request`
3. Submit feedback: `/aida feedback`
4. Open PRs: See [DEVELOPMENT.md](docs/DEVELOPMENT.md)

## Support

- **Bug Reports**: `/aida bug` or [GitHub Issues](https://github.com/oakensoul/aida-core-plugin/issues)
- **Feature Requests**: `/aida feature-request`
- **Discussions**: [GitHub Discussions](https://github.com/oakensoul/aida-core-plugin/discussions)
- **Documentation**: [docs/](docs/)

## License

GNU AGPL v3 - See [LICENSE](LICENSE)

## Credits

Created by [@oakensoul](https://github.com/oakensoul)

Part of the [AIDA Project](https://github.com/oakensoul/aida-marketplace)

## Links

- **Marketplace**: [aida-marketplace](https://github.com/oakensoul/aida-marketplace)
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/oakensoul/aida-core-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/oakensoul/aida-core-plugin/discussions)

---

**Ready to get started?** → Run `/aida config` to begin!
