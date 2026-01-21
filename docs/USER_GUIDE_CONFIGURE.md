---
type: guide
title: "Configuration Guide"
audience: users
---

# AIDA Configuration Guide

Complete walkthrough for configuring AIDA for your projects

This guide walks you through using the unified `/aida config` command
(introduced in v0.2.0) to set up project-specific context, skills, and
preferences.

Note: As of v0.2.0, AIDA uses a unified `/aida config` command (not separate
install/configure commands) with smart auto-detection that reduces questions
from 22 → 2!

## Table of Contents

- [Prerequisites](#prerequisites)
- [When to Configure](#when-to-configure)
- [Configuration Steps](#configuration-steps)
- [Questionnaire Deep Dive](#questionnaire-deep-dive)
- [Project Detection](#project-detection)
- [What Gets Created](#what-gets-created)
- [PKM Integration](#pkm-integration)
- [Verification](#verification)
- [Working with Multiple Projects](#working-with-multiple-projects)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Prerequisites

Before configuring a project, you should:

### 1. Install AIDA Globally (Optional but Recommended)

```bash
/aida config
```

Select "Set up AIDA globally" from the menu. This is optional but recommended.

**Check if installed:**

```bash
/aida status

# Should show:
# Installation: ✓ Installed
```

### 2. Be in a Project Directory

Configuration is project-specific. Navigate to your project root:

```bash
cd /path/to/your-project/
```

**Recommended**: Run from git repository root for best auto-detection.

## When to Configure

Run `/aida config` when:

### First Time Setup

- ✅ Starting work on a new project with AIDA
- ✅ First time using AIDA on an existing project
- ✅ Want Claude to understand project-specific context

### Updates

- ✅ Project architecture has changed significantly
- ✅ New conventions or patterns adopted
- ✅ Team structure or testing approach changed
- ✅ Documentation requirements updated

### Don't Reconfigure For

- ❌ Minor code changes
- ❌ Adding new features (unless changing architecture)
- ❌ Bug fixes
- ❌ Dependency updates

## Configuration Steps

### Step 1: Navigate to Project

```bash
cd your-project/
```

Ensure you're at the project root (where `package.json`, `pyproject.toml`, `.git/`, etc. live).

### Step 2: Run Configuration

```bash
/aida config
```

#### 2.1 Installation Check

```text
Checking AIDA installation...
✓ Personal skills found
✓ Ready to configure project
```

**If check fails:**

```text
✗ AIDA not installed

Run /aida config first to set up personal preferences.
```

Solution: Run `/aida config` first (see [Installation Guide](USER_GUIDE_INSTALL.md))

#### 2.2 Existing Configuration Check

If you've already configured this project:

```text
⚠ Project already configured at:
  .claude/skills/project-context/
  .claude/skills/project-documentation/

Do you want to reconfigure? This will overwrite existing project skills.

[y/N]: _
```

**Choices:**

- `N` (default): Keep existing configuration
- `y`: Reconfigure (existing skills will be backed up)

**Backup location**: `.claude/skills/.backup-TIMESTAMP/`

#### 2.3 Project Detection

AIDA automatically detects project details:

```text
Detecting project...

✓ Git repository: yes
✓ Language: TypeScript
✓ Framework: React (Next.js)
✓ Package manager: npm
✓ Build tool: Webpack

Project name: my-awesome-app
Root directory: /Users/me/projects/my-awesome-app
```

**Detection includes:**

- Git repository status
- Primary language(s)
- Frameworks and libraries
- Package managers (npm, pip, cargo, etc.)
- Build tools
- Testing frameworks
- CI/CD configuration

See [Project Detection](#project-detection) for details.

#### 2.4 Interactive Questionnaire

AIDA asks 5 questions about your project:

```text
Let's configure AIDA for this project.
This takes about 2 minutes.

Press Ctrl+C at any time to cancel.

───────────────────────────────────────────────────────────
```

See [Questionnaire Deep Dive](#questionnaire-deep-dive) for detailed explanations.

#### 2.5 PKM Symlink Prompt

After the questionnaire, you can optionally link your Personal Knowledge Management system:

```text
PKM Integration (Optional)
───────────────────────────────────────────────────────────

Do you maintain project documentation in a PKM system
(Obsidian, Notion, etc.)?

Create a .pkm/ symlink in this project? [y/N]: _
```

See [PKM Integration](#pkm-integration) for details.

#### 2.6 Skill Creation

```text
Creating project skills...

✓ Created .claude/skills/project-context/SKILL.md
✓ Created .claude/skills/project-documentation/SKILL.md
✓ Created .claude/settings.json

───────────────────────────────────────────────────────────
```

#### 2.7 Success Message

```text
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ✓ Project Configuration Complete!                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Project skills created at:
  .claude/skills/project-context/
  .claude/skills/project-documentation/

These skills will be active when working in this project,
providing Claude with project-specific context.

Next Steps:
  1. Start coding - Claude now knows your project!
  2. Check configuration:
     /aida status
  3. Update skills if project evolves:
     /aida config

Happy coding! 🚀
```

**Total time**: ~2-3 minutes

## Questionnaire Deep Dive

The configuration questionnaire asks 5 questions about your project.

### Question 1: Project Type

```text
What type of project is this?

Choose one:
  [1] Web application (frontend)
  [2] Web application (backend)
  [3] Web application (full-stack)
  [4] CLI tool or utility
  [5] Library or framework
  [6] Data science / ML project
  [7] Mobile application
  [8] DevOps / Infrastructure
  [9] Monorepo with multiple projects
  [10] Other

Your choice: _
```

**Purpose**: Provides high-level project context

**Common choices:**

- **Option 1**: React, Vue, Angular apps
- **Option 2**: REST APIs, GraphQL servers
- **Option 3**: Next.js, Django, Rails full-stack apps
- **Option 4**: Command-line tools
- **Option 5**: npm packages, Python libraries
- **Option 6**: Jupyter notebooks, ML pipelines
- **Option 9**: Multi-package repositories

**Impact**: High - affects suggestions for architecture, patterns, and tooling

### Question 2: Team Collaboration Style

```text
What is your team collaboration style for this project?

Choose one:
  [1] Solo project - just me
  [2] Small team (2-5 people) with frequent sync
  [3] Medium team (6-20) with defined roles
  [4] Large team (20+) with formal processes
  [5] Open source with external contributors

Your choice [1]: _
```

**Purpose**: Affects suggestions for commits, PRs, and documentation

**Default**: Option 1 (Solo project)

**Choose based on:**

- **Option 1**: Personal projects, experiments
- **Option 2**: Startup, small company team
- **Option 3**: Established company, defined process
- **Option 4**: Enterprise with formal procedures
- **Option 5**: GitHub OSS with community

**Impact**: Medium - affects commit message style, PR recommendations

### Question 3: Testing Approach

```text
What is your testing approach for this project?

Choose one:
  [1] Minimal - manual testing only
  [2] Unit tests for critical paths
  [3] Comprehensive unit + integration tests
  [4] TDD - tests written first
  [5] BDD - behavior-driven development
  [6] Mixed - depends on the component

Your choice [2]: _
```

**Purpose**: Guides test generation and reminders

**Default**: Option 2 (Unit tests for critical paths)

**Choose based on:**

- **Option 1**: Quick prototypes, POCs
- **Option 2**: Standard approach for most projects
- **Option 3**: High-quality production code
- **Option 4**: Test-first development
- **Option 5**: Cucumber, Gherkin syntax
- **Option 6**: Different strategies per module

**Impact**: High - affects test generation suggestions

### Question 4: Documentation Level

```text
How much documentation should this project maintain?

Choose one:
  [1] Minimal - README and inline comments
  [2] Standard - README, API docs, inline comments
  [3] Comprehensive - Full guides, examples, architecture docs
  [4] Extensive - Documentation-first approach

Your choice [2]: _
```

**Purpose**: Determines documentation suggestions

**Default**: Option 2 (Standard)

**Choose based on:**

- **Option 1**: Internal tools, simple projects
- **Option 2**: Most projects
- **Option 3**: User-facing products, libraries
- **Option 4**: Open source, enterprise APIs

**Impact**: Medium - affects documentation reminders

### Question 5: Project-Specific Conventions

```text
Are there any project-specific conventions or patterns to follow?

Examples:
  - Use Redux for state management
  - All API calls in /services directory
  - Feature flags required for new features
  - Follow 12-factor app principles

Leave blank if none.

Your answer (multiline, Ctrl+D when done):
_
```

**Purpose**: Captures unique project patterns

**Optional**: Can leave blank

**Good examples:**

- "Repository pattern for data access"
- "Use feature flags for all UI changes"
- "API responses must include request IDs"
- "Follow domain-driven design principles"
- "All components must have Storybook stories"

**Bad examples:**

- "Write good code" (too vague)
- Listing basic conventions already in coding standards

**Impact**: High - directly affects code generation patterns

## Project Detection

AIDA automatically detects project characteristics to provide smart defaults.

### What Gets Detected

#### Language Detection

**Looks for:**

- `package.json` → JavaScript/TypeScript
- `pyproject.toml`, `setup.py`, `requirements.txt` → Python
- `Cargo.toml` → Rust
- `go.mod` → Go
- `pom.xml`, `build.gradle` → Java
- `composer.json` → PHP
- `Gemfile` → Ruby

**Multiple languages**: Detected and reported (e.g., "Python + JavaScript")

#### Framework Detection

**JavaScript/TypeScript:**

- React, Vue, Angular, Svelte (from dependencies)
- Next.js, Gatsby, Remix (from config files)
- Express, Fastify, NestJS (from dependencies)

**Python:**

- Django (manage.py, settings.py)
- Flask (app.py patterns)
- FastAPI (from dependencies)

**And more**: Rails, Laravel, Spring Boot, etc.

#### Tool Detection

**Build tools:**

- Webpack, Vite, Parcel (config files)
- Babel, ESBuild, SWC (config files)

**Testing:**

- Jest, Vitest, Mocha (config files)
- PyTest, unittest (test directories)
- Go testing (test files)

**CI/CD:**

- GitHub Actions (`.github/workflows/`)
- GitLab CI (`.gitlab-ci.yml`)
- CircleCI (`.circleci/config.yml`)

### Manual Override

Detection isn't perfect. You can manually specify in Question 5 (conventions):

```text
Your answer:
Project uses custom build system (Make + shell scripts)
Testing via custom test runner in /tests
```

## What Gets Created

After configuration, AIDA creates project-specific files:

### Directory Structure

```text
your-project/
├── .claude/
│   ├── skills/
│   │   ├── project-context/
│   │   │   └── SKILL.md           # Project overview
│   │   └── project-documentation/
│   │       └── SKILL.md           # Documentation standards
│   └── settings.json              # Project settings
├── .pkm/                          # Optional symlink
└── [your project files...]
```

### Project Context Skill

**Location**: `.claude/skills/project-context/SKILL.md`

**Content** (example):

```markdown
---
name: project-context
description: Context about this specific project
scope: project
---

# Project Context: my-awesome-app

This skill provides Claude with context about this specific project.

## Project Type

Web application (full-stack)

## Technology Stack

- Language: TypeScript
- Framework: Next.js 14
- Database: PostgreSQL
- Package Manager: npm
- Build Tool: Webpack

## Team Collaboration

Small team (2-5 people) with frequent sync

## Testing Approach

Comprehensive unit + integration tests

Testing framework: Jest + React Testing Library

## Project Conventions

- Use Redux Toolkit for global state
- All API routes in /pages/api
- Feature flags via LaunchDarkly
- Storybook required for UI components
```

**Purpose**: Project-specific architecture and patterns

### Project Documentation Skill

**Location**: `.claude/skills/project-documentation/SKILL.md`

**Content** (example):

```markdown
---
name: project-documentation
description: Documentation standards for this project
scope: project
---

# Project Documentation Standards

This skill defines the documentation standards for this project.

## Documentation Level

Comprehensive - Full guides, examples, architecture docs

## Required Documentation

- README with setup instructions
- API documentation (OpenAPI/Swagger)
- Architecture Decision Records (ADRs)
- Component documentation (Storybook)
- End-user guides

## Documentation Location

- `/docs` - Technical documentation
- `/docs/architecture` - ADRs and diagrams
- `/docs/api` - API reference
- Inline JSDoc comments for all public APIs
```

**Purpose**: Documentation standards and requirements

### Project Settings

**Location**: `.claude/settings.json`

```json
{
  "project": {
    "name": "my-awesome-app",
    "type": "web-application-fullstack",
    "detected": {
      "language": "typescript",
      "framework": "nextjs",
      "testing": "jest"
    }
  },
  "aida": {
    "configured": true,
    "configuredAt": "2025-11-03T12:00:00Z"
  }
}
```

**Purpose**: Machine-readable project metadata

## PKM Integration

AIDA can integrate with Personal Knowledge Management systems.

### What is PKM Integration?

If you maintain project documentation in Obsidian, Notion, Logseq, or similar tools, AIDA can create a symlink to your notes.

**Benefits:**

- Claude can reference your detailed notes
- Keep single source of truth
- Documentation stays in your PKM system

### Setting Up PKM Symlink

During configuration:

```text
Create a .pkm/ symlink in this project? [y/N]: y

Where is your PKM vault or project notes directory?
Path: ~/Obsidian/Projects/my-awesome-app

✓ Created symlink: .pkm/ → ~/Obsidian/Projects/my-awesome-app
```

**Result:**

```text
your-project/
├── .pkm/  → ~/Obsidian/Projects/my-awesome-app
│   ├── Architecture.md
│   ├── API-Design.md
│   └── Decisions.md
└── ...
```

Claude can now read your PKM notes when working on this project.

### Supported PKM Systems

- **Obsidian**: Markdown-based vault
- **Logseq**: Markdown/org-mode
- **Foam** (VS Code): Markdown
- **Notion**: Export to markdown first
- **Custom**: Any directory with markdown files

### Manual PKM Setup

Skip during configuration, add later:

```bash
cd your-project/
ln -s ~/Obsidian/Projects/my-awesome-app .pkm
```

### Removing PKM Link

```bash
cd your-project/
rm .pkm  # Just removes symlink, not your notes!
```

## Verification

After configuration, verify everything works:

### Step 1: Check Status

```bash
/aida status
```

**Expected output:**

```text
AIDA Status

Installation: ✓ Installed
  Personal skills: 2

Project Configuration: ✓ Configured
  Project: my-awesome-app
  Location: /Users/me/projects/my-awesome-app
  Configured: 2025-11-03

Project Skills:
  ✓ project-context
  ✓ project-documentation

Detected:
  Language: TypeScript
  Framework: Next.js
  Testing: Jest
```

### Step 2: Verify Project Skills

```bash
/aida skill list
```

**Expected output:**

```text
Global Skills:
  • personal-preferences
  • work-patterns
  • aida-core

Project Skills (.claude/skills/):
  • project-context         ← NEW
  • project-documentation   ← NEW
```

### Step 3: Check Skill Content

```bash
/aida skill info project-context
```

Shows full content of the project context skill.

### Step 4: Test Context

Ask Claude a project-specific question:

```text
You: What testing framework should I use for this feature?

Claude: Based on your project configuration, you should use Jest
with React Testing Library, since this project uses comprehensive
unit + integration tests...
```

Claude should reference your project context!

## Working with Multiple Projects

AIDA supports configuration for multiple projects simultaneously.

### Separate Configuration Per Project

Each project has its own `.claude/` directory:

```text
~/projects/
├── project-a/
│   └── .claude/
│       └── skills/
│           ├── project-context/
│           └── project-documentation/
├── project-b/
│   └── .claude/
│       └── skills/
│           ├── project-context/
│           └── project-documentation/
└── project-c/
    └── .claude/
        └── skills/
            ├── project-context/
            └── project-documentation/
```

### Switching Between Projects

Just change directories:

```bash
cd ~/projects/project-a
# Claude uses project-a skills

cd ~/projects/project-b
# Claude uses project-b skills
```

No need to reconfigure or restart Claude Code!

### Shared Personal Skills

Your personal preferences apply to all projects:

```text
~/.claude/skills/
├── personal-preferences/   ← Active in ALL projects
└── work-patterns/          ← Active in ALL projects
```

### Example Multi-Project Workflow

```bash
# Morning: Work on frontend project
cd ~/projects/ecommerce-frontend
/aida status  # Shows frontend config
# Work on React components...

# Afternoon: Switch to backend project
cd ~/projects/ecommerce-backend
/aida status  # Shows backend config
# Work on API endpoints...

# Evening: Personal project
cd ~/projects/blog
/aida config  # First time, configure it
# Work on blog features...
```

Each project has appropriate context automatically!

## Troubleshooting

### Configuration Issues

#### Error: "AIDA not installed"

**Cause**: `/aida config` hasn't been run

**Solution**:

```bash
/aida config
# Complete installation first
cd your-project/
/aida config
```

#### Error: "Not in a git repository"

**Cause**: Project detection works best with git repos

**Solution**:

```bash
git init
# OR run from a different directory
/aida config
```

Configuration will work, but detection may be limited.

#### Error: "Permission denied: .claude/"

**Cause**: Cannot write to project directory

**Solution**:

```bash
# Check permissions
ls -la .claude/

# Fix if needed
chmod -R u+w .claude/

# Or check if directory is owned by you
ls -la .
```

### Detection Issues

#### Wrong Language/Framework Detected

**Not critical**: Detection is just for context. Manual specification in Question 5 overrides.

**Example**:

```text
Your answer (Question 5):
Actually uses Python with Flask (not detected correctly)
```

#### No Framework Detected

**Normal**: Not all projects use frameworks. Just answer questions accurately.

### PKM Issues

#### Symlink Creation Failed

**Possible causes:**

1. Invalid path provided
2. Target directory doesn't exist
3. Permission issues

**Solution**:

```bash
# Verify path exists
ls ~/path/to/pkm/directory

# Create manually if needed
ln -s ~/path/to/pkm/directory .pkm

# Verify
ls -la .pkm
```

#### Claude Can't Read PKM Notes

**Check:**

1. Symlink exists: `ls -la .pkm`
2. Target exists: `ls ~/.pkm/../`
3. Readable: `cat .pkm/some-note.md`

### Getting Help

1. **Run diagnostics**: `/aida doctor`
2. **Check status**: `/aida status`
3. **Report issue**: `/aida bug`
4. **Ask for help**: `/aida feedback`

## Best Practices

### When to Configure

**DO configure:**

- ✅ Starting new project with AIDA
- ✅ First time on existing project
- ✅ Architecture changed significantly
- ✅ Team or process changed

**DON'T reconfigure:**

- ❌ Minor refactorings
- ❌ Adding new features (unless pattern changes)
- ❌ Dependency updates
- ❌ Bug fixes

### Answering Questions

**Be specific:**

- ✅ "Repository pattern with interfaces, services in /domain"
- ❌ "Clean code"

**Reference existing docs:**

- ✅ "See architecture.md in /docs for details"
- ❌ Repeating entire architecture

**Update when needed:**

- ✅ Reconfigure when conventions change
- ❌ Leave outdated conventions

### Managing Multiple Projects

**Consistent structure:**

- Use same skill names across projects
- Follow similar documentation patterns
- Makes switching contexts easier

**Project-specific only:**

- Keep project skills focused on THIS project
- Don't duplicate personal preferences
- Personal preferences live in `~/.claude/skills/`

### PKM Integration

**Keep it focused:**

- Link project-specific notes only
- Don't link your entire vault
- Too much information can be overwhelming

**Structure helps:**

- Organize PKM notes clearly
- Use consistent naming
- Link to most relevant notes

### Maintenance

**Periodic review:**

- Check configuration quarterly
- Update if project evolved
- Remove outdated conventions

**Version control:**

- **DO** commit `.claude/skills/` to git
- **DO** commit `.claude/settings.json`
- **DON'T** commit `.pkm/` symlink (add to `.gitignore`)

**Team sharing:**

- Share project skills with team
- Everyone gets same context
- Commit to repository

---

**Questions?** Run `/aida feedback` or see [Troubleshooting](#troubleshooting)

**Ready to build?** Claude now understands your project context!

**Want to dive deeper?** → [Architecture Documentation](ARCHITECTURE.md)
