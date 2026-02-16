---
type: readme
title: "AIDA Core Plugin"
description: "Foundation plugin for AIDA"
---

# AIDA Core Plugin

> Your AI-powered development workflow, supercharged.

## Why AIDA?

Claude Code is powerful, but it forgets everything between sessions. AIDA fixes that.

**Save context, restore later.** Working on a complex feature? Save your session state with
`/aida memento create` and pick up exactly where you left off tomorrow.

**Smart project understanding.** AIDA auto-detects your tech stack, conventions, and patterns.
Claude knows your project without you explaining it every time.

**Build custom extensions.** Create specialized agents, commands, and skills with guided
templates. Run `/aida agent create` and AIDA walks you through the process, generating
properly structured extensions that follow best practices.

## 30-Second Demo

```bash
# Add AIDA marketplace (one-time setup)
/plugin marketplace add oakensoul/aida-marketplace

# Install the core plugin
/plugin install core@aida

# Configure AIDA (auto-detects your environment)
/aida config

# Working on a feature? Save your context before ending your session
/aida memento create "Implementing OAuth flow"

# Tomorrow, restore where you left off
/aida memento restore
```

## Features

- **Session Memory** - Save and restore context across sessions with mementos
- **Smart Configuration** - Auto-detects your environment, tools, and project setup
- **Extension Creation** - Build agents, commands, and skills with guided templates
- **Project Context** - Claude understands your codebase patterns and conventions
- **Health Diagnostics** - Built-in troubleshooting with `/aida doctor`
- **GitHub Integration** - Easy bug reports and feature requests

## Quick Start

### Step 1: Add Marketplace

```bash
/plugin marketplace add oakensoul/aida-marketplace
```

### Step 2: Install

```bash
/plugin install core@aida
```

### Step 3: Configure

```bash
/aida config
```

### Step 4: Verify

```bash
/aida status
```

For detailed walkthrough, see the [Getting Started Guide](docs/GETTING_STARTED.md).

## Commands

| Command                 | Description                          |
| ----------------------- | ------------------------------------ |
| `/aida config`          | Configure AIDA (global or project)   |
| `/aida status`          | Check installation and configuration |
| `/aida doctor`          | Run health diagnostics               |
| `/aida memento`         | Save/restore session context         |
| `/aida agent create`    | Create a custom agent                |
| `/aida command create`  | Create a custom command              |
| `/aida skill create`    | Create a custom skill                |
| `/aida feedback`        | Submit feedback via GitHub           |
| `/aida bug`             | Report a bug                         |
| `/aida feature-request` | Request a feature                    |

## Documentation

### Getting Started

- **[Getting Started](docs/GETTING_STARTED.md)** - Quick onboarding guide
- **[Installation Guide](docs/USER_GUIDE_INSTALL.md)** - Detailed setup walkthrough
- **[Configuration Guide](docs/USER_GUIDE_CONFIGURE.md)** - Project configuration

### How-To Guides

- **[Using Mementos](docs/HOWTO_MEMENTO.md)** - Save and restore session context
- **[Creating Agents](docs/HOWTO_CREATE_AGENT.md)** - Build custom expert personas
- **[Creating Commands](docs/HOWTO_CREATE_COMMAND.md)** - Define workflows and procedures
- **[Creating Skills](docs/HOWTO_CREATE_SKILL.md)** - Add execution capabilities
- **[Using Hooks](docs/HOWTO_HOOKS.md)** - Automate with lifecycle events

### Reference

- **[Examples](docs/EXAMPLES.md)** - Real-world usage scenarios
- **[Extension Framework](docs/EXTENSION_FRAMEWORK.md)** - Architecture and design

## Requirements

- **Claude Code** - Latest version
- **Python 3.8+** - For script execution
- **gh CLI** (optional) - For feedback features

## Architecture

AIDA extends Claude Code with a layered extension system:

```text
agents/          # WHO - Expert personas
commands/        # WHAT - User-invoked actions
skills/          # HOW - Background knowledge
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Roadmap

### Current: v0.5.x - Extension Framework

- Session persistence (mementos)
- Smart configuration with auto-detection
- Agent-based orchestration
- Extension creation (`/aida agent|command|skill|plugin create`)
- Hook management (`/aida hook`)

### Next: v0.6.x - Sharing & Collaboration

- Export/import extensions for sharing
- Extension marketplace integration
- Team collaboration features

## Contributing

We welcome contributions!

```bash
/aida bug              # Report bugs
/aida feature-request  # Request features
/aida feedback         # General feedback
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for contributor guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/oakensoul/aida-core-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/oakensoul/aida-core-plugin/discussions)
- **Diagnostics**: `/aida doctor`

## License

GNU AGPL v3 - See [LICENSE](LICENSE)

---

**Ready to get started?** Run `/aida config` to begin.
