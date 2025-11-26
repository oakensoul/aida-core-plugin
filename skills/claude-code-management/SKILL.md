---
type: skill
name: claude-code-management
description: Unified management for Claude Code artifacts - extensions (agents, commands, skills, plugins) and configuration files (CLAUDE.md) using templates and a two-phase API.
version: 0.2.0
tags:
  - core
  - management
  - extensions
  - configuration
---

# Claude Code Management

Unified management interface for Claude Code artifacts:

- **Extensions**: agents, commands, skills, plugins
- **Configuration**: CLAUDE.md files

## Activation

This skill activates when:

- User invokes `/aida agent [create|validate|version|list]`
- User invokes `/aida command [create|validate|version|list]`
- User invokes `/aida skill [create|validate|version|list]`
- User invokes `/aida plugin [create|validate|version|list|add|remove]`
- User invokes `/aida claude [create|optimize|validate|list]`
- Extension or configuration management is needed

## Extension Operations

### Command Routing

Parse the command to determine:

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

## CLAUDE.md Operations

### Command Routing

Parse the command to determine:

1. **Operation**: `create`, `optimize`, `validate`, `list`
2. **Scope**: `project`, `user`, `plugin`, or `all`
3. **Arguments**: path, options

### Create Operations

For `create` operations:

1. Read `references/claude-md-workflow.md` for the full workflow
2. Run Phase 1 to detect project context
3. Ask user scope if not specified
4. Run Phase 2 to create the file
5. Report success

**Script invocation:**

```bash
# Phase 1: Get questions
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"target": "claude", "operation": "create", "scope": "project"}'

# Phase 2: Execute
python {base_directory}/scripts/manage.py --execute \
  --context='{"target": "claude", "operation": "create", "scope": "project", "name": "...", "description": "...", "commands": [...]}'
```

### Optimize Operations

For `optimize` operations:

1. Read `references/best-practices.md` for scoring criteria
2. Run Phase 1 to audit and generate findings
3. Ask user how to fix (all, critical only, interactive, skip)
4. Run Phase 2 to apply fixes
5. Report new score and changes

**Script invocation:**

```bash
# Phase 1: Get audit and questions
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"target": "claude", "operation": "optimize", "scope": "project"}'

# Phase 2: Apply fixes
python {base_directory}/scripts/manage.py --execute \
  --context='{"target": "claude", "operation": "optimize", "scope": "project", "fix_mode": "Fix all"}'
```

### Validate Operations

For `validate` operations:

1. Find CLAUDE.md files in specified scope
2. Run validation checks
3. Report results

**Script invocation:**

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"target": "claude", "operation": "validate", "scope": "all"}'
```

### List Operations

For `list` operations:

1. Find all CLAUDE.md files
2. Include validation status
3. Return formatted list

**Script invocation:**

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"target": "claude", "operation": "list", "scope": "all"}'
```

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>` tags.

**Script Execution:**

```text
{base_directory}/scripts/manage.py
```

**Reference Files:**

```text
# Extension references
{base_directory}/references/create-workflow.md
{base_directory}/references/validate-workflow.md
{base_directory}/references/schemas.md

# CLAUDE.md references
{base_directory}/references/claude-md-workflow.md
{base_directory}/references/best-practices.md
```

**Templates:**

```text
# Extension templates
{base_directory}/templates/agent/agent.md.jinja2
{base_directory}/templates/command/command.md.jinja2
{base_directory}/templates/skill/SKILL.md.jinja2
{base_directory}/templates/plugin/plugin.json.jinja2
{base_directory}/templates/plugin/README.md.jinja2
{base_directory}/templates/plugin/gitignore.jinja2

# CLAUDE.md templates
{base_directory}/templates/claude-md/project.md.jinja2
{base_directory}/templates/claude-md/user.md.jinja2
{base_directory}/templates/claude-md/plugin.md.jinja2
```

## Location Options

### Extension Locations

| Location  | Path         | Use Case                    |
| --------- | ------------ | --------------------------- |
| `user`    | `~/.claude/` | Personal extensions         |
| `project` | `./.claude/` | Project-specific extensions |
| `plugin`  | Custom path  | Plugin development          |

### CLAUDE.md Scopes

| Scope     | Path                        | Use Case                |
| --------- | --------------------------- | ----------------------- |
| `project` | `./CLAUDE.md`               | Project documentation   |
| `user`    | `~/.claude/CLAUDE.md`       | Global user preferences |
| `plugin`  | `.claude-plugin/CLAUDE.md`  | Plugin documentation    |

## Two-Phase API

This skill uses a two-phase API pattern:

### Phase 1: Get Questions

Analyzes context and returns:

- Inferred metadata (name, version, tags, project context)
- Questions that need user input
- Audit findings (for optimize operations)
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

### Optimizing CLAUDE.md

```text
User: /aida claude optimize

1. Parse: target=claude, operation=optimize, scope=project
2. Run Phase 1:
   - Find CLAUDE.md
   - Audit against best practices
   - Score: 65/100
   - Findings: 3 issues (1 critical)
3. Ask: "How would you like to fix them?"
4. User: "Fix all"
5. Run Phase 2:
   - Apply fixes
   - New score: 85/100
6. Report: "Applied 3 fixes. Score improved from 65 to 85."
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

## Resources

### scripts/

- **manage.py** - Main dispatcher script
- **operations/** - Operation modules
  - **utils.py** - Shared utilities
  - **extensions.py** - Extension operations (agent/command/skill/plugin)
  - **claude_md.py** - CLAUDE.md operations

### references/

- **create-workflow.md** - Extension create workflow
- **validate-workflow.md** - Extension validation rules
- **schemas.md** - Frontmatter schema reference
- **claude-md-workflow.md** - CLAUDE.md create/optimize workflow
- **best-practices.md** - CLAUDE.md best practices and scoring

### templates/

- **agent/** - Agent template
- **command/** - Command template
- **skill/** - Skill template
- **plugin/** - Plugin templates (JSON, README, gitignore)
- **claude-md/** - CLAUDE.md templates (project, user, plugin)
