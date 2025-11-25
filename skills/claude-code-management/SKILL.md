---
type: skill
name: claude-code-management
description: This skill provides creation, validation, versioning, and management capabilities for Claude Code extensions (agents, commands, skills, plugins) using templates and a two-phase API.
version: 0.1.0
tags:
  - core
  - management
  - extensions
---

# Claude Code Management

Manages Claude Code extensions through a unified interface for creating,
validating, versioning, and listing agents, commands, skills, and plugins.

## Activation

This skill activates when:

- User invokes `/aida agent [create|validate|version|list]`
- User invokes `/aida command [create|validate|version|list]`
- User invokes `/aida skill [create|validate|version|list]`
- User invokes `/aida plugin [create|validate|version|list|add|remove]`
- Extension management operations are needed

## Command Routing

When this skill activates, parse the command to determine:

1. **Component type**: `agent`, `command`, `skill`, or `plugin`
2. **Operation**: `create`, `validate`, `version`, `list`, `add`, `remove`
3. **Arguments**: name, description, options

### Create Operations

For `create` operations:

1. Read `references/create-workflow.md` for the full workflow
2. Run Phase 1 to get questions and inferred data
3. Ask user any required questions using AskUserQuestion
4. Run Phase 2 to create the component
5. Report success and next steps

**Script invocation:**

```bash
# Phase 1: Get questions
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"operation": "create", "type": "agent", "description": "user description", "location": "user"}'

# Phase 2: Execute
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "create", "type": "agent", "name": "inferred-name", "description": "...", "version": "0.1.0", "tags": ["custom"], "location": "user"}'
```

### Validate Operations

For `validate` operations:

1. Read `references/validate-workflow.md` for validation rules
2. Run validation script
3. Report results with any errors

**Script invocation:**

```bash
# Validate specific component
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "validate", "type": "agent", "name": "my-agent"}'

# Validate all
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "validate", "type": "agent", "all": true, "location": "all"}'
```

### Version Operations

For `version` operations:

1. Find the component
2. Bump version (major, minor, or patch)
3. Update the file
4. Report the version change

**Script invocation:**

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "version", "type": "agent", "name": "my-agent", "bump": "patch"}'
```

### List Operations

For `list` operations:

1. Search specified locations
2. Parse component metadata
3. Return formatted list

**Script invocation:**

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "list", "type": "agent", "location": "all", "format": "table"}'
```

### Plugin-Specific Operations

For `add` and `remove` on plugins:

- `add`: Create component inside plugin directory
- `remove`: Remove component from plugin (with confirmation)

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>` tags.

**Script Execution:**

```text
{base_directory}/scripts/manage.py
```

**Reference Files:**

```text
{base_directory}/references/create-workflow.md
{base_directory}/references/validate-workflow.md
{base_directory}/references/schemas.md
```

**Templates:**

```text
{base_directory}/templates/agent/agent.md.jinja2
{base_directory}/templates/command/command.md.jinja2
{base_directory}/templates/skill/SKILL.md.jinja2
{base_directory}/templates/plugin/plugin.json.jinja2
{base_directory}/templates/plugin/README.md.jinja2
{base_directory}/templates/plugin/gitignore.jinja2
```

## Location Options

Components can be created/managed in different locations:

| Location  | Path         | Use Case                    |
| --------- | ------------ | --------------------------- |
| `user`    | `~/.claude/` | Personal extensions         |
| `project` | `./.claude/` | Project-specific extensions |
| `plugin`  | Custom path  | Plugin development          |

Default location is `user` for create operations.

## Two-Phase API

This skill uses a two-phase API pattern:

### Phase 1: Get Questions

Analyzes context and returns:

- Inferred metadata (name, version, tags)
- Questions that need user input
- Validation results

### Phase 2: Execute

Performs the operation with:

- User responses (if any)
- Inferred data
- Configuration options

## Example Workflows

### Creating an Agent

```text
User: /aida agent create "handles database migrations"

1. Parse: type=agent, operation=create, description="handles database migrations"
2. Run Phase 1:
   - Infer: name="database-migration", version="0.1.0", tags=["database", "custom"]
   - No questions (all data inferred)
3. Run Phase 2:
   - Create ~/.claude/agents/database-migration/database-migration.md
   - Create knowledge/ directory
4. Report: "Created agent 'database-migration'. Add knowledge docs to knowledge/"
```

### Validating All Commands

```text
User: /aida command validate --all

1. Parse: type=command, operation=validate, all=true
2. Run validation:
   - Find all commands in user/project locations
   - Validate each against schema
3. Report: "Validated 5 commands: 4 valid, 1 invalid"
   - Show errors for invalid commands
```

### Bumping Version

```text
User: /aida skill version my-skill minor

1. Parse: type=skill, operation=version, name="my-skill", bump="minor"
2. Find skill in locations
3. Read current version (0.1.0)
4. Bump to 0.2.0
5. Update SKILL.md
6. Report: "Updated my-skill from 0.1.0 to 0.2.0"
```

## Resources

### scripts/

- **manage.py** - Main management script with two-phase API

### references/

- **create-workflow.md** - Detailed create operation workflow
- **validate-workflow.md** - Validation rules and process
- **schemas.md** - Frontmatter schema reference

### templates/

- **agent/** - Agent template
- **command/** - Command template
- **skill/** - Skill template
- **plugin/** - Plugin templates (JSON, README, gitignore)
