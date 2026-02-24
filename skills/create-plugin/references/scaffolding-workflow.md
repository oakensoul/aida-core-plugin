---
type: reference
title: Plugin Scaffolding Workflow
---

# Plugin Scaffolding Workflow

Detailed reference for the create-plugin scaffolding process.

## End-to-End Flow

1. User invokes `/aida plugin scaffold` or `/aida plugin new`
2. Dispatch routes to `create-plugin` skill
3. Skill runs `scaffold.py --get-questions` with any provided context
4. Script infers git config, checks gh availability, returns questions
5. Skill presents questions to user, collects answers
6. Skill runs `scaffold.py --execute` with full context
7. Script creates project, returns result with file list and next steps
8. If `create_github_repo` is true, skill runs `gh repo create`

## Template Variables

All templates receive these variables:

| Variable | Type | Description |
| --- | --- | --- |
| `plugin_name` | string | Kebab-case name |
| `plugin_display_name` | string | Title Case display name |
| `description` | string | 10-500 char description |
| `version` | string | Semver (default "0.1.0") |
| `author_name` | string | From git config or input |
| `author_email` | string | From git config or input |
| `license_id` | string | SPDX identifier |
| `license_text` | string | Full license body |
| `year` | string | Current year |
| `language` | string | "python" or "typescript" |
| `script_extension` | string | ".py" or ".ts" |
| `python_version` | string | Python version, format "X.Y" (default: "3.11") |
| `node_version` | string | Node.js major version (default: "22") |
| `keywords` | list | Marketplace tags |
| `repository_url` | string | GitHub URL or "" |
| `include_agent_stub` | bool | Include agent stub |
| `include_skill_stub` | bool | Include skill stub |
| `timestamp` | string | ISO 8601 UTC |
| `generator_version` | string | aida-core version |

## Language-Specific Differences

### Python

- `pyproject.toml` with ruff and pytest configuration
- `.python-version` file
- `tests/conftest.py` with shared fixtures
- Makefile targets: `lint-py`, `test` (pytest), `format` (ruff)
- `.gitignore` includes `__pycache__/`, `venv/`, `.pytest_cache/`

### TypeScript

- `package.json` with ESM modules
- `tsconfig.json` with strict mode
- `eslint.config.mjs` with flat config
- `.prettierrc.json` for formatting
- `.nvmrc` for Node.js version
- `vitest.config.ts` for testing
- Makefile targets: `lint-ts`, `test` (vitest), `build` (tsc), `format` (prettier)
- `.gitignore` includes `node_modules/`, `dist/`, `coverage/`

## Error Handling

| Error | Cause | Resolution |
| --- | --- | --- |
| "Target directory is not empty" | Existing files at path | Choose a different path |
| "Parent directory does not exist" | Invalid path | Create parent or choose another |
| "Invalid plugin name" | Fails validation | Use kebab-case, 2-50 chars |
| "Invalid description" | Too short/long | Use 10-500 characters |
| "Unsupported license" | Unknown SPDX ID | Choose from supported list |

## Post-Scaffold Steps

After scaffolding completes:

1. `cd` into the new project directory
2. Install dependencies (`pip install -e ".[dev]"` or `npm install`)
3. Run `make lint` to verify the project structure
4. Run `make test` to verify test setup
5. Optionally create GitHub repo with `gh repo create`
6. Start building agents and skills
