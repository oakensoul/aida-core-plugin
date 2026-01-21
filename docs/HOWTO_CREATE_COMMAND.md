---
type: guide
title: "How to Create a Command"
description: "Step-by-step guide to creating custom Claude Code commands"
audience: users
---

# How to Create a Command

Commands are user-invoked actions triggered with `/command-name`. They define procedures
and workflows - the instructions Claude follows to accomplish a task.

## Quick Start

```bash
/aida command create
```

AIDA will guide you through the process interactively.

## When to Create a Command

Create a command when you need:

- **Repeatable workflows** - Deploy process, release checklist
- **Multi-step procedures** - Code review with specific steps
- **Team standards** - Ensure everyone follows the same process

Don't create a command for:

- Domain expertise (use an [agent](HOWTO_CREATE_AGENT.md))
- Script execution (use a [skill](HOWTO_CREATE_SKILL.md))
- One-off tasks (just ask Claude directly)

## Interactive Creation

### Step 1: Start the Wizard

```bash
/aida command create
```

### Step 2: Describe Your Command

AIDA will ask what the command should do. Be specific:

```text
A code review command that checks for security issues,
performance problems, and code style violations, then
generates a summary report.
```

### Step 3: Choose Location

- **User** (`~/.claude/commands/`) - Available in all projects
- **Project** (`.claude/commands/`) - Only for current project

### Step 4: Review and Confirm

AIDA generates the command definition. Review it and confirm to create.

## Command Structure

Commands are single markdown files:

```text
commands/
└── review-code.md
```

Or with supporting files:

```text
commands/
└── review-code/
    ├── review-code.md      # Main command
    └── templates/          # Supporting templates
        └── report.md
```

## Command Definition Format

```markdown
---
type: command
name: review-code
description: Comprehensive code review with security and performance checks
version: 0.1.0
tags:
  - review
  - quality
arguments:
  - name: path
    description: File or directory to review
    required: false
    default: "."
---

# /review-code

Perform a comprehensive code review.

## Usage

\`\`\`bash
/review-code [path]
\`\`\`

## Process

### Step 1: Gather Context

1. Identify the files to review
2. Detect the programming language
3. Check for existing linting configuration

### Step 2: Security Review

1. Check for OWASP Top 10 vulnerabilities
2. Identify hardcoded secrets or credentials
3. Review input validation

### Step 3: Performance Review

1. Identify potential bottlenecks
2. Check for N+1 queries
3. Review memory usage patterns

### Step 4: Code Quality

1. Check adherence to project style guide
2. Identify code duplication
3. Review naming conventions

### Step 5: Generate Report

Create a summary with:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (nice to have)

## Output

Provide findings in this format:

\`\`\`markdown
## Code Review: [filename]

### Critical
- [ ] Issue description

### Warnings
- [ ] Issue description

### Suggestions
- [ ] Issue description
\`\`\`
```

## Using Your Command

Once created, invoke it with:

```bash
/review-code
/review-code src/api/
```

## Invoking Agents from Commands

Commands can spawn agents for specialized expertise:

```markdown
### Step 2: Security Review

Spawn the security-engineer agent to review for vulnerabilities:

> Use the security-engineer agent to analyze the code for security issues.
> Focus on authentication, input validation, and data exposure.
```

## Invoking Skills from Commands

Commands can use skills for execution:

```markdown
### Step 5: Generate Report

Use the report-generator skill to create the final report:

\`\`\`bash
python {skill:report-generator}/scripts/generate.py --format markdown
\`\`\`
```

## Best Practices

### Do

- Define clear, sequential steps
- Include decision points ("if X, then Y")
- Specify expected outputs
- Document arguments and usage

### Don't

- Include domain expertise (use agents)
- Write execution scripts inline (use skills)
- Make steps too vague ("review the code")

## Examples

### Deploy Command

```bash
/aida command create
# Description: "A deployment command that runs tests, builds the project,
# and deploys to staging with rollback capability"
```

### PR Review Command

```bash
/aida command create
# Description: "A pull request review command that checks code quality,
# runs tests, and generates a review summary"
```

### Documentation Command

```bash
/aida command create
# Description: "A documentation generator that creates API docs,
# README updates, and changelog entries from code changes"
```

## Troubleshooting

### Command not showing up?

- Check it's in the correct location (`~/.claude/commands/` or `.claude/commands/`)
- Verify the YAML frontmatter is valid
- Ensure the filename matches the command name

### Command not working as expected?

- Review steps for clarity and specificity
- Add more detail to ambiguous steps
- Include examples of expected behavior

## Next Steps

- [Create an Agent](HOWTO_CREATE_AGENT.md) - Add expertise your command can use
- [Create a Skill](HOWTO_CREATE_SKILL.md) - Add execution capabilities
- [Extension Framework](EXTENSION_FRAMEWORK.md) - Understand the architecture
