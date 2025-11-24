# Changelog

All notable changes to AIDA Core Plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-05

### Added

**New `/aida` Command Dispatcher**
- Unified command interface for all AIDA functionality
- 8 subcommands: config, status, doctor, upgrade, feedback, bug, feature-request, help
- Skill-based architecture with `aida-dispatch` skill

**Smart Configuration System**
- `/aida config` - Intelligent configuration menu with state detection
- Auto-detects installation state (global/project)
- Context-aware menu options (shows only relevant choices)
- Handles both initial setup AND updates
- "View current configuration" option

**YAML-Based Configuration** (Major Innovation)
- Auto-detection of 90% of project facts
- Single source of truth in `.claude/aida-project-context.yml`
- Detects: VCS (Git, worktrees, remotes), files (README, LICENSE, etc.), languages, tools
- Infers: project type, team size, documentation level
- **Massive question reduction: 22 questions → 2 questions!**

**New Diagnostic Commands**
- `/aida status` - Show installation and configuration status
- `/aida doctor` - Comprehensive health check with fix suggestions
- `/aida upgrade` - Check for updates and show upgrade instructions

**Project Context Skill**
- Auto-generated from YAML configuration
- Provides project-specific facts to Claude
- Updates automatically when config changes

### Changed

**Architecture**
- Migrated from `aida-core` skill to `aida-dispatch` skill
- Command dispatcher delegates to skill (cleaner separation)
- Scripts use YAML config instead of complex conditional logic

**Configuration Flow**
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

**New Scripts**
- `scripts/detect.py` - Detect installation state
- Enhanced `scripts/configure.py` - YAML-based configuration
- Enhanced fact detection functions

**New Utilities**
- `utils/files.py` - Added `write_yaml()` function
- Enhanced `detect_project_info()` with structured schema
- New `detect_vcs_info()` and `detect_files()` functions

**New Reference Documentation**
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

## Unreleased

### Planned for v0.2.1
- [ ] Enhanced language detection (Python, JavaScript, Go, Rust, etc.)
- [ ] Better source directory detection
- [ ] Test directory enumeration
- [ ] CI/CD system-specific detection

### Planned for v0.3.0
- [ ] Memory management system
- [ ] Personal knowledge base
- [ ] Custom command creation
- [ ] Workflow automation

---

[0.2.0]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.2.0
[0.1.8]: https://github.com/oakensoul/aida-core-plugin/releases/tag/v0.1.8
