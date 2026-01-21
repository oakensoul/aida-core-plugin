---
type: reference
title: Plugin Development Guide
description: Comprehensive guide to creating, structuring, and distributing Claude Code plugins
---

# Plugin Development

Plugins are the unit of distribution for Claude Code extensions. They package
agents, commands, skills, and shared resources into installable bundles.

## What is a Plugin?

A plugin is a **distributable package** that contains:

- Agents (expert personas)
- Commands (user entry points)
- Skills (automation capabilities)
- Shared resources (templates, scripts, references)
- Metadata for installation and discovery

Plugins solve the distribution problem: "How do I share my extensions with others?"

## When to Create a Plugin

Create a plugin when you want to:

- **Distribute**: Share extensions with a team or community
- **Bundle**: Group related components that work together
- **Version**: Track changes and updates as a unit
- **Install**: Let users add your extensions with one command

Don't create a plugin for:

- Single-use extensions (keep them local)
- Exploratory/experimental work (stabilize first)
- Project-specific customizations (use project CLAUDE.md)

## Plugin Structure

### Required Files

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # REQUIRED: Plugin metadata
└── README.md             # REQUIRED: Documentation
```

### Full Structure

```text
my-plugin/
├── .claude-plugin/
│   ├── plugin.json       # Plugin metadata
│   └── marketplace.json  # Optional: Marketplace listing
├── agents/
│   └── my-agent/
│       ├── my-agent.md
│       └── knowledge/
│           ├── index.md
│           └── domain.md
├── commands/
│   └── my-command.md
├── skills/
│   └── my-skill/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── action.py
│       └── templates/
│           └── output.jinja2
├── templates/            # Shared templates (optional)
├── README.md
├── CHANGELOG.md          # Recommended
├── LICENSE               # Recommended for public plugins
└── .gitignore
```

## plugin.json Schema

### Required Fields

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief description of what this plugin provides"
}
```

### Complete Schema

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief description of what this plugin provides",
  "author": "Your Name or Organization",
  "license": "MIT",
  "repository": "https://github.com/username/my-plugin",
  "homepage": "https://your-plugin-docs.example.com",
  "keywords": [
    "keyword1",
    "keyword2"
  ],
  "dependencies": {
    "other-plugin": "^1.0.0"
  },
  "engines": {
    "claude-code": ">=1.0.0"
  }
}
```

### Field Definitions

| Field | Required | Description |
| ----- | -------- | ----------- |
| `name` | Yes | Unique identifier (kebab-case) |
| `version` | Yes | Semantic version (X.Y.Z) |
| `description` | Yes | One-line description |
| `author` | No | Creator name or organization |
| `license` | No | SPDX license identifier |
| `repository` | No | Source code URL |
| `homepage` | No | Documentation URL |
| `keywords` | No | Search/discovery terms |
| `dependencies` | No | Required plugins |
| `engines` | No | Version constraints |

## marketplace.json Schema

For plugins published to the marketplace:

```json
{
  "displayName": "My Plugin",
  "shortDescription": "A short tagline (max 100 chars)",
  "longDescription": "Detailed description with markdown support...",
  "category": "development",
  "icon": "icon.png",
  "screenshots": [
    "screenshots/demo1.png"
  ],
  "pricing": "free",
  "support": {
    "email": "support@example.com",
    "issues": "https://github.com/username/my-plugin/issues"
  }
}
```

### Categories

- `development` - Developer tools and workflows
- `productivity` - General productivity enhancements
- `integration` - External service integrations
- `framework` - Framework-specific tools
- `testing` - Testing and quality tools
- `documentation` - Documentation generation
- `devops` - CI/CD and deployment

## Installation and Management

### Installing Plugins

```bash
# From marketplace (when available)
/aida plugin add my-plugin

# From Git repository
/aida plugin add https://github.com/username/my-plugin

# From local directory
/aida plugin add /path/to/my-plugin
```

### Managing Plugins

```bash
# List installed plugins
/aida plugin list

# View plugin details
/aida plugin info my-plugin

# Update plugin
/aida plugin update my-plugin

# Remove plugin
/aida plugin remove my-plugin
```

## Versioning Strategy

Follow Semantic Versioning (SemVer):

### Major Version (X.0.0)

Breaking changes:

- Removing agents, commands, or skills
- Changing command argument formats
- Incompatible schema changes
- Renamed entry points

### Minor Version (0.X.0)

New features (backwards compatible):

- Adding new agents, commands, or skills
- New optional parameters
- Enhanced functionality
- New knowledge files

### Patch Version (0.0.X)

Bug fixes (backwards compatible):

- Fixing errors
- Documentation updates
- Performance improvements
- Minor refinements

### Pre-release Versions

For testing before release:

```text
1.0.0-alpha.1
1.0.0-beta.1
1.0.0-rc.1
```

## Dependencies

### Declaring Dependencies

```json
{
  "dependencies": {
    "base-plugin": "^1.0.0",
    "optional-plugin": "~2.3.0"
  }
}
```

### Version Operators

| Operator | Meaning | Example |
| -------- | ------- | ------- |
| `^` | Compatible | `^1.2.3` = `>=1.2.3 <2.0.0` |
| `~` | Patch updates | `~1.2.3` = `>=1.2.3 <1.3.0` |
| `>=` | Minimum | `>=1.0.0` |
| `=` | Exact | `=1.2.3` |

### Dependency Resolution

Plugins install dependencies automatically. Conflicts are resolved by:

1. Using the highest compatible version
2. Warning if incompatible versions required
3. Failing if no resolution possible

## Best Practices

### Naming Conventions

- Plugin names: `kebab-case`
- Be specific: `react-testing-tools` not `testing`
- Avoid generic terms: `awesome-plugin` is not useful
- Use scopes for organizations: `@myorg/plugin-name`

### Documentation

Include in README.md:

1. **What it does** - Clear value proposition
2. **Installation** - How to install
3. **Quick start** - Basic usage example
4. **Components** - List of agents/commands/skills
5. **Configuration** - Any setup required
6. **Examples** - Common use cases

### Quality Checklist

Before publishing:

- [ ] All components have proper frontmatter
- [ ] README.md is comprehensive
- [ ] CHANGELOG.md documents changes
- [ ] No hardcoded paths (use path resolution)
- [ ] No secrets or credentials
- [ ] License file included (for public plugins)
- [ ] Version follows SemVer
- [ ] Tests pass (if applicable)

### Security Considerations

- Never include secrets or API keys
- Avoid shell commands that could be dangerous
- Document any external network calls
- Use parameter validation in scripts
- Prefer read operations over write operations

## Plugin Organization Patterns

### Single-Purpose Plugin

For focused functionality:

```text
linting-plugin/
├── commands/
│   └── lint.md           # Entry point
└── skills/
    └── linting/          # The automation
```

### Toolkit Plugin

For related tools:

```text
testing-toolkit/
├── agents/
│   └── test-advisor/     # Strategy guidance
├── commands/
│   ├── test.md           # Run tests
│   └── coverage.md       # Coverage reports
└── skills/
    ├── test-runner/      # Execution
    └── coverage/         # Analysis
```

### Framework Plugin

For framework-specific support:

```text
react-plugin/
├── agents/
│   └── react-expert/     # React expertise
├── commands/
│   └── react.md          # Namespace command
└── skills/
    ├── component-gen/    # Component generation
    └── hooks/            # Hook templates
```

## Common Issues

### Path Resolution

**Problem:** Paths break when installed in different locations.

**Solution:** Use relative paths or path resolution utilities:

```python
# In scripts
plugin_dir = Path(__file__).parent.parent.parent
template_path = plugin_dir / "templates" / "my-template.jinja2"
```

### Version Conflicts

**Problem:** Two plugins require incompatible versions of a dependency.

**Solution:**

1. Update to latest compatible versions
2. Contact plugin authors for updates
3. Fork and update dependency locally

### Missing Components

**Problem:** Commands reference skills that don't exist.

**Solution:**

1. Ensure all referenced components exist
2. Use `/aida plugin validate` to check integrity
3. Test installation in clean environment
