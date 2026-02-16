---
type: changelog
title: "AIDA Core Plugin Changelog"
---

# Changelog

All notable changes to AIDA Core Plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-02-16

### Added

#### Auto-generate Agent Routing Directives (#12)

- Agent discovery scans three sources in priority order: project
  (`{project}/.claude/agents/`), user (`~/.claude/agents/`), and
  plugin-provided agents (via `aida-config.json` manifest)
- YAML frontmatter parsing reads agent metadata (name, description,
  version, tags, skills, model) with `yaml.safe_load()`
- Auto-generates `## Available Agents` section in project CLAUDE.md
  with routing directives for each discovered agent
- Marker-based idempotent updates — re-running config replaces the
  managed section without duplicating or losing manual content
- Agent Teams guidance included so team leads and teammates know
  when to consult domain-specific agents
- First-found-wins deduplication (project > user > plugin priority)

### Changed

- `_safe_read_file` in plugins.py now accepts `max_size` parameter
  (defaults to 1MB for backward compatibility, agents use 500KB)
- `aida-config.json` supports `agents` key declaring plugin agent
  names (falls back to directory scanning if absent)
- Phase 1 (`get_questions`) discovers agents and returns metadata
- Phase 2 (`configure`) updates CLAUDE.md with routing directives

### Security

- Agent file reading reuses TOCTOU-safe `_safe_read_file` with
  `O_NOFOLLOW`, size limits, and path containment checks
- Symlinked directories and files rejected during agent scanning

---

## [0.6.1] - 2026-02-16

### Fixed

#### Plugin Validator Compatibility (#13)

- Moved `config` and `recommendedPermissions` from `plugin.json` to new
  `aida-config.json` to resolve Claude Code plugin validator rejecting
  unrecognized keys
- Plugin discovery reads AIDA-specific fields from `aida-config.json`
  (strict separation, no fallback to `plugin.json`)

### Security

- TOCTOU-safe file reading with `O_NOFOLLOW` in plugin discovery and
  permission scanner (eliminates symlink race conditions)
- Directory-level symlink rejection for `.claude-plugin` directories
- Consistent `isinstance(data, dict)` validation at all JSON parse boundaries
- Reordered symlink check before `stat()` in permissions CLI

---

## [0.6.0] - 2026-02-15

### Added

#### User-Level Memento Storage (#3)

- Mementos stored at `~/.claude/memento/` (user-level, branch-independent)
- Project namespacing with `{project}--{slug}.md` filenames
- Auto-detected `project:` frontmatter block (name, path, repo, branch)
- List filtering: defaults to current project, `--all` for all projects,
  `--project <name>` for a specific project
- Completed mementos archived to `~/.claude/memento/.completed/`

#### Project-Level Permissions (#6, #9)

- Common development commands run without permission prompts
- Destructive operations still require confirmation
- Added Edit, Write, and NotebookEdit to allowed tools

### Changed

- Migrated from monorepo to standalone repository (#1)
- Adopted marketplace-centric distribution strategy (#2)
- Replaced custom YAML frontmatter parser with PyYAML `safe_load`

### Security

- Atomic file writes via tempfile + `os.replace` with 0o600 permissions
- Path containment validation with symlink rejection
- YAML injection prevention via `| tojson` in Jinja2 templates
- Regex backreference injection prevention via lambda replacements
- Git URL credential sanitization across all URL schemes
- Directory permissions enforced via `os.chmod(0o700)` after `mkdir`
- Input validation: slug format/length, project name, JSON size limits

---

## [0.2.0] - 2025-11-05

### Added

#### New `/aida` Command Dispatcher

- Unified command interface for all AIDA functionality
- 8 subcommands: config, status, doctor, upgrade, feedback, bug, feature-request, help
- Skill-based architecture with `aida-dispatch` skill

#### Smart Configuration System

- `/aida config` - Intelligent configuration menu with state detection
- Auto-detects installation state (global/project)
- Context-aware menu options (shows only relevant choices)
- Handles both initial setup AND updates
- "View current configuration" option

#### YAML-Based Configuration (Major Innovation)

- Auto-detection of 90% of project facts
- Single source of truth in `.claude/aida-project-context.yml`
- Detects: VCS (Git, worktrees, remotes), files (README, LICENSE, etc.), languages, tools
- Infers: project type, team size, documentation level
- **Massive question reduction: 22 questions → 2 questions!**

#### New Diagnostic Commands

- `/aida status` - Show installation and configuration status
- `/aida doctor` - Comprehensive health check with fix suggestions
- `/aida upgrade` - Check for updates and show upgrade instructions

#### Project Context Skill

- Auto-generated from YAML configuration
- Provides project-specific facts to Claude
- Updates automatically when config changes

### Changed

#### Architecture

- Migrated from `aida-core` skill to `aida-dispatch` skill
- Command dispatcher delegates to skill (cleaner separation)
- Scripts use YAML config instead of complex conditional logic

#### Configuration Flow

- Replaced questionnaire conditionals with fact detection
- Configuration saved to YAML before asking questions
- Skills rendered from YAML (not from questionnaire responses)

### Improved

- **User Experience**: Fewer questions, smarter defaults
- **Transparency**: Config file is human-readable YAML
- **Idempotency**: Can run config multiple times safely
- **Error Handling**: Better error messages with actionable suggestions
- **Documentation**: Comprehensive references and architecture docs

### Technical

#### New Scripts

- `scripts/detect.py` - Detect installation state
- Enhanced `scripts/configure.py` - YAML-based configuration
- Enhanced fact detection functions

#### New Utilities

- `utils/files.py` - Added `write_yaml()` function
- Enhanced `detect_project_info()` with structured schema
- New `detect_vcs_info()` and `detect_files()` functions

#### New Reference Documentation

- `references/config-driven-approach.md` - Architecture guide
- `references/project-facts.md` - Comprehensive fact taxonomy
- `docs/architecture/adr/007-yaml-config-single-source-truth.md` - ADR

### Fixed

- N/A (initial release of dispatcher)

### Deprecated

- Old `aida-core` skill (replaced by `aida-dispatch`)

### Security

- Validates YAML file sizes (max 1MB)
- Validates JSON payloads (max 1MB, max depth 10)
- Path validation prevents system directory access
- Template variable validation prevents injection

---

## [0.1.8] - 2025-11-04

### Previous Release

- Initial plugin structure
- Basic install/configure scripts
- Foundation utilities

See git history for details on versions prior to 0.2.0.

---

[0.7.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.7.0
[0.6.1]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.6.1
[0.6.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.6.0
[0.2.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.2.0
[0.1.8]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.1.8
