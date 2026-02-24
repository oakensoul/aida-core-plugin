---
type: readme
title: AIDA Core Plugin
---

# AIDA Core Plugin

Claude Code plugin providing smart configuration, GitHub integration, and context
management capabilities.

## Project Structure

```text
aida-core-plugin/
├── .claude-plugin/       # Plugin metadata
│   ├── plugin.json       # Required plugin manifest
│   └── marketplace.json  # Marketplace listing
├── agents/               # Subagent definitions
│   ├── aida/             # AIDA assistant subagent
│   └── claude-code-expert/  # Extension design expert
├── skills/               # Process definitions + execution capabilities
│   ├── aida/             # /aida skill - routing, scripts, references, templates
│   ├── claude-code-management/  # Extension CRUD operations
│   └── memento/          # Session persistence
├── tests/                # Python tests
└── docs/                 # Documentation
```

## Development

### Commands

```bash
make lint          # Run all linters (ruff, yamllint, markdownlint)
make test          # Run pytest
make format        # Auto-format Python code
make clean         # Remove build artifacts
```

### Testing

```bash
pytest tests/                    # Run all tests
pytest tests/test_manage.py -v   # Run specific test file
```

## Conventions

### Extension Types (see agents/claude-code-expert/knowledge/)

- **Subagents**: WHO - expertise definitions in `agents/`
- **Skills**: HOW - process definitions + execution capabilities in `skills/`
- **Knowledge**: CONTEXT - reference material in `knowledge/` subdirs

### File Naming

- Subagents: `agents/{name}/{name}.md` with `knowledge/` subdir
- Skills: `skills/{name}/SKILL.md` with `scripts/`, `templates/`, `references/`

### Python Style

- Use ruff for linting and formatting
- Type hints required for public functions
- Scripts in skills use `if __name__ == "__main__":` pattern

### Markdown

- YAML frontmatter required (type, name, description, version)
- Use markdownlint (config in `.markdownlint.json`)
- Line length: 88 characters (matches ruff)

## Key Files

- `agents/claude-code-expert/knowledge/framework-design-principles.md` - Extension architecture reference
- `skills/claude-code-management/SKILL.md` - How extensions are created/managed
- `skills/aida/SKILL.md` - Main skill entry point
