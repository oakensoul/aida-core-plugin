# Claude Code Extension Design Principles

This document defines the architecture and quality standards for Claude Code extensions.
It serves as the authoritative reference for the claude-code-expert agent's expertise.

## The Four Extension Types

### Agent (WHO)

Agents represent **expertise and judgment**. They are domain experts spawned to apply
knowledge to problems.

**Contains:**
- Identity and persona
- Expertise areas and domains
- Judgment frameworks (how they think about trade-offs)
- Quality standards (good enough vs excellent)
- Capabilities (what they can do)

**Does NOT contain:**
- Step-by-step procedures
- Script invocations
- Output format specifications (caller provides these)

**Analogy:** Hiring a consultant. You describe the problem; they apply expertise.

### Command (WHAT)

Commands are **entry points**. They capture user intent and route to handlers.

**Contains:**
- Argument hints and descriptions
- Routing to appropriate skill
- Tool restrictions if needed
- User-facing help text

**Does NOT contain:**
- Business logic
- Multi-step workflows
- Direct file operations

**Analogy:** A meeting request. "I need help with X" - not the methodology for X.

### Skill (HOW)

Skills provide **execution capabilities**. They are the operational playbook.

**Contains:**
- Activation triggers
- Workflow phases (get-questions, execute)
- Script invocations and parameters
- Output contracts for agent spawning
- Templates and path resolution

**Does NOT contain:**
- Domain expertise ("why X is better than Y")
- Best practices (unless operational)
- Quality judgments

**Analogy:** An operations manual. Anyone trained on it can execute the workflow.

### Knowledge (CONTEXT)

Knowledge is **reference material**. Facts, patterns, and examples that inform decisions.

**Contains:**
- Schemas and specifications
- Design patterns and anti-patterns
- Best practices (as principles, not procedures)
- Examples of good vs bad implementations
- Decision criteria

**Does NOT contain:**
- Step-by-step procedures
- Orchestration logic
- User-facing commands

**Analogy:** Reference books on a consultant's shelf.

---

## The Consultant Rule

When you hire an expert, you don't give them a procedure manual.

**You give them:**
- Project context (the system, constraints)
- The specific problem ("We need X")
- Output format expectations ("Provide a design document")

**They bring:**
- Judgment (when to break rules, what trade-offs to make)
- Pattern recognition ("This looks like problem type X")
- Quality standards (what "good" looks like to them)

This is how agents should work. The orchestrator (skill) provides context and format;
the agent applies expertise.

---

## Quality Standards: Agents

### What Belongs

```markdown
## Your Expertise
You understand X deeply. You know:
- The principles behind Y
- The trade-offs between A and B
- When rules should be broken

## Your Judgment
When evaluating X, you consider:
- [Quality dimension]: [what good looks like]

## Your Standards
- [Standard]: [rationale]
```

### What Does NOT Belong

```markdown
## BAD: Procedural Steps
1. Run `python script.py --get-questions`
2. Parse the JSON output
3. Use AskUserQuestion if needed

## BAD: Output Contracts
Return JSON: { "files": [...], "validation": {...} }
```

### Good Enough

- Clear identity statement
- Expertise areas defined
- References knowledge files
- Accepts output format from caller

### Excellent

- Rich judgment framework
- Explicit quality standards
- "Good enough" vs "excellent" criteria defined
- Expertise informs decisions without dictating steps

---

## Quality Standards: Commands

### What Belongs

- Argument hint and description
- Routing to appropriate skill
- Tool restrictions if needed

### What Does NOT Belong

- Business logic
- Multi-step workflows
- Direct file operations

### Good Enough

- Correctly routes to skill
- Clear argument hint
- Proper frontmatter

### Excellent

- Pure delegation (no logic)
- Clear user-facing description
- Appropriate tool restrictions

---

## Quality Standards: Skills

### What Belongs

- Activation triggers (when this skill is relevant)
- Workflow phases (get-questions, execute)
- Script invocations and parameters
- Output contracts for agent spawning
- Path resolution for resources

### What Does NOT Belong

- Domain expertise ("why X is better than Y")
- Best practices (unless operational)
- Quality judgments

### Good Enough

- Clear activation criteria
- Working script invocations
- Basic workflow documented

### Excellent

- Two-phase API pattern (get-questions → execute)
- Complete output contracts for agent spawning
- Error handling documented
- Resources clearly organized (scripts/, templates/, references/)

---

## Quality Standards: Knowledge

### What Belongs

- Schemas and specifications
- Design patterns with rationale
- Anti-patterns with explanations
- Decision criteria ("when to use X vs Y")
- Examples of good vs poor implementations

### What Does NOT Belong

- Step-by-step procedures
- Script invocations
- User-facing commands

### Good Enough

- Accurate information
- Clear organization
- Referenced by agent

### Excellent

- Decision trees for choosing options
- Before/after examples
- Common mistakes explained
- Cross-references to related knowledge

---

## Quality Standards: Plugins

### What Belongs

- Plugin manifest (plugin.json)
- Bundled agents, commands, skills
- README documentation
- Proper directory structure

### What Does NOT Belong

- User-specific configuration
- Secrets or credentials

### Good Enough

- Valid plugin.json with required fields
- At least one agent, command, or skill
- Basic README

### Excellent

- Comprehensive README with examples
- Well-organized component structure
- Version documented
- Marketplace metadata complete

---

## Quality Standards: CLAUDE.md

### What Belongs

- Project-specific instructions
- Coding conventions
- Tool preferences
- Workflow guidance

### What Does NOT Belong

- Secrets or credentials
- User-specific paths (use ~ expansion)
- Temporary notes

### Good Enough

- Accurate project description
- Key conventions documented

### Excellent

- Comprehensive but concise
- Organized by topic
- Updated with project evolution
- Includes examples of preferred patterns
