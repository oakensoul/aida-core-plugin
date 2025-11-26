---
type: reference
title: Extension Types Decision Guide
description: How to choose between agents, commands, skills, plugins, and hooks
---

# Extension Types

Claude Code supports multiple extension types, each designed for different
use cases. This guide helps you choose the right type.

**See also:** `framework-design-principles.md` for architectural standards and
quality criteria for each type.

## The Framework: WHO / WHAT / HOW / CONTEXT / MEMORY / AUTOMATION

| Type | Role | Contains |
|------|------|----------|
| **Subagent** | WHO | Identity, expertise, judgment, quality standards |
| **Command** | WHAT | Instructions/recipe/process (thinking + doing steps) |
| **Skill** | HOW | Execution capabilities (scripts, templates, automation) |
| **Knowledge** | CONTEXT | Facts, schemas, patterns (loaded with extensions) |
| **CLAUDE.md** | MEMORY | Project/user conventions (always loaded) |
| **Plugin** | DISTRIBUTION | Container for subagents, commands, skills, knowledge |
| **Hooks** | AUTOMATION | Shell commands triggered on lifecycle events |

**Key insight:** Claude Code (the orchestrator) is the primary agent. All extensions
are inert definitions that the orchestrator reads and acts upon. Subagents are
specialists spawned for specific expertise.

**See also:** `framework-design-principles.md` for Context Layering - how these
sources combine when processing requests.

## Quick Decision Tree

```text
Start Here
    │
    ▼
Is this a distributable package of multiple components?
    │
    ├─ YES → Plugin
    │
    ▼ NO
    │
Should it run AUTOMATICALLY on lifecycle events (not user-invoked)?
    │
    ├─ YES → Hook (deterministic automation)
    │
    ▼ NO
    │
Does it need domain expertise to DEFINE (not just use)?
    │
    ├─ YES → Subagent (expertise definition)
    │
    ▼ NO
    │
Does it need Python scripts or Jinja2 templates?
    │
    ├─ YES → Skill (execution capabilities)
    │
    ▼ NO
    │
Is it a user-invoked process (simple or complex)?
    │
    └─ YES → Command (instructions/recipe)
```

**Note:** Commands can invoke Skills and spawn Subagents. The question is where
the definition lives, not what gets used during execution.

## Extension Types Compared

| Aspect         | Command              | Skill          | Subagent         | Plugin       |
| -------------- | -------------------- | -------------- | ---------------- | ------------ |
| **Purpose**    | Process definition   | Execution      | Expertise        | Distribution |
| **Analogy**    | Recipe/Instructions  | Kitchen tools  | Specialist chef  | Cookbook     |
| **Invocation** | `/command`           | Via command    | Via Task tool    | Container    |
| **State**      | Stateless            | Stateless      | Context-aware    | N/A          |
| **Scripts**    | No (invokes skills)  | Yes            | Via skills       | Contains all |
| **Complexity** | Simple to complex    | Execution-focused | Domain-focused | Bundles all  |

## Commands

### What They Are

Commands are **instructions/recipes/process definitions** - they define what should
happen when a user invokes them. Like furniture assembly instructions or a recipe,
they describe the steps (both thinking and doing) but don't execute anything
themselves.

### When to Use

- User-invoked processes of any complexity
- Workflows that combine thinking and doing steps
- Entry points that orchestrate skills and agents
- Any process that doesn't require custom scripts

### Characteristics

- Invoked with `/command-name`
- Defined in a single `.md` file
- Can define multi-step processes (the recipe)
- Can invoke skills for execution capabilities
- Can spawn agents for expert judgment
- Can specify allowed tools
- Can accept arguments

### What Commands Can Contain

- **Thinking steps**: "Analyze X", "Evaluate against these criteria", "Decide Y"
- **Doing steps**: "Create file", "Run tests", "Update config"
- **Skill invocations**: "Use the `setup` skill to configure"
- **Agent spawns**: "Spawn the security expert to review"
- **Decision criteria**: "If TypeScript project, do X; otherwise do Y"

### Example Use Cases

- `/deploy` - Analyze environment, decide deployment strategy, invoke deploy skill
- `/review` - Apply review criteria, evaluate code, generate report
- `/setup` - Detect project type, gather requirements, invoke setup skill
- `/test` - Determine test strategy, run appropriate tests, report results

### Structure

```text
commands/
└── my-command.md
```

## Skills

### What They Are

Skills are reusable capabilities with scripts, templates, and references.
They provide automation and can be used by multiple agents.

### When to Use

- Automation workflows
- Script execution
- Template rendering
- Reusable functionality across agents
- Complex multi-step processes

### Characteristics

- Can execute Python scripts
- Can use Jinja2 templates
- Have reference documentation
- Activate on triggers or invocation
- Stateless (no memory between calls)

### Example Use Cases

- Project configuration
- Code generation
- API integration
- File management
- Build automation

### Structure

```text
skills/
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    │   └── action.py
    ├── references/
    │   └── workflow.md
    └── templates/
        └── template.jinja2
```

## Subagents

### What They Are

Subagents are specialist personas with domain knowledge. The orchestrator
(Claude Code) spawns them when specific expertise is needed. They provide
guidance, make decisions, and can use skills to accomplish tasks.

**Note:** The `/agents` folder contains subagent definitions. The orchestrator
itself is the primary agent.

### When to Use

- Domain expertise needed beyond the orchestrator's general knowledge
- Specialized judgment or quality standards
- Complex decision-making in a specific domain
- Tasks requiring deep context in a particular area
- Advisory or consultative roles

### Characteristics

- Have a knowledge directory with domain expertise
- Can use multiple skills for execution
- Spawned by orchestrator via Task tool
- Return results to orchestrator when done
- Provide expert guidance within their domain

### Example Use Cases

- Code review expert
- Security advisor
- Architecture consultant
- Documentation specialist
- Test strategy expert

### Structure

```text
agents/
└── my-subagent/
    ├── my-subagent.md
    └── knowledge/
        ├── index.md
        └── domain.md
```

## Plugins

### What They Are

Plugins are distributable packages that contain agents, commands, and skills.
They're the unit of distribution and installation.

### When to Use

- Packaging related components
- Distribution to others
- Organizing project-specific extensions
- Creating shareable toolkits

### Characteristics

- Contains multiple component types
- Has plugin.json metadata
- Installable via `/plugin add`
- Can depend on other plugins
- Self-contained and portable

### Example Use Cases

- Testing toolkit plugin
- CI/CD automation plugin
- Framework-specific plugin (React, Django)
- Organization standards plugin

### Structure

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/
├── commands/
├── skills/
├── README.md
└── .gitignore
```

## Hooks

### What They Are

Hooks are shell commands that execute automatically at specific lifecycle
events. Unlike other extensions that rely on LLM judgment, hooks provide
deterministic control - things that MUST happen, every time.

### When to Use

- Actions that must ALWAYS happen (not "should" happen)
- Automatic formatting after file edits
- Logging/audit trails for compliance
- Blocking dangerous operations
- Custom notifications
- Integration with external tools

### Characteristics

- Triggered automatically (not user-invoked)
- Deterministic (same input = same output)
- Execute shell commands
- Receive JSON input via stdin
- Can block operations (PreToolUse) with non-zero exit
- Configured in settings.json, not as separate files

### Example Use Cases

- Auto-format code after Write/Edit (PostToolUse)
- Block writes to .env files (PreToolUse)
- Log all Bash commands for compliance (PostToolUse)
- Desktop notifications when Claude needs input (Notification)
- Security scanning before commits (PreToolUse)

### Configuration

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write \"$FILE\""
          }
        ]
      }
    ]
  }
}
```

### Hooks vs Commands/Skills

| Aspect | Hooks | Commands/Skills |
|--------|-------|-----------------|
| **Trigger** | Automatic | User-invoked |
| **Control** | Deterministic | LLM-guided |
| **Purpose** | Enforcement | Workflows |
| **Execution** | Shell commands | Claude orchestration |

**Key insight:** Use hooks when something MUST happen. Use commands/skills
when something SHOULD happen based on context and judgment.

## Decision Examples

### "I want to automate deployments"

#### Recommendation: Skill

Deployments are procedural (run scripts, check status, verify). A skill
can contain deployment scripts and be invoked by commands or subagents.

### "I need help designing APIs"

#### Recommendation: Subagent

API design requires expertise, judgment, and understanding context. A
subagent can provide guidance based on best practices and project specifics.
The orchestrator spawns the API design expert when needed.

### "I want a code review workflow"

#### Recommendation: Command

A code review is a process: analyze changes, apply criteria, generate findings,
suggest fixes. This is a recipe/set of instructions. The command defines the
process; it can spawn a `code-review-expert` subagent for judgment and invoke
a `report-generator` skill for output.

### "I want to share my testing tools with my team"

#### Recommendation: Plugin

Multiple components (commands, skills, maybe a subagent) that need to be
distributed together. A plugin packages them for easy installation.

### "I want code to always be formatted after edits"

#### Recommendation: Hook

This is enforcement, not guidance. Every time Claude writes or edits a file,
prettier should run. No judgment needed - it must always happen. A PostToolUse
hook with a Write|Edit matcher ensures deterministic formatting.

## Combining Types

Often the best solution combines multiple types:

```text
my-testing-plugin/           # Plugin for distribution
├── agents/
│   └── test-advisor/        # Subagent: defines testing expertise
├── commands/
│   └── test.md              # Command: defines the testing process
└── skills/
    └── test-runner/         # Skill: provides execution capabilities
```

**How they work together:**

1. User invokes `/test` (Command)
2. Orchestrator reads the command (the recipe/instructions)
3. Orchestrator spawns `test-advisor` subagent for strategy decisions
4. Orchestrator invokes `test-runner` skill for execution
5. Plugin packages it all for distribution

**The command is the recipe** - it defines what happens. Skills provide execution
capabilities. Subagents provide specialized expertise. The orchestrator (Claude Code)
reads the command and performs the work, spawning subagents as needed.
