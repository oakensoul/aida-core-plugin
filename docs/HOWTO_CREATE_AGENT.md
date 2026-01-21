---
type: guide
title: "How to Create an Agent"
description: "Step-by-step guide to creating custom Claude Code agents"
audience: users
---

# How to Create an Agent

Agents are expert personas that Claude can become. Use them when you need specialized
expertise for specific domains like security review, API design, or database optimization.

## Quick Start

```bash
/aida agent create
```

AIDA will guide you through the process interactively.

## When to Create an Agent

Create an agent when you need:

- **Domain expertise** - Security auditor, performance engineer, accessibility expert
- **Consistent persona** - Code reviewer with specific standards
- **Reusable specialist** - Database expert you consult across projects

Don't create an agent for:

- Step-by-step procedures (use a [command](HOWTO_CREATE_COMMAND.md))
- Execution capabilities (use a [skill](HOWTO_CREATE_SKILL.md))
- One-off tasks (just ask Claude directly)

## Interactive Creation

### Step 1: Start the Wizard

```bash
/aida agent create
```

### Step 2: Describe Your Agent

AIDA will ask what kind of agent you want. Be specific:

```text
A security engineer who reviews code for OWASP vulnerabilities,
focuses on input validation and authentication, and provides
actionable remediation steps.
```

### Step 3: Choose Location

- **User** (`~/.claude/agents/`) - Available in all projects
- **Project** (`.claude/agents/`) - Only for current project

### Step 4: Review and Confirm

AIDA generates the agent definition. Review it and confirm to create.

## Agent Structure

After creation, your agent will have this structure:

```text
agents/
└── security-engineer/
    ├── security-engineer.md    # Agent definition
    └── knowledge/              # Optional reference docs
        └── owasp-top-10.md
```

## Agent Definition Format

```markdown
---
type: agent
name: security-engineer
description: Security expert for code review and vulnerability assessment
version: 0.1.0
tags:
  - security
  - review
---

# Security Engineer

You are a security engineer specializing in application security.

## Expertise

- OWASP Top 10 vulnerabilities
- Authentication and authorization patterns
- Input validation and sanitization
- Secure coding practices

## Approach

When reviewing code:
1. Identify potential attack vectors
2. Check for common vulnerabilities
3. Provide specific remediation steps
4. Reference relevant security standards

## Quality Standards

- Always explain WHY something is a vulnerability
- Provide code examples for fixes
- Prioritize findings by severity
```

## Using Your Agent

Once created, your agent is available via the Task tool:

```bash
# Claude will spawn your agent when appropriate
"Please have the security-engineer review this authentication code"
```

Or reference it in commands/skills you create.

## Adding Knowledge

Add reference documents to your agent's `knowledge/` directory:

```text
agents/security-engineer/knowledge/
├── owasp-top-10.md
├── auth-patterns.md
└── secure-coding-checklist.md
```

These documents provide context the agent can reference.

## Best Practices

### Do

- Focus on expertise and judgment, not procedures
- Define clear quality standards
- Include example scenarios
- Add relevant knowledge documents

### Don't

- Include step-by-step scripts (use skills)
- Define specific output formats (caller provides these)
- Make it too broad (specialized agents work better)

## Examples

### Code Reviewer

```bash
/aida agent create
# Description: "A code reviewer focused on readability, maintainability,
# and adherence to team coding standards"
```

### API Designer

```bash
/aida agent create
# Description: "An API design expert who follows REST best practices
# and ensures consistent, intuitive endpoint design"
```

### Performance Engineer

```bash
/aida agent create
# Description: "A performance specialist who identifies bottlenecks,
# suggests optimizations, and validates improvements with benchmarks"
```

## Troubleshooting

### Agent not showing up?

- Check it's in the correct location (`~/.claude/agents/` or `.claude/agents/`)
- Verify the YAML frontmatter is valid
- Restart Claude Code to reload agents

### Agent behaving unexpectedly?

- Review the agent definition for clarity
- Add more specific guidance in the Approach section
- Include examples of desired behavior

## Next Steps

- [Create a Command](HOWTO_CREATE_COMMAND.md) - Define procedures that use your agent
- [Create a Skill](HOWTO_CREATE_SKILL.md) - Add execution capabilities
- [Extension Framework](EXTENSION_FRAMEWORK.md) - Understand the architecture
