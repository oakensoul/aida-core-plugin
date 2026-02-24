---
type: research
title: "User Perspective Analysis: Decomposing claude-code-management"
author: shell-systems-ux-designer
date: 2026-02-24
status: complete
---

# User Perspective Analysis: Decomposing claude-code-management

Evaluation of the proposed decomposition from the standpoint of real AIDA users
-- developers who use `/aida` commands to manage Claude Code extensions.

## Executive Summary

The decomposition is **a clear UX improvement** for most workflows. The current
three-layer indirection (`/aida` -> `claude-code-management` -> internal dispatch)
is invisible to users at the command level but creates noticeable latency, vague
error messages, and a monolithic help surface. The proposed entity-focused routing
(`/aida agent [verb]` -> `agent-manager`) aligns the internal architecture with
how users already think about their commands.

However, the proposal introduces naming concerns and a risk of subcommand
proliferation that deserve careful attention. The recommendations below address
both.

---

## 1. Current UX Audit

### What Users See Today

```text
/aida help
```

The help text already presents commands in entity-focused groups:

```text
### Extension Management
- /aida agent [create|validate|version|list]
- /aida skill [create|validate|version|list]
- /aida plugin [scaffold|create|validate|version|list|add|remove]
- /aida hook [list|add|remove|validate]

### CLAUDE.md Management
- /aida claude [create|optimize|validate|list]
```

**Key observation:** The user-facing command grammar is already entity-first
(`/aida agent create`, `/aida skill list`). Users already think in terms of
entity + verb. The internal routing through `claude-code-management` is an
implementation detail they never see -- but they feel its effects.

### Where the Current Architecture Hurts Users

1. **Latency**: Three layers of indirection means more processing before the
   user's actual operation begins. Each routing hop involves reading SKILL.md
   files, parsing context, and dispatching.

2. **Error message attribution**: When `manage.py` fails, the error context
   refers to `claude-code-management` internals. Users see messages about
   `target`, `context`, and `operation` fields rather than their original
   command.

3. **Monolithic help**: The `claude-code-management` SKILL.md is 600+ lines
   covering agents, skills, plugins, hooks, AND CLAUDE.md files. When the
   orchestrator loads this, it consumes substantial context window for every
   management operation, even if the user only asked to list their agents.

4. **Special-case routing**: `plugin scaffold` must be caught BEFORE general
   extension routing (line 94-96 of `aida/SKILL.md`). This is fragile and
   creates a class of bugs users cannot diagnose.

---

## 2. Command Discoverability and Cognitive Load

### Current State: Good

The existing command surface is well-designed from a discoverability standpoint:

- `/aida` with no args shows help -- correct default behavior
- Commands follow a consistent `entity verb` pattern
- Help text groups commands by domain (config, extensions, session, CLAUDE.md)
- "Getting Started" section provides an on-ramp for new users

### Proposed State: Equally Good (Potentially Better)

The decomposition does not change the user-facing command grammar. Users will
still type `/aida agent create "description"`. The routing just becomes direct
instead of going through a middleman.

**Potential improvement**: Each manager skill can provide its own focused help
text. Instead of one massive help dump, `/aida agent help` could show only
agent-relevant commands and examples, reducing cognitive load for users who
already know what entity they're working with.

### Cognitive Load Analysis

| Aspect | Current | Proposed | Verdict |
| ------ | ------- | -------- | ------- |
| Commands to memorize | Same | Same | Neutral |
| Help text length | One large block | Modular sections | Better |
| Error specificity | Generic | Entity-specific | Better |
| Mental model | "management does everything" | "each entity has its handler" | Better |

---

## 3. Common Workflow Analysis

### Workflow 1: Create an Agent

**Current (3 layers)**:

```text
User: /aida agent create "handles database migrations"
  -> aida SKILL.md: parse type=agent, operation=create
  -> invoke claude-code-management skill
  -> claude-code-management SKILL.md: parse type=agent, operation=create
  -> manage.py: is_hook? no. is_claude_md? no. -> extensions.get_questions()
  -> (questions presented to user)
  -> manage.py: extensions.execute()
  -> Result returned through 3 layers back to user
```

**Proposed (2 layers)**:

```text
User: /aida agent create "handles database migrations"
  -> aida SKILL.md: parse entity=agent
  -> invoke agent-manager skill
  -> agent-manager: get_questions() -> execute()
  -> Result returned to user
```

**Improvement**: One fewer routing hop. The agent-manager's SKILL.md only
contains agent-relevant content, so the orchestrator loads less context and
can provide more specific error messages.

### Workflow 2: List All Extensions

A user wanting to see "everything I have" would run:

```text
/aida agent list
/aida skill list
/aida plugin list
/aida hook list
```

This is 4 commands in both architectures. Neither approach provides a
`/aida list --all` convenience. Consider adding one.

### Workflow 3: Validate Before Commit

```text
/aida agent validate --all
/aida skill validate --all
/aida claude validate
/aida hook validate
```

Again 4 commands. A `/aida validate --all` cross-cutting command would be
valuable. The decomposition makes this harder if not planned for -- each
manager would need to be invoked separately. Recommendation: keep a
"validate-all" capability at the aida dispatcher level that fans out to
each manager.

### Workflow 4: Plugin Scaffolding

**Current**: Special-case routing in `aida/SKILL.md` catches `plugin scaffold`
before it hits `claude-code-management`. This is documented with a warning
comment.

**Proposed**: The `plugin-manager` skill owns all plugin operations including
scaffold. No special-case routing needed. This is cleaner.

---

## 4. Naming Analysis

### Proposed Names and User Perception

| Proposed Name | User Clarity | Concern |
| ------------- | ------------ | ------- |
| `agent-manager` | Clear | None |
| `skill-manager` | Confusing | A "skill" that "manages skills" is recursive |
| `plugin-manager` | Clear | None |
| `hook-manager` | Clear | None |
| `claude-md-manager` | Awkward | "claude" is overloaded (brand vs file) |
| `marketplace-manager` | Clear | Is this needed at v1.0? |

### The "skill-manager" Problem

This is the biggest naming concern. In the AIDA framework, a Skill is a defined
extension type. Having `skills/skill-manager/SKILL.md` -- a skill that manages
skills -- is confusing for:

- **Developers reading the codebase**: "Is this the skill system itself?"
- **Users seeing error messages**: "skill-manager skill failed" is a mouthful
- **Documentation**: Writing about "the skill-manager skill" is awkward

**Alternatives considered**:

| Name | Pros | Cons |
| ---- | ---- | ---- |
| `skill-manager` | Consistent pattern | Recursive naming |
| `skill-ops` | Clear, short | Breaks `*-manager` consistency |
| `extension-skills` | Descriptive | Too long |
| `skill-admin` | Clear role | Inconsistent with others |

**Recommendation**: Accept the minor awkwardness of `skill-manager` for the
sake of naming consistency across all managers. The recursive naming is a
one-time learning cost, while inconsistent naming creates ongoing confusion.
Document it with a note: "Yes, the skill that manages skills is called
skill-manager."

### The "claude-md-manager" Problem

The name `claude-md-manager` conflates the brand "Claude" with the file
format "CLAUDE.md". Users might expect it to manage Claude (the AI) itself.

**Alternatives**:

| Name | Pros | Cons |
| ---- | ---- | ---- |
| `claude-md-manager` | Matches the file name | Brand confusion |
| `claudemd-manager` | Shorter | Still confusing |
| `memory-manager` | Matches framework concept | Conflicts with system memory |
| `config-docs-manager` | Descriptive | Too vague |

**Recommendation**: Keep `claude-md-manager` but ensure the help text and
error messages always reference "CLAUDE.md files" (with the .md suffix) to
disambiguate from the brand.

### The "marketplace-manager" Question

The issue README proposes 6 managers including `marketplace-manager`. Current
`claude-code-management` has no marketplace operations -- this appears to be
forward-looking scope.

**Recommendation**: Do not create `marketplace-manager` for v1.0 unless there
are concrete operations to put in it. Start with the 5 managers that have
existing functionality. Adding a 6th later is easy; removing a premature one
is awkward.

---

## 5. Progressive Disclosure

### New User Journey

A new user's typical path:

1. `/aida` or `/aida help` - See all available commands
2. `/aida status` - Check installation
3. `/aida config` - Set up
4. `/aida agent create "my first agent"` - First extension

**Assessment**: The decomposition does not change this journey. The help text
remains the same. The routing is more direct but invisible to the user. New
users are unaffected.

### Power User Journey

An experienced user's typical session:

1. `/aida agent create "security reviewer"` - Create extension
2. `/aida agent validate security-reviewer` - Validate it
3. `/aida claude optimize` - Optimize project docs
4. `/aida hook add "auto-format on write"` - Add automation

**Assessment**: Improved. Each operation loads only its manager's context,
leaving more context window for the user's actual work.

### Discoverability Layers

| Layer | Current | Proposed |
| ----- | ------- | -------- |
| `/aida` | Full help text | Full help text (unchanged) |
| `/aida agent` | Goes to claude-code-management | Could show agent-specific help |
| `/aida agent create` | Runs create flow | Runs create flow (unchanged) |

**Recommendation**: Each manager skill should provide entity-specific help
when invoked with no verb or with `help`:

```text
$ /aida agent
Available agent commands:
  create <description>   Create a new agent
  validate [name|--all]  Validate agent structure
  version <name> <bump>  Bump agent version
  list                   List all agents

Examples:
  /aida agent create "handles code reviews"
  /aida agent validate --all
```

This is a new UX capability the decomposition enables.

---

## 6. Error Recovery and Help Text

### Current Error Experience

When `manage.py` fails, users see errors like:

```text
Validation error: Missing required field 'type' in context
```

This leaks implementation details. The user typed `/aida agent create` -- they
should not need to know about context fields.

### Proposed Improvement

With entity-focused managers, errors can be more specific:

```text
Error: Could not create agent -- no description provided.

Usage: /aida agent create "description of what the agent does"

Example:
  /aida agent create "reviews Python code for security issues"
```

**Recommendation**: Each manager skill should define its own error templates
that reference the user's actual command, not internal context structures.

---

## 7. Subcommand Count: Better or Worse?

### The Question

Is 5-6 entity-focused managers better than one unified `claude-code-management`?

### User Perspective

Users **do not interact with managers directly**. They type `/aida agent create`,
not `/agent-manager create`. The number of internal skills is invisible. What
matters is:

1. **Command surface area**: Unchanged. Same commands, same verbs.
2. **Response quality**: Improved. More focused context per operation.
3. **Error specificity**: Improved. Entity-aware error messages.
4. **Help granularity**: Improved. Entity-specific help possible.

### Developer Perspective

Developers maintaining the plugin see more skills in the `skills/` directory:

```text
Current:                     Proposed:
skills/                      skills/
  aida/                        aida/
  claude-code-management/      agent-manager/
  create-plugin/               skill-manager/
  memento/                     plugin-manager/
  permissions/                 hook-manager/
                               claude-md-manager/
                               memento/
                               permissions/
```

This is more files but each is smaller and focused. The net complexity is lower
because the routing logic within each manager is trivial (no `is_hook_operation`
/ `is_claude_md_operation` dispatch).

### Verdict

The decomposition is **better** for both users and developers. Users get the
same command surface with better error messages and help text. Developers get
smaller, focused skills that are easier to maintain and test.

---

## 8. Cross-Cutting Concerns

### Operations That Span Entities

Some operations naturally span multiple entity types:

- **Validate all**: `/aida validate --all` should check agents, skills,
  plugins, hooks, and CLAUDE.md files
- **List all**: `/aida list` could show a summary across all types
- **Plugin operations**: Creating a component inside a plugin (e.g.,
  `/aida plugin add agent "my-agent"`) needs awareness of both plugins
  and agents

### Recommendation

Keep these cross-cutting operations at the `aida` dispatcher level. The
dispatcher can fan out to individual managers and aggregate results. This
is a natural role for the top-level routing skill and does not need a
"unified manager" middleman.

---

## 9. Summary of Recommendations

### Do

1. **Proceed with the decomposition** -- it aligns internal architecture
   with the existing user mental model
2. **Use consistent `*-manager` naming** for all entity managers, including
   `skill-manager` despite the recursive naming
3. **Add entity-specific help** to each manager (show focused help when
   entity is specified with no verb)
4. **Design entity-aware error messages** that reference the user's command,
   not internal context fields
5. **Keep cross-cutting operations** (`validate --all`, etc.) at the aida
   dispatcher level
6. **Absorb `create-plugin` into `plugin-manager`** -- users should not
   need to know that scaffolding and management are separate skills

### Do Not

1. **Do not create `marketplace-manager` yet** -- defer until concrete
   operations exist
2. **Do not change the user-facing command grammar** -- `/aida entity verb`
   is already well-designed
3. **Do not fragment shared utilities** -- keep `utils.py` shared, not
   duplicated per manager
4. **Do not require users to know manager names** -- these are internal
   routing targets, not user-facing concepts

### Consider

1. **`/aida validate --all`** as a cross-cutting convenience
2. **`/aida list`** as a summary across all entity types
3. **Per-entity help** (e.g., `/aida agent` with no verb shows agent help)
4. **Error message templates** per manager with user-command context

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Naming confusion (`skill-manager`) | Medium | Low | Document it, accept the cost |
| Shared code duplication | Medium | Medium | Keep shared `utils.py` as a library |
| Cross-cutting ops forgotten | Low | Medium | Add to aida dispatcher in this PR |
| Help text inconsistency | Medium | Low | Template-based help per manager |
| Breaking existing commands | Low | High | Keep command grammar unchanged |
