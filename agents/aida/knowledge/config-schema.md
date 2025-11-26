---
type: reference
title: AIDA Configuration Schema
description: Schema and validation rules for aida-project-context.yml
---

# Configuration Schema

AIDA uses YAML configuration files to store project context and user preferences.

## File Locations

- **Global**: `~/.claude/aida.yml` - User-wide settings
- **Project**: `.claude/aida-project-context.yml` - Project-specific context

## Project Configuration Schema

```yaml
# Version of the config schema
version: "0.2.0"

# Whether configuration is complete
config_complete: true|false

# Version Control System
vcs:
  type: git|svn|mercurial|none
  remote: github|gitlab|bitbucket|azure|none
  default_branch: main|master|develop|trunk
  uses_worktrees: true|false

# Project Files
files:
  has_readme: true|false
  has_license: true|false
  has_contributing: true|false
  has_changelog: true|false
  has_claude_md: true|false

# Languages & Frameworks
languages:
  primary: Python|JavaScript|TypeScript|Go|Rust|Java|...
  all:
    - Python
    - JavaScript
    - ...

# Development Tools
tools:
  detected:
    - Git
    - pytest
    - npm
    - ...
  package_manager: pip|npm|yarn|pnpm|cargo|go|...

# Inferred Project Characteristics
inferred:
  project_type: "CLI Tool"|"Web App"|"Library"|"API"|"Unknown"
  team_collaboration: Solo|Small Team|Large Team
  maturity: New|Active|Maintenance

# User Preferences (may be null until configured)
preferences:
  branching_model: github-flow|git-flow|trunk|null
  issue_tracking: "GitHub Issues"|"Jira"|"Linear"|"None"|null
  commit_style: conventional|semantic|freeform|null
  pr_template: true|false|null
```

## Required Fields

These fields must be present:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `version` | string | Schema version (e.g., "0.2.0") |
| `config_complete` | boolean | Whether setup is finished |
| `vcs.type` | string | Version control system |
| `languages.primary` | string | Main language |

## Optional Fields

All other fields are optional and will use defaults or null.

## Defaults

When not specified:

| Field | Default |
| ----- | ------- |
| `vcs.default_branch` | "main" |
| `vcs.uses_worktrees` | false |
| `inferred.team_collaboration` | "Solo" |
| `preferences.*` | null |

## Validation Rules

### Version

- Must be semver format: `"X.Y.Z"`
- Current schema version: `"0.2.0"`

### VCS Type

Valid values:

- `git` - Git repository
- `svn` - Subversion
- `mercurial` - Mercurial
- `none` - No version control

### Languages

- `primary` must be a recognized language
- `all` must include `primary`
- Use official language names (Python, not python or py)

### Preferences

- Can be null (not yet configured)
- Once set, must be valid value from allowed list

## Drift Detection

When reviewing configs, check for drift:

| Check | Issue |
| ----- | ----- |
| `languages.all` missing detected language | Config outdated |
| `tools.detected` missing installed tool | Config outdated |
| `vcs.remote` doesn't match actual remote | Config incorrect |
| `config_complete: true` but nulls in preferences | Incomplete config |

## Example Configuration

```yaml
version: "0.2.0"
config_complete: true

vcs:
  type: git
  remote: github
  default_branch: main
  uses_worktrees: false

files:
  has_readme: true
  has_license: true
  has_contributing: false
  has_changelog: true
  has_claude_md: true

languages:
  primary: Python
  all:
    - Python
    - YAML
    - Markdown

tools:
  detected:
    - Git
    - pytest
    - ruff
    - pip
  package_manager: pip

inferred:
  project_type: "CLI Tool"
  team_collaboration: "Solo"
  maturity: "Active"

preferences:
  branching_model: github-flow
  issue_tracking: "GitHub Issues"
  commit_style: conventional
  pr_template: true
```
