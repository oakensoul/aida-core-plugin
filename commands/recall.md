---
name: recall
description: Recall information from memory
---

# Recall

Search and retrieve information from your memory system.

## Usage
```
/recall $ARGUMENTS
```

## Examples
```
/recall what did I decide about databases
/recall recent decisions
/recall what happened last week
/recall project alpha status
```

## Search Locations

1. **Context** (`~/.claude/memory/context.md`) - Current state
2. **Decisions** (`~/.claude/memory/decisions.md`) - Decision log
3. **History** (`~/.claude/memory/history/*.md`) - Past months
4. **Knowledge** (`~/.claude/knowledge/*.md`) - Static info

## Process

1. Parse the query
2. Determine what to search (decisions, context, history, all)
3. Search relevant files
4. Present findings in chronological order
5. Provide links to detailed entries if needed
