---
type: skill
name: plugin-manager
description: >-
  Unified plugin management combining extension CRUD operations
  (create, validate, version, list) with project scaffolding
version: 0.1.0
argument_hint: "[operation] [args]"
tags:
  - core
  - management
  - plugin
  - scaffolding
---

# Plugin Manager

Unified plugin management skill that combines two capabilities:

1. **Extension CRUD** -- create, validate, version, and list plugin
   extensions within existing projects
2. **Project Scaffolding** -- scaffold entirely new plugin projects
   as local git repositories with language-specific tooling

## Activation

This skill activates when:

- User invokes `/aida plugin create`
- User invokes `/aida plugin validate`
- User invokes `/aida plugin version`
- User invokes `/aida plugin list`
- User invokes `/aida plugin scaffold`
- Routed from `aida` skill for any plugin operation

## Operations

| Operation  | Mode       | Description                          |
| ---------- | ---------- | ------------------------------------ |
| `create`   | Extension  | Create plugin extension dirs/files   |
| `validate` | Extension  | Validate plugin.json metadata        |
| `version`  | Extension  | Bump plugin.json version             |
| `list`     | Extension  | List discovered plugins              |
| `scaffold` | Scaffolding| Scaffold a full new plugin project   |

## Path Resolution

**Base Directory:** Provided when skill loads via
`<command-message>` tags containing the skill base directory.

**Script Execution:**

```text
{base_directory}/scripts/manage.py
```

**Templates:**

```text
{base_directory}/templates/extension/   # Plugin extension templates
{base_directory}/templates/scaffold/    # Project scaffolding templates
```

## Two-Phase Workflow

### Extension Operations (create / validate / version / list)

#### Phase 1: Gather Context

```bash
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"operation": "create", "description": "..."}'
```

Returns questions and inferred metadata. The script auto-sets
`component_type` to `"plugin"`.

#### Phase 2: Execute

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "create", ...}'
```

Creates, validates, versions, or lists plugin extensions.

### Scaffold Operation

#### Phase 1: Gather Context

```bash
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"operation": "scaffold", "plugin_name": "my-plugin"}'
```

Infers git config (author name/email), checks gh availability,
and returns questions for missing fields (name, description,
license, language, target directory, stubs, keywords).

#### Phase 2: Execute Scaffolding

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "scaffold", "plugin_name": "my-plugin", "language": "python", ...}'
```

Creates a complete plugin project with:

- Directory structure (`.claude-plugin/`, agents, skills, docs)
- Metadata files (`plugin.json`, `marketplace.json`,
  `aida-config.json`)
- Documentation (`CLAUDE.md`, `README.md`, `LICENSE`)
- Language tooling (pyproject.toml or package.json, linters)
- Composite `.gitignore` and `Makefile`
- Optional agent and skill stubs
- Initialized git repository with initial commit

### Post-Scaffold: GitHub Repository (Optional)

If the user requested `create_github_repo: true`, the result
includes this flag. Use the GitHub CLI to create the remote:

```bash
cd /path/to/my-plugin
gh repo create my-plugin --public --source=. --push
```

## Plugin Validation Notes

Plugin validation is **JSON-based** (plugin.json), not
frontmatter-based like agents and skills. The validation checks:

- `name` -- required, kebab-case, 2-50 chars
- `version` -- required, semver X.Y.Z
- `description` -- required, 10-500 chars

## Error Handling

If Phase 2 returns `{"success": false, ...}`, report the
`message` field to the user and offer to retry. The response
includes `path` and `files_created` for any partial output.

## Resources

### scripts/

- **manage.py** -- Two-phase API entry point (routes between
  extension and scaffold operations)
- **operations/extensions.py** -- Plugin extension CRUD
- **operations/scaffold.py** -- Plugin project scaffolding
- **operations/scaffold_ops/** -- Scaffolding submodules
  - **context.py** -- Git config inference, directory validation
  - **generators.py** -- Directory creation, template rendering
  - **licenses.py** -- License text templates
- **operations/utils.py** -- Re-export shim for shared utilities

### templates/

- **extension/** -- Plugin extension templates (plugin.json,
  README.md, .gitignore)
- **scaffold/** -- Project scaffolding templates
  - **shared/** -- Language-independent files
  - **python/** -- Python toolchain templates
  - **typescript/** -- TypeScript toolchain templates

### references/

- **scaffolding-workflow.md** -- Scaffolding workflow reference
- **validate-workflow.md** -- Plugin validation reference
- **schemas.md** -- Plugin JSON schema reference
