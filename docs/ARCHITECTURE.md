---
type: documentation
title: "Architecture"
description: "System architecture and design decisions for AIDA"
audience: developers
---

# AIDA Core Plugin - Architecture

## System architecture and design decisions for AIDA

This document provides a comprehensive overview of AIDA's architecture, components, data flows,
and design decisions.

## Table of Contents

- [Overview](#overview)
- [Architecture Principles](#architecture-principles)
- [System Architecture](#system-architecture)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Directory Structure](#directory-structure)
- [Extension Points](#extension-points)
- [Design Decisions](#design-decisions)
- [Security Considerations](#security-considerations)
- [Performance Considerations](#performance-considerations)
- [Further Reading](#further-reading)

## Overview

AIDA (Agentic Intelligence Digital Assistant) is a Claude Code plugin that provides skills-first
architecture for personal and project-specific context management.

### Key Characteristics

- **Plugin-Based**: Extends Claude Code via official plugin system
- **Skills-First**: Context and knowledge over automation
- **Python Utilities**: Foundation module for all scripts
- **Template-Driven**: Jinja2 templates for skill generation
- **Questionnaire-Based**: Interactive setup and configuration
- **Privacy-First**: All data stored locally

### Design Goals

1. **< 5 Minute Setup**: Fast onboarding with intelligent defaults
2. **Lovable UX**: Delightful interactions, not just functional
3. **Extensibility**: Users can create their own skills and agents
4. **Cross-Platform**: Works on macOS, Linux, and WSL
5. **Maintainability**: Clean separation of concerns

## Architecture Principles

### 1. Skills Over Automation

**Philosophy**: AIDA focuses on context and knowledge rather than task automation.

**Rationale**:

- Users need Claude to understand their preferences
- Automation can be added later as workflows mature
- Skills persist; automation scripts become outdated

### 2. Questionnaire-Driven Configuration

**Philosophy**: Interactive questionnaires with smart defaults

**Rationale**:

- Reduces decision fatigue
- Provides guidance for new users
- Validates input and catches errors
- Creates consistent skill structures

### 3. Template-Based Generation

**Philosophy**: Use Jinja2 templates for all generated content

**Rationale**:

- Separation of logic and content
- Easy to customize and extend
- Consistent formatting
- Version-controllable templates

### 4. Local-First Storage

**Philosophy**: All data stored in `~/.claude/` and `.claude/`

**Rationale**:

- User privacy and control
- No network dependencies (except feedback)
- Works offline
- Simple backup/migration

### 5. Progressive Enhancement

**Philosophy**: Start minimal, add features as needed

**Rationale**:

- Lower barrier to entry
- Users only pay for what they use
- Easier to understand and debug
- Natural upgrade path

## System Architecture

See [C4 Diagrams](architecture/c4/) for visual representations.

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    Claude Code                          │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │           AIDA Core Plugin                        │ │
│  │                                                   │ │
│  │  ┌──────────────────────────┐                     │ │
│  │  │     Skills               │                     │ │
│  │  │  (user-invocable + auto) │                     │ │
│  │  └────────────┬─────────────┘                     │ │
│  │                  │                                │ │
│  │         ┌────────▼────────┐                       │ │
│  │         │  Python Scripts  │                       │ │
│  │         │                  │                       │ │
│  │         │ • install.py     │                       │ │
│  │         │ • configure.py   │                       │ │
│  │         │ • feedback.py    │                       │ │
│  │         │ • utils/         │                       │ │
│  │         └────────┬─────────┘                       │ │
│  │                  │                                 │ │
│  │         ┌────────▼──────────┐                      │ │
│  │         │  Templates         │                      │ │
│  │         │  (Jinja2)          │                      │ │
│  │         └────────┬───────────┘                      │ │
│  │                  │                                  │ │
│  └──────────────────┼──────────────────────────────────┘ │
│                     │                                    │
└─────────────────────┼────────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   File System           │
         │                         │
         │  ~/.claude/             │
         │  ├── skills/            │
         │  └── settings.json      │
         │                         │
         │  .claude/               │
         │  ├── skills/            │
         │  └── settings.json      │
         └─────────────────────────┘
```

### Component Layers

#### Layer 1: Claude Code Interface

- **Skills**: User-invocable and auto-loaded (SKILL.md files)
- **Agents**: Persona definitions

#### Layer 2: Python Scripts

- **install.py**: Global setup wizard
- **configure.py**: Project setup wizard
- **feedback.py**: GitHub issue creation
- **utils/**: Shared utilities

#### Layer 3: Utilities Module

- **version.py**: Python version checking
- **paths.py**: Path resolution and directories
- **files.py**: File operations (JSON, text)
- **questionnaire.py**: Interactive questionnaires
- **inference.py**: Smart project detection
- **template_renderer.py**: Jinja2 rendering
- **errors.py**: Custom error classes

#### Layer 4: Templates

- **blueprints/**: Skill templates
- **questionnaires/**: Question definitions

#### Layer 5: File System

- **~/.claude/**: Global configuration
- **.claude/**: Project-specific configuration

## Component Architecture

See [C4 Component Diagrams](architecture/c4/component-diagram.md) for details.

### Python Utilities Module

The foundation for all AIDA scripts:

```text
# High-level structure
utils/
├── __init__.py          # Public API
├── version.py           # Python version checking
├── paths.py             # Path resolution
├── files.py             # File operations
├── questionnaire.py     # Interactive questions
├── inference.py         # Project detection
├── template_renderer.py # Jinja2 rendering
└── errors.py            # Error classes
```

**Key Functions**:

- `check_python_version()`: Validates Python 3.8+
- `get_claude_dir()`: Returns `~/.claude/` path
- `run_questionnaire(template)`: Interactive Q&A
- `render_skill_directory(template, output, vars)`: Generate skills
- `infer_preferences(project_path)`: Detect project details

### Installation Script

**File**: `scripts/install.py`

**Responsibilities**:

1. Check Python version
2. Detect existing installation
3. Run installation questionnaire
4. Create personal skills
5. Update settings.json

**Flow**:

```text
main()
├── check_python_version()
├── is_already_installed()
│   └── prompt_reinstall()
├── print_welcome()
├── run_questionnaire("install.yml")
├── create_directory_structure()
├── render_skills()
│   └── render_user_context()
├── update_settings_json()
└── print_success()
```

### Questionnaire System

**File**: `utils/questionnaire.py`

**Responsibilities**:

- Load YAML questionnaire definitions
- Display questions with formatting
- Validate answers
- Handle defaults
- Support multiple question types

**Question Types**:

- `text`: Free-form text input
- `multiline`: Multi-line text (Ctrl+D to finish)
- `choice`: Single selection from options
- `confirm`: Yes/no (y/N)

**Example**:

```yaml
questions:
  - id: coding_standards
    question: "What coding standards do you follow?"
    type: text
    default: "PEP 8"
    help: "Examples: PEP 8, Airbnb, PSR-12"
```

### Template Renderer

**File**: `utils/template_renderer.py`

**Responsibilities**:

- Render Jinja2 templates
- Handle file and directory templates
- Support filename templating
- Skip binary files
- Error handling

**Key Features**:

- Templates use `.jinja2` extension
- Variables passed to all templates
- Filenames can be templated: `{{skill_name}}.md.jinja2`
- Binary files (images, etc.) copied as-is

**Example**:

```jinja2
---
name: {{ skill_name }}
description: {{ skill_description }}
---

# {{ skill_name | title }}

{{ skill_content }}
```

### Feedback System

**File**: `scripts/feedback.py`

**Responsibilities**:

- Create GitHub issues via `gh` CLI
- Templates for bugs, features, feedback
- Auto-fill environment information
- Validation and error handling

**Templates**:

- Bug report: System info, steps to reproduce
- Feature request: Problem, solution, alternatives
- General feedback: Open-ended

## Data Flow

### Installation Flow

```text
User
  │
  ├─> /aida config
  │
  ▼
check_python_version()
  │
  ├─> Python >= 3.8?
  │   ├─ Yes → Continue
  │   └─ No  → Error + Exit
  │
  ▼
is_already_installed()
  │
  ├─> Personal skills exist?
  │   ├─ Yes → Prompt reinstall
  │   │   ├─ Confirm → Backup + Continue
  │   │   └─ Decline → Exit
  │   └─ No  → Continue
  │
  ▼
run_questionnaire("install.yml")
  │
  ├─> Load questions from YAML
  ├─> Display questions
  ├─> Collect answers
  └─> Validate responses
  │
  ▼
create_directory_structure()
  │
  ├─> ~/.claude/skills/user-context/
  └─> ~/.claude/skills/aida-core/
  │
  ▼
render_skills()
  │
  ├─> Load templates
  ├─> Inject questionnaire responses
  ├─> Render with Jinja2
  └─> Write SKILL.md files
  │
  ▼
update_settings_json()
  │
  ├─> Read existing settings
  ├─> Merge AIDA config
  └─> Write back
  │
  ▼
Success!
```

### Configuration Flow

```text
User
  │
  ├─> /aida config
  │
  ▼
check_installation()
  │
  ├─> Personal skills exist?
  │   ├─ Yes → Continue
  │   └─ No  → Error: Run /aida config first
  │
  ▼
detect_project()
  │
  ├─> Detect language
  ├─> Detect framework
  ├─> Detect tools
  └─> Detect patterns
  │
  ▼
run_questionnaire("configure.yml")
  │
  ├─> Display detected info
  ├─> Ask project questions
  └─> Collect answers
  │
  ▼
create_project_skills()
  │
  ├─> .claude/skills/project-context/
  └─> .claude/skills/project-documentation/
  │
  ▼
update_project_settings()
  │
  └─> Write .claude/settings.json
  │
  ▼
Success!
```

### Skill Loading Flow (Claude Code)

```text
Claude Code Start
  │
  ▼
Load Plugins
  │
  ├─> Load aida-core
  │
  ▼
Load Global Skills
  │
  ├─> Scan ~/.claude/skills/
  ├─> Read *.md files
  └─> Parse frontmatter
  │
  ▼
Load Project Skills (if in project)
  │
  ├─> Scan .claude/skills/
  ├─> Read *.md files
  └─> Parse frontmatter
  │
  ▼
Skills Active
  │
  └─> Claude has context
```

## Directory Structure

### Global Configuration

```text
~/.claude/
├── skills/                      # Personal skills (global)
│   ├── user-context/
│   │   └── SKILL.md            # Environment, preferences, standards
│   └── aida-core/
│       └── SKILL.md            # AIDA management knowledge
├── settings.json               # Claude Code settings
├── plugins/
│   └── aida-core/         # This plugin
│       ├── .claude-plugin/
│       │   └── plugin.json     # Plugin metadata
│       ├── scripts/
│       │   ├── install.py
│       │   ├── feedback.py
│       │   └── utils/
│       │       ├── __init__.py
│       │       ├── version.py
│       │       ├── paths.py
│       │       ├── files.py
│       │       ├── questionnaire.py
│       │       ├── inference.py
│       │       ├── template_renderer.py
│       │       └── errors.py
│       └── templates/
│           ├── blueprints/
│           │   └── user-context/
│           │       └── SKILL.md.jinja2
│           └── questionnaires/
│               ├── install.yml
│               └── configure.yml
└── cache/                      # (future) Cached data
```

### Project Configuration

```text
your-project/
├── .claude/
│   ├── skills/                 # Project-specific skills
│   │   ├── project-context/
│   │   │   └── SKILL.md        # Architecture, stack
│   │   └── project-documentation/
│   │       └── SKILL.md        # Documentation standards
│   └── settings.json           # Project settings
└── [your project files...]
```

## Extension Points

AIDA is designed to be extensible. Users can add:

### 1. Custom Skills

**Location**: `~/.claude/skills/` (global) or `.claude/skills/` (project)

**Create with**: `/aida skill create`

**Structure**:

```markdown
---
name: my-custom-skill
description: My custom behavior
scope: global|project
---

# My Custom Skill

Content here...
```

### 2. Custom Agents

**Location**: `.claude/agents/` (project)

**Create with**: `/aida agent create`

**Structure**:

```markdown
---
name: my-agent
description: Agent persona
---

# My Agent

You are [persona description]...
```

### 3. Template Customization

Users can modify templates in:

- `templates/blueprints/` - Skill templates
- `templates/questionnaires/` - Question sets

### 4. Python Utilities Extension

Developers can extend the utils module:

```python
from utils import (
    check_python_version,
    get_claude_dir,
    run_questionnaire,
    render_skill_directory
)

# Build custom scripts using foundation
```

## Design Decisions

See [Architecture Decision Records](architecture/adr/) for detailed rationale.

### ADR Index

- [ADR-001: Skills-First Architecture](architecture/adr/001-skills-first-architecture.md)
- [ADR-002: Python for Installation Scripts](architecture/adr/002-python-for-scripts.md)
- [ADR-003: Jinja2 for Templates](architecture/adr/003-jinja2-templates.md)
- [ADR-004: YAML for Questionnaires](architecture/adr/004-yaml-questionnaires.md)
- [ADR-005: Local-First Storage](architecture/adr/005-local-first-storage.md)
- [ADR-006: gh CLI for Feedback](architecture/adr/006-gh-cli-feedback.md)
- [ADR-007: YAML Config as Single Source of Truth](architecture/adr/007-yaml-config-single-source-truth.md)
- [ADR-008: Marketplace-Centric Distribution](architecture/adr/008-marketplace-centric-distribution.md)
- [ADR-009: Input Validation and Path Security](architecture/adr/009-input-validation-path-security.md)
- [ADR-010: Two-Phase API for LLM Integration](architecture/adr/010-two-phase-api-pattern.md)
- [ADR-011: User-Level Memento Storage](architecture/adr/011-user-level-memento-storage.md)

### Key Decisions Summary

#### Skills Over Memory

- **Decision**: Focus on skills (context) over memory (state)
- **Rationale**: Skills are persistent and sharable; memory requires maintenance
- **Trade-off**: No auto-updating context (yet)

#### Python for Scripts

- **Decision**: Use Python 3.8+ for all scripts
- **Rationale**: Cross-platform, rich ecosystem, Claude Code users likely have it
- **Trade-off**: Adds Python dependency

#### Jinja2 for Templates

- **Decision**: Use Jinja2 template engine
- **Rationale**: Powerful, well-known, handles edge cases
- **Trade-off**: Learning curve for template syntax

#### Local File Storage

- **Decision**: Store all data in `~/.claude/` and `.claude/`
- **Rationale**: Privacy, offline support, no infrastructure
- **Trade-off**: No cloud sync (future feature)

## Security Considerations

### Input Validation

**Questionnaires**:

- All input sanitized before file operations
- Path traversal prevention
- No code execution in templates

**File Operations**:

- Validate paths before read/write
- Check permissions before operations
- No arbitrary file deletion

### Dependencies

**Python Dependencies**:

- Minimal dependencies (Jinja2, PyYAML only)
- Pinned versions in requirements.txt
- Regular security updates

**External Commands**:

- `gh` CLI - official GitHub tool
- Input sanitized before shell execution

### Data Privacy

**Local Storage**:

- No network requests except `gh` CLI
- No telemetry or analytics
- User data never leaves machine

**GitHub Feedback**:

- Opt-in only (user runs `/aida bug`)
- User reviews before submission
- No automatic data collection

### File Permissions

**Installation**:

- Respects user file permissions
- No sudo/root required
- Only writes to `~/.claude/` and `.claude/`

**Skill Files**:

- Readable only by user
- Standard file permissions (644)

## Performance Considerations

### Installation Speed

**Target**: < 30 seconds for `/aida config`

**Optimizations**:

- Lazy imports in Python
- Minimal file operations
- No network requests (except gh check)

### Skill Loading

**Claude Code**:

- Skills loaded at startup
- Cached in memory
- No runtime overhead

### Template Rendering

**Performance**:

- Templates rendered once at install/configure
- Cached Jinja2 environment
- No runtime template rendering

### File System

**Efficiency**:

- Minimal file I/O
- Batch operations where possible
- No unnecessary scans

## Further Reading

### Detailed Documentation

- **[C4 Diagrams](architecture/c4/)**: Visual architecture models
  - [Context Diagram](architecture/c4/context-diagram.md)
  - [Container Diagram](architecture/c4/container-diagram.md)
  - [Component Diagram](architecture/c4/component-diagram.md)
- **[Architecture Decision Records](architecture/adr/)**: Design rationale
- **[API Reference](API.md)**: Python utilities API
- **[Development Guide](DEVELOPMENT.md)**: Contributing

### External Resources

- [Claude Code Plugin System](https://docs.claude.com/code/plugins)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [C4 Model](https://c4model.com/)

---

**Questions?** See [Development Guide](DEVELOPMENT.md) or `/aida feedback`
