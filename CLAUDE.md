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
├── commands/             # Command definitions (recipes)
│   └── aida.md           # /aida command entry point
├── skills/               # Execution capabilities
│   ├── aida-dispatch/    # Command routing
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
- **Commands**: WHAT - recipes/instructions in `commands/`
- **Skills**: HOW - execution capabilities in `skills/`
- **Knowledge**: CONTEXT - reference material in `knowledge/` subdirs

### File Naming

- Subagents: `agents/{name}/{name}.md` with `knowledge/` subdir
- Commands: `commands/{name}.md`
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
- `commands/aida.md` - Main command entry point
