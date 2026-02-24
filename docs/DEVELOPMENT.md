---
type: documentation
title: "Development Guide"
description: "For contributors and developers working on AIDA"
audience: contributors
---

# AIDA Core Plugin - Development Guide

## For contributors and developers working on AIDA

This guide covers development setup, code organization, testing, and contribution workflow.

## Table of Contents

- [Development Setup](#development-setup)
- [Repository Structure](#repository-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Adding Features](#adding-features)
- [Debugging](#debugging)
- [Release Process](#release-process)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- **Python**: 3.8 or higher
- **Git**: For version control
- **gh CLI**: For testing feedback system
- **Claude Code**: For testing the plugin

**Check versions**:

```bash
python3 --version  # 3.8+
git --version
gh --version
```

### Clone Repository

```bash
# Clone the aida-core-plugin repository
git clone git@github.com:oakensoul/aida-core-plugin.git
cd aida-core-plugin

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # (planned)
```

### Set Up Local Testing

```bash
# Create test Claude directory
mkdir -p ~/.claude-test/

# Set environment variable for testing
export CLAUDE_DIR=~/.claude-test/

# Run installation script in test mode
python scripts/install.py
```

## Repository Structure

```text
packages/aida-core-plugin/
├── .claude-plugin/               # Plugin metadata (planned)
│   └── plugin.json
├── skills/                      # /aida skills
│   ├── aida/                   # /aida skill - routing, scripts, references, templates
│   └── [more skills]
├── scripts/                      # Python scripts
│   ├── install.py               # Installation wizard
│   ├── configure.py             # Configuration wizard (planned)
│   ├── feedback.py              # GitHub feedback
│   └── utils/                   # Utilities module
│       ├── __init__.py          # Public API
│       ├── version.py           # Version checking
│       ├── paths.py             # Path resolution
│       ├── files.py             # File operations
│       ├── questionnaire.py     # Interactive Q&A
│       ├── inference.py         # Project detection
│       ├── template_renderer.py # Jinja2 rendering
│       └── errors.py            # Error classes
├── templates/                    # Jinja2 templates
│   ├── blueprints/              # Skill templates
│   │   └── user-context/
│   │       └── SKILL.md.jinja2
│   └── questionnaires/          # YAML questionnaires
│       ├── install.yml
│       └── configure.yml
├── tests/                       # Test suite
│   ├── test_utils.py
│   ├── test_feedback.py
│   └── test_install.py          # (planned)
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── USER_GUIDE_INSTALL.md
│   ├── USER_GUIDE_CONFIGURE.md
│   ├── DEVELOPMENT.md           # This file
│   ├── API.md
│   └── architecture/
│       ├── c4/                  # C4 diagrams
│       └── adr/                 # Architecture decisions
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies (planned)
├── README.md                    # Main documentation
└── LICENSE                      # License file
```

### Key Directories

**scripts/**: Main Python code

- Entry points (install.py, feedback.py)
- Utils module (shared functionality)

**templates/**: Jinja2 templates and YAML questionnaires

- blueprints/: Skill generation templates
- questionnaires/: Question definitions

**tests/**: Test suite

- Unit tests for utils module
- Integration tests for scripts
- End-to-end tests (planned)

**docs/**: Comprehensive documentation

- User guides
- Architecture documentation
- API reference
- ADRs (Architecture Decision Records)

## Development Workflow

### Creating a Feature Branch

```bash
# Ensure you're up to date
git checkout main
git pull

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ...

# Commit with descriptive message
git add .
git commit -m "feat: add new questionnaire validation"

# Push to remote
git push origin feature/your-feature-name

# Open pull request on GitHub
```

### Commit Message Convention

Follow conventional commits format:

```text
type(scope): short description

Longer description if needed.

Fixes #123
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:

```text
feat(questionnaire): add multiline question type
fix(install): handle existing directory gracefully
docs(api): document template_renderer functions
test(utils): add tests for path resolution
```

### Running Scripts Locally

```bash
# Test installation script
python scripts/install.py

# Test feedback script
python scripts/feedback.py bug

# Test with specific Python version
python3.8 scripts/install.py
python3.11 scripts/install.py
```

### Using Development Environment

```bash
# Set test environment
export CLAUDE_DIR=~/.claude-test/

# Run script (uses test directory)
python scripts/install.py

# Check results
ls ~/.claude-test/skills/
cat ~/.claude-test/settings.json
```

## Testing

### Running Tests

```bash
cd packages/aida-core-plugin

# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run with coverage
pytest --cov=scripts/utils --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_utils.py::test_check_python_version
```

### Writing Tests

#### Unit Test Example

```python
# tests/test_paths.py
import pytest
from pathlib import Path
from scripts.utils import get_claude_dir, ensure_directory

def test_get_claude_dir():
    """Test getting Claude directory"""
    result = get_claude_dir()
    assert isinstance(result, Path)
    assert result.name == ".claude"

def test_ensure_directory(tmp_path):
    """Test directory creation"""
    test_dir = tmp_path / "test" / "nested"
    result = ensure_directory(test_dir)
    assert result.exists()
    assert result.is_dir()
```

#### Integration Test Example

```python
# tests/test_install.py
import pytest
from pathlib import Path
from scripts.install import main

def test_full_installation(tmp_path, monkeypatch):
    """Test complete installation flow"""
    # Set up test environment
    monkeypatch.setenv("CLAUDE_DIR", str(tmp_path))

    # Mock questionnaire responses
    responses = {
        "coding_standards": "PEP 8",
        "work_hours": "Flexible",
        # ...
    }
    monkeypatch.setattr("scripts.install.run_questionnaire", lambda _: responses)

    # Run installation
    exit_code = main()

    # Verify results
    assert exit_code == 0
    assert (tmp_path / "skills/user-context/SKILL.md").exists()
    assert (tmp_path / "settings.json").exists()
```

### Test Coverage

Aim for:

- **Utils module**: > 90% coverage
- **Scripts**: > 80% coverage
- **Integration tests**: Major workflows covered

## Code Style

### Python Style Guide

Follow **PEP 8** with these specifics:

**Line Length**: 100 characters (slightly relaxed from 79)

**Imports**:

```python
# Standard library
import sys
from pathlib import Path
from typing import Dict, Any

# Third-party
import jinja2
import yaml

# Local
from .errors import AidaError
from .paths import get_claude_dir
```

**Type Hints**:

```python
def render_template(
    template_path: Path,
    variables: Dict[str, Any]
) -> str:
    """Render Jinja2 template with variables."""
    # ...
```

**Docstrings** (Google style):

```python
def ensure_directory(path: Path) -> Path:
    """Create directory if it doesn't exist.

    Args:
        path: Directory path to create

    Returns:
        The created (or existing) directory path

    Raises:
        FileOperationError: If directory cannot be created
    """
    # ...
```

### Formatting

Use **Black** for automatic formatting:

```bash
# Format all Python files
black scripts/ tests/

# Check without modifying
black --check scripts/ tests/
```

### Linting

Use **Flake8** for linting:

```bash
# Lint all files
flake8 scripts/ tests/

# With specific config
flake8 --max-line-length=100 scripts/
```

### Type Checking

Use **mypy** for type checking:

```bash
# Type check utils module
mypy scripts/utils/

# Strict mode
mypy --strict scripts/utils/
```

## Adding Features

### Adding a New Utility Function

**1. Add to appropriate utils/ module**:

```python
# scripts/utils/paths.py
def get_aida_plugin_dir() -> Path:
    """Get AIDA plugin directory.

    Returns:
        Path to ~/.claude/plugins/aida-core/
    """
    return get_claude_dir() / "plugins/aida-core"
```

**2. Export in \_\_init\_\_.py**:

```python
# scripts/utils/__init__.py
from .paths import (
    get_claude_dir,
    get_aida_plugin_dir,  # Add here
    # ...
)

__all__ = [
    "get_claude_dir",
    "get_aida_plugin_dir",  # And here
    # ...
]
```

**3. Add tests**:

```python
# tests/test_paths.py
def test_get_aida_plugin_dir():
    result = get_aida_plugin_dir()
    assert result.name == "aida-core"
```

**4. Update API documentation**:

Add the new function to docs/API.md with proper documentation including parameters,
return values, and usage examples.

### Adding a New Skill

**1. Create skill directory and SKILL.md**:

```markdown
<!-- skills/doctor/SKILL.md -->
---
type: skill
name: doctor
description: Run health check and diagnostics
version: 0.1.0
tags:
  - core
  - diagnostics
---

# /aida doctor

Run health check and diagnostics.

## Activation

This skill activates when the user runs `/aida doctor`.

## What It Checks

- Python version (>= 3.8)
- Directory structure
- File permissions
- Skill syntax
- settings.json validity

## Output

Shows checkmarks (✓) for passing checks, errors (✗) for failures.
```

**2. Create Python script** (if needed):

```python
# scripts/doctor.py
from utils import (
    check_python_version,
    get_claude_dir,
    file_exists,
)

def main() -> int:
    print("Running AIDA health check...\n")

    # Check Python version
    try:
        check_python_version()
        print("✓ Python version compatible")
    except VersionError as e:
        print(f"✗ {e}")
        return 1

    # Check directories
    claude_dir = get_claude_dir()
    if claude_dir.exists():
        print(f"✓ Claude directory exists: {claude_dir}")
    else:
        print(f"✗ Claude directory not found: {claude_dir}")
        return 1

    # ... more checks

    print("\nAll checks passed! ✓")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**3. Register in dispatch skill**:

Update `skills/aida/SKILL.md` to route the new subcommand
to your skill.

### Adding a New Question to Questionnaire

**Edit questionnaire YAML**:

```yaml
# templates/questionnaires/install.yml
questions:
  # ... existing questions

  - id: preferred_editor
    question: "What is your preferred code editor?"
    type: choice
    options:
      - "VS Code"
      - "Vim/Neovim"
      - "IntelliJ IDEA"
      - "Emacs"
      - "Other"
    default: "VS Code"
    help: "This helps AIDA provide editor-specific suggestions"
```

**Update template to use new variable**:

```jinja2
<!-- templates/blueprints/user-context/SKILL.md.jinja2 -->
## Preferred Editor

{{ preferred_editor }}
```

## Debugging

### Debug Mode

Enable verbose logging:

```bash
export AIDA_DEBUG=1
python scripts/install.py
```

### Python Debugger

Use `pdb`:

```python
# Add to code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Debugging Tests

```bash
# Run with pdb on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Print output (bypass capture)
pytest -s
```

### Common Issues

**Import errors**:

```python
# Ensure PYTHONPATH includes scripts/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/scripts"
```

**Template not found**:

```python
# Check template paths are relative to script
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"
```

## Release Process

### Version Bumping

**Update version in**:

- `scripts/utils/__init__.py` (`__version__`)
- `plugin.json` (planned)
- `CHANGELOG.md`

### Creating a Release

```bash
# 1. Update version
vim scripts/utils/__init__.py  # __version__ = "0.2.0"

# 2. Update CHANGELOG
vim CHANGELOG.md

# 3. Commit
git add .
git commit -m "chore: bump version to 0.2.0"

# 4. Tag
git tag -a v0.2.0 -m "Release v0.2.0"

# 5. Push
git push origin main --tags
```

### Publishing

See monorepo `scripts/publish.sh` for publishing to separate repositories.

## Contributing

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:

   ```bash
   git clone git@github.com:YOUR-USERNAME/aida-development.git
   ```

3. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature
   ```

4. **Make your changes** and add tests
5. **Run tests**: `pytest`
6. **Commit**: Follow commit conventions
7. **Push**: `git push origin feature/your-feature`
8. **Open Pull Request** on GitHub

### Pull Request Guidelines

**Before submitting**:

- ✅ All tests pass
- ✅ Code formatted with Black
- ✅ Linting passes (Flake8)
- ✅ Type checking passes (mypy)
- ✅ Documentation updated
- ✅ CHANGELOG.md updated (if applicable)

**PR Description should include**:

- What changed
- Why it changed
- How to test it
- Screenshots (if UI changes)
- Related issues (`Fixes #123`)

### Code Review Process

1. Maintainer reviews PR
2. Feedback provided (if needed)
3. Author addresses feedback
4. Maintainer approves
5. PR merged to main

### Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: Use `/aida bug` or create an issue
- **Features**: Use `/aida feature-request`

## Resources

- **[Architecture Documentation](ARCHITECTURE.md)**: System design
- **[API Reference](API.md)**: Python utilities API
- **[ADRs](architecture/adr/)**: Design decisions
- **[User Guides](USER_GUIDE_INSTALL.md)**: Installation and configuration

---

**Ready to contribute?** Check out [good first issues](https://github.com/oakensoul/aida-core-plugin/labels/good-first-issue)
