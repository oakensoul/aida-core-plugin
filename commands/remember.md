---
name: remember
description: Remember a fact, decision, or important information
---

# Remember

Store information in your personal memory system.

## Usage
```
/remember $ARGUMENTS
```

## Examples
```
/remember chose PostgreSQL over MongoDB for better transaction support
/remember meeting with Sarah revealed new requirements for reporting  
/remember bug in payment processor needs urgent fix
```

## Process

1. **Parse the input**: Understand what needs to be remembered
2. **Categorize**:
   - Decision? → Goes to decisions.md with full context
   - Update to current state? → Goes to context.md
   - Important fact? → Goes to context.md
3. **Store with timestamp**
4. **Confirm** what was stored

## Storage Locations

- **Decisions**: `~/.claude/memory/decisions.md`
- **Context**: `~/.claude/memory/context.md`
- **History**: `~/.claude/memory/history/YYYY-MM.md`

## Format for Decisions
```markdown
## YYYY-MM-DD: {Decision Title}

**Context**: {Why this came up}
**Decision**: {What was decided}  
**Rationale**: {Why this choice}
**Alternatives**: {What else was considered}
**Impact**: {Expected effects}
```

## Format for Context
```markdown
## {Category}
- {Timestamp}: {What happened or was decided}
```
