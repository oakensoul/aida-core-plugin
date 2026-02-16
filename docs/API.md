---
type: documentation
title: "API Reference"
description: "Complete API documentation for AIDA Python utilities module"
audience: developers
---

# AIDA Core Plugin - API Reference

## Complete API documentation for AIDA Python utilities module

This document provides detailed API reference for all public functions, classes, and modules in
AIDA's utilities package.

## Table of Contents

- [Overview](#overview)
- [version Module](#version-module)
- [paths Module](#paths-module)
- [files Module](#files-module)
- [questionnaire Module](#questionnaire-module)
- [inference Module](#inference-module)
- [template_renderer Module](#template_renderer-module)
- [errors Module](#errors-module)
- [Usage Examples](#usage-examples)

## Overview

The AIDA utilities module (`scripts/utils/`) provides shared functionality for all AIDA scripts.

### Importing

```python
# Import entire API
from utils import *

# Import specific functions
from utils import (
    check_python_version,
    get_claude_dir,
    read_json,
    run_questionnaire,
    render_skill_directory,
)

# Import specific modules
from utils import version, paths, files
```

### Module Structure

```text
utils/
├── __init__.py          # Public API
├── version.py           # Python version checking
├── paths.py             # Path resolution
├── files.py             # File operations
├── questionnaire.py     # Interactive questions
├── inference.py         # Project detection
├── template_renderer.py # Jinja2 rendering
└── errors.py            # Error classes
```

---

## version Module

**Purpose**: Python version checking and validation

### Constants

#### `MIN_PYTHON_VERSION`

Minimum required Python version tuple.

```python
MIN_PYTHON_VERSION: tuple[int, int] = (3, 8)
```

### Functions

#### `check_python_version() -> None`

Check if current Python version meets minimum requirement.

**Raises**:

- `VersionError`: If Python version < 3.8

**Example**:

```python
from utils import check_python_version, VersionError

try:
    check_python_version()
    print("Python version OK")
except VersionError as e:
    print(f"Error: {e}")
    sys.exit(1)
```

#### `get_python_version() -> tuple[int, int, int]`

Get current Python version as tuple.

**Returns**: Tuple of `(major, minor, patch)` (e.g., `(3, 11, 5)`)

**Example**:

```python
from utils import get_python_version

version = get_python_version()
print(f"Python {version[0]}.{version[1]}.{version[2]}")
# Output: Python 3.11.5
```

#### `is_compatible_version(version: tuple[int, int]) -> bool`

Check if given version meets minimum requirement.

**Parameters**:

- `version`: Version tuple `(major, minor)`

**Returns**: `True` if compatible, `False` otherwise

**Example**:

```python
from utils import is_compatible_version

if is_compatible_version((3, 7)):
    print("Compatible")  # False
else:
    print("Not compatible")

if is_compatible_version((3, 11)):
    print("Compatible")  # True
```

#### `format_version(version: tuple[int, ...]) -> str`

Format version tuple as string.

**Parameters**:

- `version`: Version tuple (any length)

**Returns**: Formatted string (e.g., `"3.11.5"`)

**Example**:

```python
from utils import format_version

print(format_version((3, 11, 5)))  # "3.11.5"
print(format_version((3, 8)))      # "3.8"
```

---

## paths Module

**Purpose**: Path resolution and directory management

### Functions

#### `get_home_dir() -> Path`

Get user's home directory.

**Returns**: `Path` to home directory (e.g., `/Users/username`)

**Example**:

```python
from utils import get_home_dir

home = get_home_dir()
print(home)  # /Users/username
```

#### `get_claude_dir() -> Path`

Get Claude Code global configuration directory.

**Returns**: `Path` to `~/.claude/`

**Example**:

```python
from utils import get_claude_dir

claude_dir = get_claude_dir()
print(claude_dir)  # /Users/username/.claude
```

#### `get_aida_skills_dir() -> Path`

Get AIDA global skills directory.

**Returns**: `Path` to `~/.claude/skills/`

**Example**:

```python
from utils import get_aida_skills_dir

skills_dir = get_aida_skills_dir()
print(skills_dir)  # /Users/username/.claude/skills
```

#### `get_aida_plugin_dirs() -> list[Path]`

Get all AIDA plugin directories.

**Returns**: List of `Path` objects to plugin directories

**Example**:

```python
from utils import get_aida_plugin_dirs

plugins = get_aida_plugin_dirs()
for plugin_dir in plugins:
    print(plugin_dir)
```

#### `ensure_directory(path: Path) -> Path`

Create directory if it doesn't exist (including parents).

**Parameters**:

- `path`: Directory path to create

**Returns**: The created (or existing) directory `Path`

**Raises**:

- `FileOperationError`: If directory cannot be created

**Example**:

```python
from utils import ensure_directory

skills_dir = ensure_directory(Path.home() / ".claude" / "skills")
print(f"Skills directory: {skills_dir}")
```

#### `resolve_path(path: str) -> Path`

Resolve and expand path (handles `~`, relative paths, symlinks).

**Parameters**:

- `path`: String path to resolve

**Returns**: Absolute `Path` with `~` expanded and symlinks resolved

**Example**:

```python
from utils import resolve_path

path = resolve_path("~/.claude/skills")
print(path)  # /Users/username/.claude/skills

rel_path = resolve_path("../templates")
print(rel_path)  # /full/path/to/templates
```

#### `is_subdirectory(child: Path, parent: Path) -> bool`

Check if child path is subdirectory of parent.

**Parameters**:

- `child`: Potential subdirectory
- `parent`: Potential parent directory

**Returns**: `True` if child is under parent

**Example**:

```python
from utils import is_subdirectory

is_sub = is_subdirectory(
    Path("/home/user/.claude/skills"),
    Path("/home/user/.claude")
)
print(is_sub)  # True
```

#### `get_relative_path(path: Path, base: Path) -> Path`

Get path relative to base directory.

**Parameters**:

- `path`: Absolute path
- `base`: Base directory

**Returns**: Relative path from base to path

**Example**:

```python
from utils import get_relative_path

rel = get_relative_path(
    Path("/home/user/.claude/skills/user-context"),
    Path("/home/user/.claude")
)
print(rel)  # skills/user-context
```

---

## files Module

**Purpose**: File I/O operations

### Functions

#### `read_file(path: Path) -> str`

Read text file contents.

**Parameters**:

- `path`: File path to read

**Returns**: File contents as string

**Raises**:

- `FileOperationError`: If file cannot be read

**Example**:

```python
from utils import read_file

content = read_file(Path("SKILL.md"))
print(content)
```

#### `write_file(path: Path, content: str) -> None`

Write string to text file (creates parent directories).

**Parameters**:

- `path`: File path to write
- `content`: String content to write

**Raises**:

- `FileOperationError`: If file cannot be written

**Example**:

```python
from utils import write_file

write_file(
    Path("~/.claude/skills/test/SKILL.md"),
    "# Test Skill\n\nContent here."
)
```

#### `read_json(path: Path) -> dict`

Read and parse JSON file.

**Parameters**:

- `path`: JSON file path

**Returns**: Parsed JSON as dictionary

**Raises**:

- `FileOperationError`: If file cannot be read or parsed

**Example**:

```python
from utils import read_json

settings = read_json(Path("~/.claude/settings.json"))
print(settings["enabledPlugins"])
```

#### `write_json(path: Path, data: dict, indent: int = 2) -> None`

Write dictionary to JSON file with formatting.

**Parameters**:

- `path`: JSON file path
- `data`: Dictionary to write
- `indent`: Indentation spaces (default: 2)

**Raises**:

- `FileOperationError`: If file cannot be written

**Example**:

```python
from utils import write_json

data = {
    "enabledPlugins": {
        "aida-core": True
    }
}
write_json(Path("~/.claude/settings.json"), data)
```

#### `update_json(path: Path, updates: dict) -> None`

Merge updates into existing JSON file.

**Parameters**:

- `path`: JSON file path (created if doesn't exist)
- `updates`: Dictionary to merge into existing

**Behavior**:

- Creates file with `{}` if doesn't exist
- Deep merges updates into existing
- Preserves existing keys not in updates

**Raises**:

- `FileOperationError`: If file cannot be read/written

**Example**:

```python
from utils import update_json

# Add plugin without overwriting other settings
updates = {
    "enabledPlugins": {
        "aida-core": True
    }
}
update_json(Path("~/.claude/settings.json"), updates)
```

#### `copy_template(src: Path, dst: Path) -> None`

Copy file from src to dst (creates parent directories).

**Parameters**:

- `src`: Source file path
- `dst`: Destination file path

**Raises**:

- `FileOperationError`: If copy fails

**Example**:

```python
from utils import copy_template

copy_template(
    Path("templates/SKILL.md"),
    Path("~/.claude/skills/test/SKILL.md")
)
```

#### `file_exists(path: Path) -> bool`

Check if file exists.

**Parameters**:

- `path`: File path to check

**Returns**: `True` if file exists

**Example**:

```python
from utils import file_exists

if file_exists(Path("~/.claude/settings.json")):
    print("Settings file found")
```

#### `directory_exists(path: Path) -> bool`

Check if directory exists.

**Parameters**:

- `path`: Directory path to check

**Returns**: `True` if directory exists

**Example**:

```python
from utils import directory_exists

if directory_exists(Path("~/.claude/skills")):
    print("Skills directory exists")
```

---

## questionnaire Module

**Purpose**: Interactive user questionnaires

### Data Types

#### Question Type

```python
{
    "id": str,              # Unique identifier
    "question": str,        # Question text
    "type": str,            # "text", "multiline", "choice", "confirm"
    "default": Any,         # Default value (optional)
    "help": str,            # Help text (optional)
    "options": list[str],   # For "choice" type
    "required": bool,       # Required (default: True)
}
```

### Functions

#### `run_questionnaire(template_path: Path) -> dict[str, Any]`

Run interactive questionnaire from YAML definition.

**Parameters**:

- `template_path`: Path to questionnaire YAML file

**Returns**: Dictionary mapping question IDs to user responses

**Raises**:

- `ConfigurationError`: If YAML invalid or questions malformed
- `KeyboardInterrupt`: If user cancels (Ctrl+C)

**Example**:

```python
from utils import run_questionnaire

responses = run_questionnaire(Path("templates/questionnaires/install.yml"))

print(responses["coding_standards"])  # "PEP 8"
print(responses["work_hours"])        # "Flexible hours"
```

#### `load_questionnaire(path: Path) -> dict`

Load YAML questionnaire definition without running it.

**Parameters**:

- `path`: Path to questionnaire YAML file

**Returns**: Parsed questionnaire definition dictionary

**Raises**:

- `FileOperationError`: If file cannot be read
- `ConfigurationError`: If YAML invalid

**Example**:

```python
from utils import load_questionnaire

questionnaire = load_questionnaire(Path("install.yml"))
questions = questionnaire["questions"]
print(f"Found {len(questions)} questions")
```

#### `filter_questions(questions: list[dict], condition: Callable) -> list[dict]`

Filter questions based on condition function.

**Parameters**:

- `questions`: List of question dictionaries
- `condition`: Function that takes question and returns bool

**Returns**: Filtered list of questions

**Example**:

```python
from utils import load_questionnaire, filter_questions

questionnaire = load_questionnaire(Path("install.yml"))
required = filter_questions(
    questionnaire["questions"],
    lambda q: q.get("required", True)
)
print(f"{len(required)} required questions")
```

#### `questions_to_dict(responses: list[tuple[str, Any]]) -> dict[str, Any]`

Convert list of (id, answer) tuples to dictionary.

**Parameters**:

- `responses`: List of tuples `[(id, answer), ...]`

**Returns**: Dictionary mapping IDs to answers

**Example**:

```python
from utils import questions_to_dict

responses = [
    ("coding_standards", "PEP 8"),
    ("work_hours", "Flexible"),
]
result = questions_to_dict(responses)
print(result["coding_standards"])  # "PEP 8"
```

---

## inference Module

**Purpose**: Smart project detection

### Functions

#### `infer_preferences(project_path: Path) -> dict[str, Any]`

Detect all project characteristics.

**Parameters**:

- `project_path`: Path to project directory

**Returns**: Dictionary with detected information:

```python
{
    "languages": ["Python", "JavaScript"],
    "frameworks": ["Django", "React"],
    "tools": ["Docker", "pytest"],
    "project_type": "web-application-fullstack",
    "testing": "pytest",
    "ci_cd": "github-actions",
}
```

**Example**:

```python
from utils import infer_preferences

detected = infer_preferences(Path.cwd())
print(f"Detected language: {detected['languages'][0]}")
print(f"Project type: {detected['project_type']}")
```

#### `detect_languages(path: Path) -> list[str]`

Detect programming languages used in project.

**Parameters**:

- `path`: Project directory path

**Returns**: List of language names (e.g., `["Python", "JavaScript"]`)

**Detection Method**:

- File extensions (`.py`, `.js`, etc.)
- Config files (`package.json`, `pyproject.toml`)

**Example**:

```python
from utils import detect_languages

languages = detect_languages(Path.cwd())
print(f"Languages: {', '.join(languages)}")
```

#### `detect_tools(path: Path) -> list[str]`

Detect development tools used in project.

**Parameters**:

- `path`: Project directory path

**Returns**: List of tool names (e.g., `["Docker", "pytest", "webpack"]`)

**Detects**:

- Build tools (Webpack, Vite, etc.)
- Testing frameworks (pytest, Jest, etc.)
- Package managers (npm, pip, etc.)
- Containers (Docker, docker-compose)

**Example**:

```python
from utils import detect_tools

tools = detect_tools(Path.cwd())
if "Docker" in tools:
    print("Docker detected")
```

#### `detect_coding_standards(path: Path) -> list[str]`

Detect linters and formatters configured.

**Parameters**:

- `path`: Project directory path

**Returns**: List of coding standard tools (e.g., `["Black", "ESLint"]`)

**Detects**:

- Config files (`.eslintrc`, `pyproject.toml`, etc.)
- Tool sections in config files

**Example**:

```python
from utils import detect_coding_standards

standards = detect_coding_standards(Path.cwd())
print(f"Coding standards: {', '.join(standards)}")
```

#### `detect_testing_approach(path: Path) -> str`

Detect testing framework and approach.

**Parameters**:

- `path`: Project directory path

**Returns**: Testing approach string (e.g., `"pytest"`, `"Jest"`, `"Mixed"`)

**Example**:

```python
from utils import detect_testing_approach

testing = detect_testing_approach(Path.cwd())
print(f"Testing framework: {testing}")
```

#### `detect_project_type(path: Path) -> str`

Infer high-level project type.

**Parameters**:

- `path`: Project directory path

**Returns**: Project type string:

- `"web-application-frontend"`
- `"web-application-backend"`
- `"web-application-fullstack"`
- `"library"`
- `"cli-tool"`
- `"data-science"`
- `"mobile"`
- `"unknown"`

**Example**:

```python
from utils import detect_project_type

project_type = detect_project_type(Path.cwd())
print(f"Project type: {project_type}")
```

---

## template_renderer Module

**Purpose**: Jinja2 template rendering

### Functions

#### `render_template(template_path: Path, variables: dict[str, Any]) -> str`

Render single Jinja2 template file.

**Parameters**:

- `template_path`: Path to `.jinja2` template file
- `variables`: Dictionary of variables for template

**Returns**: Rendered template as string

**Raises**:

- `FileOperationError`: If template file cannot be read
- `TemplateError`: If template rendering fails

**Example**:

```python
from utils import render_template

result = render_template(
    Path("templates/SKILL.md.jinja2"),
    {
        "skill_name": "test-skill",
        "coding_standards": "PEP 8",
    }
)
print(result)
```

#### `render_filename(filename: str, variables: dict[str, Any]) -> str`

Render filename template (for dynamic filenames).

**Parameters**:

- `filename`: Filename with Jinja2 template syntax
- `variables`: Dictionary of variables

**Returns**: Rendered filename

**Example**:

```python
from utils import render_filename

name = render_filename(
    "{{skill_name}}.md.jinja2",
    {"skill_name": "test-skill"}
)
print(name)  # "test-skill.md.jinja2"
```

#### `render_skill_directory(template_dir: Path, output_dir: Path, variables: dict[str, Any]) -> None`

Recursively render entire directory of templates.

**Parameters**:

- `template_dir`: Source directory with templates
- `output_dir`: Destination directory for rendered files
- `variables`: Dictionary of variables for all templates

**Behavior**:

- Recursively processes all files and subdirectories
- Renders `.jinja2` files and removes extension
- Copies binary files as-is
- Creates output directory if doesn't exist
- Renders filenames if they contain template syntax

**Raises**:

- `FileOperationError`: If template or output cannot be accessed
- `TemplateError`: If template rendering fails

**Example**:

```python
from utils import render_skill_directory

render_skill_directory(
    Path("templates/blueprints/user-context"),
    Path("~/.claude/skills/user-context"),
    {
        "skill_name": "user-context",
        "coding_standards": "PEP 8",
    }
)
```

#### `is_binary_file(path: Path) -> bool`

Check if file is binary (vs text).

**Parameters**:

- `path`: File path to check

**Returns**: `True` if binary file

**Example**:

```python
from utils import is_binary_file

if is_binary_file(Path("logo.png")):
    print("Binary file, will copy as-is")
```

#### `is_template_file(path: Path) -> bool`

Check if file is a Jinja2 template (has `.jinja2` extension).

**Parameters**:

- `path`: File path to check

**Returns**: `True` if template file

**Example**:

```python
from utils import is_template_file

if is_template_file(Path("SKILL.md.jinja2")):
    print("Template file, will render")
```

#### `get_output_filename(template_name: str) -> str`

Remove `.jinja2` extension from filename.

**Parameters**:

- `template_name`: Template filename

**Returns**: Output filename without `.jinja2`

**Example**:

```python
from utils import get_output_filename

output = get_output_filename("SKILL.md.jinja2")
print(output)  # "SKILL.md"
```

---

## errors Module

**Purpose**: Custom exception hierarchy

### Exception Classes

#### `AidaError(Exception)`

Base exception for all AIDA errors.

**Usage**:

```python
from utils import AidaError

raise AidaError("Something went wrong with AIDA")
```

#### `VersionError(AidaError)`

Python version incompatibility error.

**Usage**:

```python
from utils import VersionError

raise VersionError("Python 3.8+ required, found 3.7")
```

#### `PathError(AidaError)`

Invalid or inaccessible path error.

**Usage**:

```python
from utils import PathError

raise PathError(f"Path does not exist: {path}")
```

#### `FileOperationError(AidaError)`

File I/O operation failed.

**Usage**:

```python
from utils import FileOperationError

raise FileOperationError(f"Cannot write to {path}: Permission denied")
```

#### `ConfigurationError(AidaError)`

Invalid or missing configuration.

**Usage**:

```python
from utils import ConfigurationError

raise ConfigurationError("Invalid questionnaire YAML: missing 'questions' key")
```

#### `InstallationError(AidaError)`

Installation process failed.

**Usage**:

```python
from utils import InstallationError

raise InstallationError("Failed to create skills directory")
```

### Error Handling Pattern

```python
from utils import (
    check_python_version,
    VersionError,
    FileOperationError,
    ConfigurationError,
)

try:
    check_python_version()
    # ... other operations
except VersionError as e:
    print(f"Version error: {e}")
    sys.exit(1)
except FileOperationError as e:
    print(f"File error: {e}")
    sys.exit(1)
except ConfigurationError as e:
    print(f"Config error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
```

---

## Usage Examples

### Complete Installation Script

```python
from pathlib import Path
from utils import (
    check_python_version,
    get_claude_dir,
    ensure_directory,
    run_questionnaire,
    render_skill_directory,
    update_json,
    VersionError,
    FileOperationError,
    ConfigurationError,
)

def main() -> int:
    try:
        # Check Python version
        check_python_version()

        # Get directories
        claude_dir = get_claude_dir()
        skills_dir = claude_dir / "skills"

        # Run questionnaire
        responses = run_questionnaire(
            Path("templates/questionnaires/install.yml")
        )

        # Create directories
        ensure_directory(skills_dir / "user-context")

        # Render skills
        render_skill_directory(
            Path("templates/blueprints/user-context"),
            skills_dir / "user-context",
            responses
        )

        # Update settings.json
        settings_path = claude_dir / "settings.json"
        update_json(settings_path, {
            "enabledPlugins": {
                "aida-core": True
            }
        })

        print("✓ Installation complete!")
        return 0

    except VersionError as e:
        print(f"❌ {e}")
        return 1
    except (FileOperationError, ConfigurationError) as e:
        print(f"❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled")
        return 130

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

---

**See Also**:

- [Architecture Documentation](ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)
- [User Guide - Installation](USER_GUIDE_INSTALL.md)
