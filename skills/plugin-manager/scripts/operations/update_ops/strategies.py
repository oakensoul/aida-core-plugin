"""File classification and strategy registry for plugin update.

Maps each scaffolded file to its category, template source,
and default merge strategy. This is the single source of truth
for how the update operation treats each file.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import FileCategory, MergeStrategy


@dataclass(frozen=True)
class FileSpec:
    """Specification for a scaffolded file.

    Attributes:
        path: Relative path from plugin root
        template: Template path relative to scaffold dir
            (None for files with special handling)
        category: File classification
        default_strategy: How to handle during update
        language: None for shared files, "python" or
            "typescript" for language-specific files
        user_overridable: Whether the user can change
            the strategy
    """

    path: str
    template: str | None
    category: FileCategory
    default_strategy: MergeStrategy
    language: str | None = None
    user_overridable: bool = False


# Custom content: never modified by update
_CUSTOM_FILES: list[FileSpec] = [
    FileSpec(
        "CLAUDE.md",
        "shared/claude-md.jinja2",
        FileCategory.CUSTOM,
        MergeStrategy.SKIP,
    ),
    FileSpec(
        "README.md",
        "shared/readme.md.jinja2",
        FileCategory.CUSTOM,
        MergeStrategy.SKIP,
    ),
    FileSpec(
        "LICENSE",
        None,
        FileCategory.CUSTOM,
        MergeStrategy.SKIP,
    ),
]

# AIDA metadata: never modified by update (generator_version
# is updated separately by the patcher, not via template)
_AIDA_METADATA_FILES: list[FileSpec] = [
    FileSpec(
        ".claude-plugin/aida-config.json",
        "shared/aida-config.json.jinja2",
        FileCategory.METADATA,
        MergeStrategy.SKIP,
    ),
]

# Pure boilerplate: safe to overwrite
_BOILERPLATE_SHARED: list[FileSpec] = [
    FileSpec(
        ".markdownlint.json",
        "shared/markdownlint.json.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        user_overridable=True,
    ),
    FileSpec(
        ".yamllint.yml",
        "shared/yamllint.yml.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        user_overridable=True,
    ),
    FileSpec(
        ".frontmatter-schema.json",
        "shared/frontmatter-schema.json.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        user_overridable=True,
    ),
]

_BOILERPLATE_PYTHON: list[FileSpec] = [
    FileSpec(
        ".python-version",
        "python/python-version.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="python",
        user_overridable=True,
    ),
    FileSpec(
        "tests/conftest.py",
        "python/conftest.py.jinja2",
        FileCategory.TEST_SCAFFOLD,
        MergeStrategy.ADD,
        language="python",
        user_overridable=True,
    ),
]

_BOILERPLATE_TYPESCRIPT: list[FileSpec] = [
    FileSpec(
        ".nvmrc",
        "typescript/nvmrc.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="typescript",
        user_overridable=True,
    ),
    FileSpec(
        ".prettierrc.json",
        "typescript/prettierrc.json.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="typescript",
        user_overridable=True,
    ),
    FileSpec(
        "eslint.config.mjs",
        "typescript/eslint.config.mjs.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="typescript",
        user_overridable=True,
    ),
    FileSpec(
        "tsconfig.json",
        "typescript/tsconfig.json.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="typescript",
        user_overridable=True,
    ),
    FileSpec(
        "vitest.config.ts",
        "typescript/vitest.config.ts.jinja2",
        FileCategory.BOILERPLATE,
        MergeStrategy.OVERWRITE,
        language="typescript",
        user_overridable=True,
    ),
]

# Plugin metadata: skip for v1.0 (deep-merge not yet
# implemented; SKIP avoids overwriting user-added fields)
_METADATA_FILES: list[FileSpec] = [
    FileSpec(
        ".claude-plugin/plugin.json",
        "shared/plugin.json.jinja2",
        FileCategory.METADATA,
        MergeStrategy.SKIP,
    ),
    FileSpec(
        ".claude-plugin/marketplace.json",
        "shared/marketplace.json.jinja2",
        FileCategory.METADATA,
        MergeStrategy.SKIP,
    ),
]

# Composite files: merge (append-only)
_COMPOSITE_FILES: list[FileSpec] = [
    FileSpec(
        ".gitignore",
        None,
        FileCategory.COMPOSITE,
        MergeStrategy.MERGE,
    ),
    FileSpec(
        "Makefile",
        None,
        FileCategory.COMPOSITE,
        MergeStrategy.MERGE,
    ),
]

# CI workflows: add if missing, skip if exists
_CI_FILES: list[FileSpec] = [
    FileSpec(
        ".github/workflows/ci.yml",
        "python/ci.yml.jinja2",
        FileCategory.CI_WORKFLOW,
        MergeStrategy.ADD,
        language="python",
        user_overridable=True,
    ),
    FileSpec(
        ".github/workflows/ci.yml",
        "typescript/ci.yml.jinja2",
        FileCategory.CI_WORKFLOW,
        MergeStrategy.ADD,
        language="typescript",
        user_overridable=True,
    ),
]

# Dependency configs: flag for manual review
_DEPENDENCY_PYTHON: list[FileSpec] = [
    FileSpec(
        "pyproject.toml",
        "python/pyproject.toml.jinja2",
        FileCategory.DEPENDENCY_CONFIG,
        MergeStrategy.MANUAL_REVIEW,
        language="python",
    ),
]

_DEPENDENCY_TYPESCRIPT: list[FileSpec] = [
    FileSpec(
        "package.json",
        "typescript/package.json.jinja2",
        FileCategory.DEPENDENCY_CONFIG,
        MergeStrategy.MANUAL_REVIEW,
        language="typescript",
    ),
]


def get_file_specs(
    language: str,
) -> list[FileSpec]:
    """Get the file specifications for a given language.

    Returns the complete list of files that the scaffolder
    would produce for a plugin of the given language.

    Args:
        language: "python" or "typescript"

    Returns:
        List of FileSpec for all applicable files
    """
    specs: list[FileSpec] = []

    # Shared files (all languages)
    specs.extend(_CUSTOM_FILES)
    specs.extend(_AIDA_METADATA_FILES)
    specs.extend(_BOILERPLATE_SHARED)
    specs.extend(_METADATA_FILES)
    specs.extend(_COMPOSITE_FILES)

    # Language-specific files
    if language == "python":
        specs.extend(_BOILERPLATE_PYTHON)
        specs.extend(
            s for s in _CI_FILES if s.language == "python"
        )
        specs.extend(_DEPENDENCY_PYTHON)
    elif language == "typescript":
        specs.extend(_BOILERPLATE_TYPESCRIPT)
        specs.extend(
            s
            for s in _CI_FILES
            if s.language == "typescript"
        )
        specs.extend(_DEPENDENCY_TYPESCRIPT)

    return specs


def get_spec_by_path(
    path: str,
    language: str,
) -> FileSpec | None:
    """Look up a file spec by its relative path.

    Args:
        path: Relative path from plugin root
        language: Plugin language

    Returns:
        FileSpec if found, None otherwise
    """
    for spec in get_file_specs(language):
        if spec.path == path:
            return spec
    return None
