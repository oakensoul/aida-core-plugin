---
type: skill
name: create-plugin
description: Scaffolds a complete Claude Code plugin project as a new local git repository with language-specific tooling
version: 0.1.0
argument_hint: "[plugin-name]"
tags:
  - scaffolding
  - plugin
  - project
---

# Create Plugin

Scaffolds a complete Claude Code plugin project as a new local git repository
with language-specific tooling (Python or TypeScript).

This is distinct from `claude-code-management` which creates extensions *inside*
an existing project. This skill creates a brand new project from scratch, ready
to develop and publish.

## Activation

This skill activates when:

- User invokes `/aida plugin scaffold`
- Routed from `aida` skill for plugin scaffolding commands

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>` tags
containing the skill base directory.

**Script Execution:** Construct full paths from base directory:

```text
{base_directory}/scripts/scaffold.py
```

**Templates:** Located in the templates subdirectory:

```text
{base_directory}/templates/shared/
{base_directory}/templates/python/
{base_directory}/templates/typescript/
```

**CCM Templates:** Agent and skill stubs reference templates from:

```text
{project_root}/skills/claude-code-management/templates/
```

## Two-Phase Workflow

### Phase 1: Gather Context

Run the scaffold script with `--get-questions` to determine what information is
needed. The script automatically infers git config (author name/email) and checks
for `gh` CLI availability.

```bash
python {base_directory}/scripts/scaffold.py --get-questions --context='{"plugin_name": "my-plugin"}'
```

The script returns a JSON object with:

- `questions`: List of questions for missing context fields
- `inferred`: Auto-detected values (author name/email from git config)

Present the questions to the user, collecting answers. Merge answers with
inferred values into the full context object. For example, if Phase 1 returns
`inferred.author_name` and the user was not asked for `author_name`, include
the inferred value in the context sent to Phase 2:

```json
{
  "plugin_name": "my-plugin",
  "author_name": "Jane Smith",
  "author_email": "jane@example.com",
  "language": "python"
}
```

### Phase 2: Execute Scaffolding

Run the scaffold script with `--execute` and the complete context:

```bash
python {base_directory}/scripts/scaffold.py --execute --context='{
  "plugin_name": "my-plugin",
  "description": "A useful Claude Code plugin",
  "license": "MIT",
  "language": "python",
  "target_directory": "/path/to/my-plugin",
  "author_name": "Author Name",
  "author_email": "author@example.com",
  "include_agent_stub": false,
  "include_skill_stub": false,
  "keywords": "productivity, automation",
  "create_github_repo": false
}'
```

The script creates:

- Complete directory structure with `.claude-plugin/`, agents, skills, docs
- `plugin.json`, `marketplace.json`, `aida-config.json` metadata
- `CLAUDE.md`, `README.md`, `LICENSE`
- Language-specific config (pyproject.toml or package.json, linter configs)
- Composite `.gitignore` and `Makefile`
- Optional agent and skill stubs
- Initialized git repository with initial commit

### Post-Scaffold: GitHub Repository (Optional)

If the user requested `create_github_repo: true`, the result will include this
flag. Use the GitHub CLI to create the remote:

```bash
cd /path/to/my-plugin
gh repo create my-plugin --public --source=. --push
```

This step is LLM-orchestrated (not in the Python script) so the user can
customize visibility, organization, etc.

## Error Handling

If Phase 2 returns `{"success": false, ...}`, report the `message` field to
the user and offer to retry. The response includes `path` and `files_created`
for any partial output. Common causes and resolutions are documented in
`references/scaffolding-workflow.md`.

## Resources

### scripts/

- **scaffold.py** - Main entry point (two-phase API)
- **scaffold_ops/context.py** - Git config inference, directory validation
- **scaffold_ops/generators.py** - Directory creation, template rendering, git init
- **scaffold_ops/licenses.py** - License text templates (MIT, Apache-2.0, ISC, GPL-3.0, AGPL-3.0, UNLICENSED)

### templates/

Jinja2 templates organized by scope:

- **shared/** - Language-independent files (plugin.json, CLAUDE.md, README, linter configs)
- **python/** - Python toolchain (pyproject.toml, conftest.py, ruff config)
- **typescript/** - TypeScript toolchain (package.json, tsconfig, eslint, vitest)

### references/

- **scaffolding-workflow.md** - Detailed workflow documentation
