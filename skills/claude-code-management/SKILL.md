---
type: skill
name: claude-code-management
description: Unified management for Claude Code artifacts - extensions (agents, commands, skills, plugins) and configuration files (CLAUDE.md) using templates and a two-phase API.
version: 0.3.0
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

For `create` operations, use the **three-phase orchestration pattern**:

#### Phase 1: Gather Context (Python)

Run the script to infer metadata and get questions:

```bash
python {base_directory}/scripts/manage.py --get-questions \
  --context='{"operation": "create", "type": "agent", "description": "user description", "location": "user"}'
```

Returns:

```json
{
  "inferred": {
    "name": "inferred-name",
    "version": "0.1.0",
    "tags": ["custom"],
    "base_path": "~/.claude/agents/inferred-name"
  },
  "questions": [
    {"id": "location", "question": "Where to create?", "options": [...]}
  ],
  "project_context": {
    "languages": ["python"],
    "frameworks": ["fastapi"]
  }
}
```

#### Phase 2: Generate Content (Agent)

Spawn the `claude-code-expert` agent with complete context and output contract:

```text
Operation: CREATE
Type: agent

Requirements:
  - Name: {inferred.name}
  - Description: {user_description}
  - Location: {inferred.base_path}
  - Project Context: {project_context}
  - User Answers: {answers to questions}

Output Format:
Return a JSON object with this exact structure:

{
  "validation": {
    "passed": true|false,
    "issues": [
      {"severity": "error|warning", "message": "description", "suggestion": "how to fix"}
    ]
  },
  "files": [
    {
      "path": "relative/path/to/file.md",
      "content": "complete file content as string"
    }
  ],
  "summary": {
    "created": ["list of files"],
    "next_steps": ["what user should do next"]
  }
}

If validation fails (passed=false with errors), return empty files array.
Warnings should not prevent file generation.
```

**Handle agent response:**

1. Parse the JSON response
2. If `validation.passed` is false with errors:
   - Report issues to user
   - Ask if they want to proceed anyway or provide more info
3. If validation passed (or user chose to proceed):
   - Continue to Phase 3

#### Phase 3: Write Files (Python)

Pass agent output to Python for file creation:

```bash
python {base_directory}/scripts/manage.py --execute \
  --context='{"operation": "create", "type": "agent", "agent_output": <agent_json>}'
```

The script:

1. Validates file structure (required fields, proper frontmatter)
2. Creates directories
3. Writes files
4. Returns success/failure

### Validate Operations

For `validate` operations:

1. Run validation script
2. Report results with any errors

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

## Agent Output Contract

When spawning `claude-code-expert` for CREATE operations, always include this output format specification:

### For Agents

```text
Output Format:
Return a JSON object with this exact structure:

{
  "validation": {
    "passed": boolean,
    "issues": [
      {"severity": "error|warning", "message": "string", "suggestion": "string"}
    ]
  },
  "files": [
    {"path": "agents/{name}/{name}.md", "content": "..."},
    {"path": "agents/{name}/knowledge/index.md", "content": "..."},
    {"path": "agents/{name}/knowledge/{topic}.md", "content": "..."}
  ],
  "summary": {
    "created": ["list of relative paths"],
    "next_steps": ["actionable items for user"]
  }
}
```

### For Commands

```text
Output Format:
Return a JSON object with this exact structure:

{
  "validation": {
    "passed": boolean,
    "issues": [...]
  },
  "files": [
    {"path": "commands/{name}.md", "content": "..."}
  ],
  "summary": {
    "created": ["list of relative paths"],
    "next_steps": ["actionable items for user"]
  }
}
```

### For Skills

```text
Output Format:
Return a JSON object with this exact structure:

{
  "validation": {
    "passed": boolean,
    "issues": [...]
  },
  "files": [
    {"path": "skills/{name}/SKILL.md", "content": "..."},
    {"path": "skills/{name}/scripts/{script}.py", "content": "..."},
    {"path": "skills/{name}/references/{doc}.md", "content": "..."},
    {"path": "skills/{name}/templates/{template}.jinja2", "content": "..."}
  ],
  "summary": {
    "created": ["list of relative paths"],
    "next_steps": ["actionable items for user"]
  }
}
```

### For Plugins

```text
Output Format:
Return a JSON object with this exact structure:

{
  "validation": {
    "passed": boolean,
    "issues": [...]
  },
  "files": [
    {"path": ".claude-plugin/plugin.json", "content": "..."},
    {"path": "README.md", "content": "..."},
    {"path": ".gitignore", "content": "..."},
    {"path": "agents/{name}/{name}.md", "content": "..."}
  ],
  "summary": {
    "created": ["list of relative paths"],
    "next_steps": ["actionable items for user"]
  }
}
```

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
{base_directory}/references/create-workflow.md
{base_directory}/references/validate-workflow.md
{base_directory}/references/schemas.md
{base_directory}/references/claude-md-workflow.md
{base_directory}/references/best-practices.md
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

## Example Workflows

### Creating an Agent (Full Flow)

```text
User: /aida agent create "handles database migrations"

1. Parse: type=agent, operation=create, description="handles database migrations"

2. Phase 1 (Python):
   python manage.py --get-questions --context='{...}'
   Returns:
   - inferred: name="database-migration", version="0.1.0"
   - questions: [location question]
   - project_context: {languages: ["python"], frameworks: ["alembic"]}

3. Ask user questions (if any):
   AskUserQuestion: "Where should we create this agent?"

4. Phase 2 (Agent):
   Spawn claude-code-expert with:
   - Operation: CREATE
   - Type: agent
   - Name: database-migration
   - Description: handles database migrations
   - Location: ~/.claude/agents/database-migration
   - Project Context: Python, Alembic detected
   - Output Format: [JSON contract]

   Agent returns:
   {
     "validation": {"passed": true, "issues": []},
     "files": [
       {"path": "agents/database-migration/database-migration.md", "content": "..."},
       {"path": "agents/database-migration/knowledge/index.md", "content": "..."},
       {"path": "agents/database-migration/knowledge/migration-patterns.md", "content": "..."}
     ],
     "summary": {
       "created": ["database-migration.md", "knowledge/index.md", "knowledge/migration-patterns.md"],
       "next_steps": ["Review migration-patterns.md and add project-specific patterns"]
     }
   }

5. Phase 3 (Python):
   python manage.py --execute --context='{"operation": "create", "agent_output": {...}}'
   - Validates structure
   - Creates directories
   - Writes files

6. Report to user:
   "Created agent 'database-migration' with 3 files:
    - database-migration.md
    - knowledge/index.md
    - knowledge/migration-patterns.md

   Next steps:
    - Review migration-patterns.md and add project-specific patterns"
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

## Resources

### scripts/

- **manage.py** - Main dispatcher script
- **operations/** - Operation modules
  - **utils.py** - Shared utilities
  - **extensions.py** - Extension operations (agent/command/skill/plugin)
  - **claude_md.py** - CLAUDE.md operations

### references/

- **create-workflow.md** - Extension create workflow (deprecated - use this SKILL.md)
- **validate-workflow.md** - Extension validation rules
- **schemas.md** - Frontmatter schema reference
- **claude-md-workflow.md** - CLAUDE.md create/optimize workflow
- **best-practices.md** - CLAUDE.md best practices and scoring
