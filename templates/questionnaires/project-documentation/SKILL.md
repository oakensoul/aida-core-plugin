---
name: project-documentation
description: Helps locate and navigate project documentation efficiently
version: 0.1.0
author: aida-core
tags:
  - project
  - documentation
  - navigation
  - reference
---

# Project Documentation Skill

This skill provides an organized index of project documentation, making it easy to find relevant docs without searching through the entire codebase.

## When to Use

This skill should be invoked when you need to:

- Locate specific documentation (README, architecture docs, API docs, etc.)
- Understand where different types of documentation live in the project
- Find documentation about a specific topic or component
- Navigate the project's documentation structure
- Reference documentation locations for team members

## Supporting Files

### doc-index.md
Comprehensive index of documentation locations:
- README and getting started guides
- Architecture and design documentation
- API documentation and references
- Contributing guidelines
- Testing documentation
- Deployment and operations docs
- User guides and tutorials
- Changelog and release notes

The index provides quick navigation to all project documentation without needing to grep or search through directories.

## Examples

### Finding Architecture Documentation
```
User: "Where can I find the architecture documentation?"

Claude: *Invokes project-documentation skill, reads doc-index.md*
"The architecture documentation is located in docs/architecture.md"
```

### Locating API Documentation
```
User: "How do I learn about the API endpoints?"

Claude: *Invokes project-documentation skill, reads doc-index.md*
"API documentation is available at:
- OpenAPI spec: docs/api/openapi.yaml
- API guide: docs/api/README.md"
```

### Getting Started Resources
```
User: "What documentation should a new contributor read?"

Claude: *Invokes project-documentation skill, reads doc-index.md*
"New contributors should start with:
1. README.md - Project overview and setup
2. CONTRIBUTING.md - Contribution guidelines
3. docs/architecture.md - Architecture overview
4. docs/development.md - Development workflow"
```

## Progressive Disclosure

Like all AIDA skills, this skill's SKILL.md is always available (small token footprint), but the doc-index.md is only loaded when Claude determines documentation navigation is needed.

## Maintenance

Update doc-index.md when:
- New documentation is added
- Documentation is moved or reorganized
- Documentation is deprecated or removed
- Documentation URLs change

Keep the index current so team members can always find what they need.

## Future Enhancement

This skill can be extended with:
- `scripts/find-docs.py` - Programmatic documentation search
- `scripts/validate-docs.py` - Check that documented files exist
- Integration with documentation generators
