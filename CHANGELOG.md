---
type: changelog
title: "AIDA Core Plugin Changelog"
---

# Changelog

All notable changes to AIDA Core Plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-04-21

### Added

#### Marketplace Sync Skill

- New `/aida marketplace sync` command to detect plugin version drift
  and resolve transitive dependency trees
- Reads `dependencies` field from each plugin's `plugin.json` (existing
  documented schema, now implemented)
- Builds full dependency graph with topological sort and cycle detection
- Compares installed versions against marketplace availability
- Reports drift table with dependency satisfaction status
- `/aida marketplace sync --apply` to update outdated plugins in
  dependency order
- `/aida marketplace status` for quick summary counts
- Shared `VersionRange` module (`scripts/shared/version.py`) using
  `packaging.version.Version` with `^`, `~`, `>=`, `=` operators
- 133+ unit tests and integration tests

---

## [1.4.0] - 2026-04-16

### Added

#### Expert Registry Skill

- New `/aida expert` command family for managing expert agents
- Expert activation at project and global scopes with layered
  resolution (project overrides global)
- Named panel compositions for grouped expert workflows
  (code review, plan grading)
- `expert-role` frontmatter field on agents (`core`, `domain`, `qa`)
  for role-based filtering
- Commands: `list`, `configure`, `panels`, `panel create`,
  `panel remove`
- Two-phase API following ADR-010 pattern
- Project config schema bumped to v0.3.0 with `experts` section
- Post-configuration nudge when expert agents are detected
- 19 new unit tests (11 registry, 8 panels)

#### Version & Changelog CI check

- Added `.github/workflows/version-check.yml` that runs on every PR to
  `main` and fails the build if `.claude-plugin/plugin.json` version
  was not bumped or if `CHANGELOG.md` lacks a matching
  `## [<version>] - YYYY-MM-DD` entry
- Enforces semver bump direction (head version must be greater than base)
- Intent: every change — including typo fixes — updates the version so
  the release history stays aligned with the code, even when a version
  is not separately tagged

---

## [1.2.1] - 2026-04-16

### Fixed

#### Replace pinned model versions with family aliases (#56)

- Replaced version-pinned model identifiers (`claude-opus-4-6`,
  `claude-sonnet-4-6`, `claude-haiku-4-5`) with family aliases (`opus`,
  `sonnet`, `haiku`) across knowledge docs, reference schemas, and tests
- Ensures model references stay valid as new Claude versions ship without
  requiring downstream doc updates

---

## [1.2.0] - 2026-03-18

### Added

#### `/aida about` command and version in help text (#51)

- Added `/aida about` command to display plugin version, author, and
  repository from `plugin.json`
- Updated `/aida help` to include version footer
- Reorganized help text "Info" section with `help`, `about`, `status`

---

## [1.1.5] - 2026-03-18

### Fixed

#### Generated SKILL.md has multiple consecutive blank lines (#49)

- Added `trim_blocks`, `lstrip_blocks`, and `keep_trailing_newline`
  to `template_renderer.py` SandboxedEnvironment — this was the
  actual production renderer used by `configure.py`, which lacked
  the whitespace settings present in `shared/utils.py`
- Added post-processing safety net in `render_skill_directory()` to
  collapse 3+ consecutive newlines to a single blank line
- Added 5 tests using the production SandboxedEnvironment renderer
  covering all-true, all-false, and mixed (marketplace-like) inputs

---

## [1.1.4] - 2026-03-18

### Fixed

#### Scripts invoked with bare python3 instead of AIDA venv (#47)

- Updated all reference docs to invoke scripts via
  `~/.aida/venv/bin/python3` instead of bare `python3`
- Fixed Makefile `lint-frontmatter` target to use `$(VENV_BIN)/python3`
- Updated troubleshooting docs to reference venv Python path
- Affected files: `config.md`, `diagnostics.md`, `feedback.md`,
  `permissions-workflow.md`, `troubleshooting.md`, `Makefile`

---

## [1.1.3] - 2026-03-18

### Fixed

#### Config bugs: hardcoded version and missing project marker (#45)

- Replaced hardcoded `AIDA_VERSION = "0.7.0"` with dynamic version
  read from `plugin.json`, so `aida-project-context.yml` reflects
  the actual plugin version
- Added call to `render_aida_project_marker()` at the end of the
  configure flow, writing `.claude/aida.yml` so `detect.py` correctly
  reports `project_configured: true` after configuration

---

## [1.1.2] - 2026-03-18

### Fixed

#### Generated project-context SKILL.md fails markdown linting (#41)

- Changed 9 `'None'` string fallbacks to `''` in `configure.py` so
  Jinja2 conditionals correctly skip missing values
- Fixed all `{% if has_xxx %}` boolean checks to use
  `{% if has_xxx == 'true' %}` since values are strings
- Removed `| join()` and `[0]` indexing on string values that were
  incorrectly treated as lists
- Restructured template whitespace control to eliminate MD012
  (multiple blank lines) and MD032 (blanks around lists)
- Changed footer emphasis lines to HTML comments (fixes MD036)
- Fixed `tools` default to handle empty strings
- Added 19 unit tests for template rendering

---

## [1.1.1] - 2026-03-18

### Fixed

#### Missing `_paths` import in install.py (#42)

- Added `import _paths` to `install.py` before `from utils import`
  block, fixing `ModuleNotFoundError` when invoked via `/aida config`
  → "Update global preferences"

### Changed

#### Dev tooling uses AIDA-managed venv (#42)

- Added `requirements-dev.txt` for dev dependencies (pytest, ruff,
  yamllint)
- Makefile targets now use `~/.aida/venv/bin/` for all Python tools
- `make install` installs both runtime and dev deps into the venv
- Updated CLAUDE.md with setup instructions

---

## [1.1.0] - 2026-03-05

### Added

#### AIDA-managed Virtual Environment (#34)

- Bootstrap module (`scripts/shared/bootstrap.py`) that lazily creates
  and maintains a virtual environment at `~/.aida/venv/`
- Unified dependency management -- no manual `pip install` required
- Stamp file tracking to skip reinstall when dependencies haven't changed
- Venv health check in `/aida doctor`
- Optional AIDA bootstrap integration for skill creation flow
- Standardized `_paths.py` across all 8 skills

### Removed

- Ad-hoc "Install with: pip install ..." error messages from 6 scripts

## [1.0.0] - 2026-02-24

### Added

#### Plugin Scaffolding Skill (#23)

- Two-phase API for creating new plugins from templates
- Interactive setup with marketplace configuration

#### Plugin Update Skill (#27)

- `/aida plugin update` for standards migration
- Guides plugins through convention changes

### Changed

#### Decompose claude-code-management into Focused Skills (#31)

- Extracted `agent-manager`, `skill-manager`, `plugin-manager`,
  `hook-manager`, and `claude-md-manager` as standalone skills
- Shared logic moved to `extension_utils` module
- Standardized validate response shapes and default operations
- Replaced hand-rolled YAML parser with PyYAML
- Added `operation` key to list responses

#### Merge aida-dispatch into aida Skill (#24)

- Unified `/aida` routing into a single `aida` skill
- Removed `aida-dispatch` as a separate skill

#### Updated Knowledge Base (#31)

- Refreshed all 10 claude-code-expert knowledge files with current
  Claude Code capabilities

### Fixed

- Short-circuit permissions flow when no plugin recommendations
  exist (#28)

---

## [0.8.0] - 2026-02-23

### Changed

#### Merge Commands into Skills (#19)

- Eliminated "Command" as a separate extension type, aligning with Anthropic's
  upstream merge of commands into skills in Claude Code
- Migrated `commands/aida.md` to `skills/aida/SKILL.md` with `user-invocable: true`
  frontmatter field
- Removed `commands/` directory entirely
- Updated `.frontmatter-schema.json`: removed `command` from type enum, added
  skill-specific fields (`user-invocable`, `argument-hint`, `allowed-tools`,
  `disable-model-invocation`)
- Removed `command` from `COMPONENT_TYPES` in Python extension management code
- Removed command template from `skills/claude-code-management/templates/`
- Updated extension taxonomy from WHO/WHAT/HOW/CONTEXT to WHO/HOW/CONTEXT
  (Subagents/Skills/Knowledge)

#### Knowledge Documentation Rewrite

- Rewrote `extension-types.md` with updated decision tree (no Command branch)
- Rewrote `framework-design-principles.md` removing Command sections
- Updated `design-patterns.md`, `plugin-development.md`, `claude-md-files.md`,
  and `hooks.md` to reflect skills-only taxonomy
- Updated `schemas.md` with skill-specific field documentation and examples

#### User-Facing Documentation Updates

- Removed `docs/HOWTO_CREATE_COMMAND.md`
- Updated all HOWTO guides, Getting Started, Install Guide, Development Guide,
  Examples, and Architecture docs
- Updated C4 container and context diagrams (merged Commands container into Skills)
- Updated CI workflow, CODEOWNERS, and integration test scripts

### Fixed

- Fixed agent `model` frontmatter using invalid `claude-sonnet-4.5` model ID;
  changed to `sonnet` alias which resolves to latest Sonnet at runtime

---

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

[1.5.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.5.0
[1.4.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.4.0
[1.2.1]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.2.1
[1.2.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.2.0
[1.1.1]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.1.1
[1.1.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.1.0
[1.0.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v1.0.0
[0.8.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.8.0
[0.7.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.7.0
[0.6.1]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.6.1
[0.6.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.6.0
[0.2.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.2.0
[0.1.8]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.1.8
