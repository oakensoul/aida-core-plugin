---
type: reference
title: Extension Design Patterns
description: Best practices and common patterns for Claude Code extensions
---

# Design Patterns

This document covers best practices and common patterns for designing
Claude Code extensions.

## General Principles

### 1. Single Responsibility

Each extension should do one thing well:

- Skills: One capability or workflow
- Agents: One domain of expertise

### 2. Composability

Design extensions to work together:

- Skills can be used by multiple agents
- Skills can delegate to other skills
- Plugins can bundle related components

### 3. Progressive Disclosure

Start simple, add complexity as needed:

- Infer defaults where possible
- Ask only necessary questions
- Provide sensible defaults

### 4. Documentation First

Write clear documentation:

- Every extension has a description
- Include usage examples
- Document expected behavior

## Skill Patterns

### Argument Handling (User-Invocable Skills)

Use clear argument hints for user-invocable skills:

```yaml
argument-hint: "[target] [--verbose] [--dry-run]"
user-invocable: true
```

Document each argument in the skill body.

### Tool Restrictions

Restrict tools when security matters:

```yaml
allowed-tools: "Read,Write,Bash"  # Specific tools
allowed-tools: "*"                 # All tools (default)
```

### Two-Phase API

For interactive operations, use two phases:

#### Phase 1: Get Questions

```python
def get_questions(context):
    # Analyze context
    # Infer what we can
    # Return questions for unknowns
    return {"questions": [...], "inferred": {...}}
```

#### Phase 2: Execute

```python
def execute(context, responses):
    # Merge inferred + responses
    # Perform operation
    return {"success": True, "message": "..."}
```

**Why:** Allows inference to minimize questions, enables dry-runs.

### Script Organization

Organize scripts by function:

```text
scripts/
├── main.py           # Entry point
├── operations/       # Operation implementations
│   ├── create.py
│   ├── validate.py
│   └── list.py
└── utils/            # Shared utilities
    ├── files.py
    └── validation.py
```

### Template Usage

Use Jinja2 templates for generated content:

```jinja2
---
type: {{ type }}
name: {{ name }}
version: {{ version }}
---

# {{ name | replace("-", " ") | title }}

{{ description }}
```

**Why:** Separates structure from logic, easy to modify.

### Reference Documentation

Create references for complex workflows:

```text
references/
├── create-workflow.md    # Step-by-step process
├── validation-rules.md   # What gets validated
└── schemas.md            # Field definitions
```

Load references dynamically based on operation.

## Agent Patterns

### Knowledge Organization

Structure knowledge for efficient retrieval:

```text
knowledge/
├── index.md              # Catalog and routing
├── domain-overview.md    # High-level concepts
├── specific-topic.md     # Deep dives
└── examples/             # Example scenarios
```

### Index Pattern

The index.md should help find the right document:

```markdown
# Knowledge Index

| Question | Document |
|----------|----------|
| "What is X?" | domain-overview.md |
| "How do I Y?" | specific-topic.md |
| "Show me an example" | examples/ |
```

### Skill Composition

Agents should use skills for actions:

```markdown
## Skills

This agent uses:
- **skill-a** - For operation A
- **skill-b** - For operation B
```

**Why:** Agents provide expertise, skills provide automation.

### Decision Documentation

Document decision processes:

```markdown
## Decision Process

When user asks X:
1. Check condition A → recommend option 1
2. Check condition B → recommend option 2
3. Default → ask clarifying question
```

## Plugin Patterns

### Directory Structure

Standard plugin layout:

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # Required: plugin metadata
├── agents/               # Optional: plugin agents
├── skills/               # Optional: plugin skills
├── templates/            # Optional: shared templates
├── README.md             # Required: documentation
├── CHANGELOG.md          # Recommended: version history
└── .gitignore            # Recommended: git ignores
```

### Plugin Metadata

Essential plugin.json fields:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "What this plugin does",
  "author": "Author name",
  "repository": "https://github.com/...",
  "keywords": ["keyword1", "keyword2"],
  "dependencies": {}
}
```

### Internal References

Reference components within the plugin:

```markdown
# In a command

Invoke the `../skills/my-skill` skill for this operation.
```

### Versioning Strategy

Follow semantic versioning:

- **Major:** Breaking changes
- **Minor:** New features
- **Patch:** Bug fixes

Bump versions using:

```bash
/aida plugin version my-plugin minor
```

## Anti-Patterns

### Avoid: Monolithic Skills

**Bad:**

```markdown
# SKILL.md
[500 lines of deployment logic with no script delegation]
```

**Good:**

```markdown
# SKILL.md
Delegates complex automation to scripts/ and spawns agents for expertise
```

### Avoid: Hardcoded Paths

**Bad:**

```python
config_path = "/Users/me/.claude/config.yml"
```

**Good:**

```python
config_path = get_claude_dir() / "config.yml"
```

### Avoid: Over-Questioning

**Bad:**

```python
questions = [
    "Project name?",
    "Version?",
    "Author?",
    "License?",
    "Keywords?",
    # ... 20 more questions
]
```

**Good:**

```python
# Infer everything possible
inferred = detect_project_info()
# Only ask what we couldn't detect
questions = get_unanswered_questions(inferred)
```

### Avoid: Missing Error Handling

**Bad:**

```python
content = file.read()
data = json.loads(content)
```

**Good:**

```python
try:
    content = file.read()
    data = json.loads(content)
except FileNotFoundError:
    return {"success": False, "message": "File not found"}
except json.JSONDecodeError as e:
    return {"success": False, "message": f"Invalid JSON: {e}"}
```

## Testing Patterns

### Unit Tests

Test script functions:

```python
def test_to_kebab_case():
    assert to_kebab_case("Hello World") == "hello-world"
    assert to_kebab_case("API Handler") == "api-handler"
```

### Integration Tests

Test full workflows:

```python
def test_create_agent():
    result = execute({"operation": "create", "type": "agent", ...})
    assert result["success"]
    assert Path(result["path"]).exists()
```

### Manual Testing

Document manual test scenarios:

```markdown
## Test Scenarios

1. Create agent with minimal args
2. Create agent with all options
3. Validate existing agent
4. Version bump (patch/minor/major)
5. List with filters
```
