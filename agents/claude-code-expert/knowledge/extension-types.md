---
type: reference
title: Extension Types Decision Guide
description: How to choose between agents, commands, skills, and plugins
---

# Extension Types

Claude Code supports four types of extensions, each designed for different
use cases. This guide helps you choose the right type.

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
Does it need domain expertise or conversational interaction?
    │
    ├─ YES → Agent
    │
    ▼ NO
    │
Does it need scripts, templates, or reusable automation?
    │
    ├─ YES → Skill
    │
    ▼ NO
    │
Is it a simple user-invoked action?
    │
    └─ YES → Command
```

## Extension Types Compared

| Aspect         | Command     | Skill          | Agent            | Plugin       |
| -------------- | ----------- | -------------- | ---------------- | ------------ |
| **Purpose**    | User action | Automation     | Expert guidance  | Distribution |
| **Invocation** | `/command`  | Auto or manual | Task or subagent | Container    |
| **State**      | Stateless   | Stateless      | Context-aware    | N/A          |
| **Scripts**    | No          | Yes            | Via skills       | Contains all |
| **Knowledge**  | Minimal     | References     | Knowledge dir    | All types    |

## Commands

### What They Are

Commands are user-invoked actions that perform a specific task. They're the
simplest extension type.

### When to Use

- Simple, single-purpose actions
- Actions that don't require scripts
- Entry points that delegate to skills
- Quick utilities

### Characteristics

- Invoked with `/command-name`
- Defined in a single `.md` file
- Can specify allowed tools
- Can accept arguments

### Example Use Cases

- `/deploy` - Deploy current project
- `/review` - Start code review
- `/test` - Run test suite
- `/docs` - Generate documentation

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

## Agents

### What They Are

Agents are expert personas with domain knowledge. They provide guidance,
make decisions, and can use skills to accomplish tasks.

### When to Use

- Domain expertise needed
- Conversational interaction
- Complex decision-making
- Tasks requiring context
- Advisory or consultative roles

### Characteristics

- Have a knowledge directory
- Can use multiple skills
- Maintain conversation context
- Can be spawned as subagents
- Provide expert guidance

### Example Use Cases

- Code review expert
- Security advisor
- Architecture consultant
- Documentation specialist
- Test strategy expert

### Structure

```text
agents/
└── my-agent/
    ├── my-agent.md
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

## Decision Examples

### "I want to automate deployments"

#### Recommendation: Skill

Deployments are procedural (run scripts, check status, verify). A skill
can contain deployment scripts and be invoked by commands or agents.

### "I need help designing APIs"

#### Recommendation: Agent

API design requires expertise, judgment, and understanding context. An
agent can provide guidance based on best practices and project specifics.

### "I want a quick way to format code"

#### Recommendation: Command

Simple action, single purpose, delegates to a formatter. A command is
the lightest-weight option.

### "I want to share my testing tools with my team"

#### Recommendation: Plugin

Multiple components (commands, skills, maybe an agent) that need to be
distributed together. A plugin packages them for easy installation.

## Combining Types

Often the best solution combines multiple types:

```text
my-testing-plugin/           # Plugin for distribution
├── agents/
│   └── test-advisor/        # Agent for test strategy
├── commands/
│   └── test.md              # Command entry point
└── skills/
    └── test-runner/         # Skill for execution
```

The command provides the entry point, the skill does the work, the agent
provides expertise, and the plugin packages it all together.
