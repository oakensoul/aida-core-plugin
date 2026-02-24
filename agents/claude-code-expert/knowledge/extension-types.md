---
type: reference
title: Extension Types Decision Guide
description: How to choose between agents, skills, plugins, and hooks
---

# Extension Types

Claude Code supports multiple extension types, each designed for different
use cases. This guide helps you choose the right type.

**See also:** `framework-design-principles.md` for architectural standards and
quality criteria for each type.

## The Framework: WHO / HOW / CONTEXT / MEMORY / AUTOMATION

| Type | Role | Contains |
| ---- | ---- | -------- |
| **Subagent** | WHO | Identity, expertise, judgment, quality standards |
| **Skill** | HOW | Process definitions, execution capabilities (scripts, templates) |
| **Knowledge** | CONTEXT | Facts, schemas, patterns (loaded with extensions) |
| **CLAUDE.md** | MEMORY | Project/user conventions (always loaded) |
| **Plugin** | DISTRIBUTION | Container for subagents, skills, knowledge |
| **Hooks** | AUTOMATION | Shell commands triggered on lifecycle events |

**Key insight:** Claude Code (the orchestrator) is the primary agent. All extensions
are inert definitions that the orchestrator reads and acts upon. Subagents are
specialists spawned for specific expertise.

**See also:** `framework-design-principles.md` for Context Layering - how these
sources combine when processing requests.

## Quick Decision Tree

```text
Start Here
    |
    v
Is this a distributable package of multiple components?
    |
    +- YES -> Plugin
    |
    v NO
    |
Should it run AUTOMATICALLY on lifecycle events (not user-invoked)?
    |
    +- YES -> Hook (deterministic automation)
    |
    v NO
    |
Does it need domain expertise to DEFINE (not just use)?
    |
    +- YES -> Subagent (expertise definition)
    |
    v NO
    |
Is it a user-invoked process, automation workflow, or reusable capability?
    |
    +- YES -> Skill (process definition + execution)
```

**Note:** Skills can be simple entry points (user-invocable) or complex
automation with scripts and templates. The question is where the definition
lives, not what gets used during execution.

## Extension Types Compared

| Aspect | Skill | Subagent | Plugin |
| ------ | ----- | -------- | ------ |
| **Purpose** | Process + execution | Expertise | Distribution |
| **Analogy** | Recipe + kitchen tools | Specialist chef | Cookbook |
| **Invocation** | `/skill` or via agent | Via Task tool | Container |
| **State** | Stateless | Context-aware | N/A |
| **Scripts** | Yes | Via skills | Contains all |
| **Complexity** | Simple to complex | Domain-focused | Bundles all |

## Skills

### What They Are

Skills are **process definitions and execution capabilities**. They define what
should happen when invoked and provide the automation to make it happen. Skills
range from simple user-invocable entry points to complex automation workflows
with scripts, templates, and references.

### When to Use

- User-invoked processes of any complexity
- Workflows that combine thinking and doing steps
- Entry points that orchestrate other skills and agents
- Automation workflows with scripts and templates
- Reusable functionality across agents

### Characteristics

- Can be invoked with `/skill-name` (when user-invocable)
- Can execute Python scripts
- Can use Jinja2 templates
- Have reference documentation
- Can define multi-step processes
- Can spawn agents for expert judgment
- Can specify allowed tools and accept arguments

### What Skills Can Contain

- **Process steps**: "Analyze X", "Evaluate against criteria", "Decide Y"
- **Script invocations**: Python scripts for automation
- **Agent spawns**: "Spawn the security expert to review"
- **Templates**: Jinja2 templates for generated content
- **Decision criteria**: "If TypeScript project, do X; otherwise do Y"
- **Argument hints**: User-facing help for invocation

### Example Use Cases

- `/deploy` - Analyze environment, decide strategy, execute deployment
- `/review` - Apply review criteria, evaluate code, generate report
- `/setup` - Detect project type, gather requirements, configure
- Project configuration with auto-detection
- Code generation with templates
- API integration
- Build automation

### Structure

```text
skills/
+-- my-skill/
    +-- SKILL.md
    +-- scripts/
    |   +-- action.py
    +-- references/
    |   +-- workflow.md
    +-- templates/
        +-- template.jinja2
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
+-- my-subagent/
    +-- my-subagent.md
    +-- knowledge/
        +-- index.md
        +-- domain.md
```

## Plugins

### What They Are

Plugins are distributable packages that contain agents and skills.
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
+-- .claude-plugin/
|   +-- plugin.json
+-- agents/
+-- skills/
+-- README.md
+-- .gitignore
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

### Hooks vs Skills

| Aspect | Hooks | Skills |
| ------ | ----- | ------ |
| **Trigger** | Automatic | User-invoked |
| **Control** | Deterministic | LLM-guided |
| **Purpose** | Enforcement | Workflows |
| **Execution** | Shell commands | Claude orchestration |

**Key insight:** Use hooks when something MUST happen. Use skills
when something SHOULD happen based on context and judgment.

## Decision Examples

### "I want to automate deployments"

#### Recommendation: Skill

Deployments are procedural (run scripts, check status, verify). A skill
can contain deployment scripts and be invoked by users or subagents.

### "I need help designing APIs"

#### Recommendation: Subagent

API design requires expertise, judgment, and understanding context. A
subagent can provide guidance based on best practices and project specifics.
The orchestrator spawns the API design expert when needed.

### "I want a code review workflow"

#### Recommendation: Skill

A code review is a process: analyze changes, apply criteria, generate findings,
suggest fixes. A skill defines the process and can spawn a `code-review-expert`
subagent for judgment and invoke scripts for output generation.

### "I want to share my testing tools with my team"

#### Recommendation: Plugin

Multiple components (skills, maybe a subagent) that need to be distributed
together. A plugin packages them for easy installation.

### "I want code to always be formatted after edits"

#### Recommendation: Hook

This is enforcement, not guidance. Every time Claude writes or edits a file,
prettier should run. No judgment needed - it must always happen. A PostToolUse
hook with a Write|Edit matcher ensures deterministic formatting.

## Combining Types

Often the best solution combines multiple types:

```text
my-testing-plugin/           # Plugin for distribution
+-- agents/
|   +-- test-advisor/        # Subagent: defines testing expertise
+-- skills/
    +-- test/                # Skill: defines the testing process
    +-- test-runner/         # Skill: provides execution capabilities
```

**How they work together:**

1. User invokes `/test` (Skill)
2. Orchestrator reads the skill (the process definition)
3. Orchestrator spawns `test-advisor` subagent for strategy decisions
4. Orchestrator invokes `test-runner` skill for execution
5. Plugin packages it all for distribution

**The skill is the entry point** - it defines what happens. Other skills provide
execution capabilities. Subagents provide specialized expertise. The orchestrator
(Claude Code) reads the skill and performs the work, spawning subagents as needed.
