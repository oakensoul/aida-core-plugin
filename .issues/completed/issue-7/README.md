---
issue: 7
title: "Launch preparedness: documentation, marketing, and code quality review"
status: "OPEN"
created: "2026-02-15"
---

# Issue #7: Launch preparedness: documentation, marketing, and code quality review

**Status**: OPEN
**Labels**: none
**Milestone**: none
**Assignees**: oakensoul

## Description

Before publishing aida-core-plugin to the marketplace for broader adoption, we
need a comprehensive readiness review. This covers user-facing documentation,
marketing/discovery materials, code quality, and overall polish.

## Documentation Review

### User-Facing Docs

- [ ] **README.md** - Clear value proposition, accurate install steps, up-to-date
      command reference, working examples
- [ ] **Getting Started guide** (docs/GETTING_STARTED.md) - End-to-end onboarding
      flow works as documented
- [ ] **Installation guide** (docs/USER_GUIDE_INSTALL.md) - All install methods
      tested and accurate
- [ ] **Configuration guide** (docs/USER_GUIDE_CONFIGURE.md) - Reflects current
      /aida config behavior
- [ ] **How-To guides** - Each guide is complete, tested, and follows consistent
      format:
  - [ ] HOWTO_MEMENTO.md
  - [ ] HOWTO_CREATE_AGENT.md
  - [ ] HOWTO_CREATE_COMMAND.md
  - [ ] HOWTO_CREATE_SKILL.md
  - [ ] HOWTO_HOOKS.md
- [ ] **Examples** (docs/EXAMPLES.md) - Real-world scenarios that actually work
- [ ] **API reference** (docs/API.md) - Accurate and complete

### Architecture and Developer Docs

- [ ] **ARCHITECTURE.md** - Reflects current plugin structure and design
- [ ] **DEVELOPMENT.md** - Contributor setup works, conventions documented
- [ ] **ADRs reviewed and current:**
  - [ ] ADR-001: Skills-first architecture
  - [ ] ADR-002: Python for scripts
  - [ ] ADR-003: Jinja2 templates
  - [ ] ADR-004: YAML questionnaires
  - [ ] ADR-005: Local-first storage
  - [ ] ADR-006: GH CLI feedback
  - [ ] ADR-007: YAML config single source of truth
  - [ ] ADR-008: Marketplace-centric distribution
- [ ] **Missing ADRs identified** - Any architectural decisions made since last
      ADR are documented with new ADRs
- [ ] **C4 diagrams reviewed and up to date:**
  - [ ] Context diagram (docs/architecture/c4/context-diagram.md)
  - [ ] Container diagram (docs/architecture/c4/container-diagram.md)
  - [ ] Component diagram (docs/architecture/c4/component-diagram.md)
- [ ] **Architecture docs reflect current plugin structure**
- [ ] **Extension framework design principles documented accurately**
- [ ] **Extension framework docs** - Accurate for plugin authors

### Changelog and Versioning

- [ ] **CHANGELOG.md** - Exists, covers all releases, follows Keep a Changelog
      format
- [ ] **Version numbers** - Consistent across plugin.json, marketplace.json, docs
- [ ] **LICENSE** - Present and correct (AGPL v3)

## Architecture Review

- [ ] C4 Context diagram reflects current system boundaries and actors
- [ ] C4 Container diagram reflects current component relationships
- [ ] C4 Component diagram reflects current internal structure
- [ ] All ADRs have status (accepted/superseded/deprecated)
- [ ] No architectural decisions are undocumented
- [ ] Architecture diagrams match actual implementation
- [ ] Extension type taxonomy (agents/commands/skills/knowledge) documented
      correctly

## Marketing and Discovery

### Marketplace Listing

- [ ] **marketplace.json** - Description, tags, categories optimized for discovery
- [ ] **Short description** - Compelling, under character limit
- [ ] **Long description** - Covers key features, differentiators, use cases
- [ ] **Screenshots/examples** - If supported, include terminal examples
- [ ] **Tags/keywords** - Comprehensive for searchability

### README as Landing Page

- [ ] Hook/value proposition in first 3 lines
- [ ] 30-second demo is copy-pasteable and works
- [ ] Feature list is scannable and compelling
- [ ] Command reference table is complete and accurate
- [ ] Links to docs all resolve correctly
- [ ] Badges (if applicable) - build status, version, license

### Branding and Messaging

- [ ] Consistent terminology across all docs (AIDA, aida-core, etc.)
- [ ] Personality/tone consistent with AIDA brand
- [ ] No references to internal/development concepts in user-facing content

## Code Quality Review

### Full Code Review

- [ ] **All Python scripts** - Security, error handling, edge cases, type hints
- [ ] **All Markdown extensions** - Frontmatter valid, content accurate, no broken
      references
- [ ] **Templates** - Jinja2 templates render correctly, no missing variables
- [ ] **Plugin manifest** - plugin.json schema complete and valid
- [ ] **Test coverage** - All critical paths tested, no skipped/ignored tests

### Linting and Standards

- [ ] `make lint` passes with zero warnings
- [ ] `make test` passes with zero failures
- [ ] No TODO/FIXME/HACK comments left in shipped code
- [ ] No hardcoded paths, credentials, or personal references
- [ ] No dead code or unused imports

### Security Review

- [ ] No secrets or credentials in codebase
- [ ] No command injection vulnerabilities in scripts
- [ ] File operations use safe path handling
- [ ] Git operations do not expose sensitive data
- [ ] Permissions model is appropriate (no overly broad defaults)

## Operational Readiness

### CI/CD

- [ ] GitHub Actions workflows working (lint, test)
- [ ] Branch protection rules configured
- [ ] Release workflow ready (if applicable)

### Issue Management

- [ ] Issue templates configured
- [ ] Labels set up and consistent
- [ ] Milestones defined for post-launch work

### Support Readiness

- [ ] `/aida bug` workflow tested end-to-end
- [ ] `/aida feature-request` workflow tested
- [ ] `/aida doctor` diagnostics cover common issues
- [ ] Error messages are user-friendly and actionable

## Acceptance Criteria

- [ ] All documentation links resolve and content is accurate
- [ ] Fresh install from marketplace works end-to-end
- [ ] All commands listed in README work as documented
- [ ] Code review completed with no critical findings
- [ ] `make lint` and `make test` pass cleanly
- [ ] Marketplace listing is polished and discoverable
- [ ] No TODO/FIXME items remaining in shipped code

## Work Tracking

- Branch: `chore/7-launch-preparedness`
- Started: 2026-02-15
- Work directory: `issues/in-progress/issue-7/`

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/7)

## Notes

### Changelog and Versioning Audit (2026-02-15)

Findings from initial review:

1. **CHANGELOG missing PR #11 / Issue #4** - Plugin config discovery and
   permissions management is merged but not documented in the 0.6.0 entry
2. **Stale "Unreleased" section** - Planned items for v0.2.1/v0.3.0 are outdated;
   some features already shipped in 0.6.0
3. **No git tags** - Release links at bottom of CHANGELOG.md are dead since no
   tags/releases exist
4. **Version numbers consistent** - plugin.json and marketplace.json both at 0.6.0
