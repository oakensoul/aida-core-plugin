---
name: init-aida
description: Initialize AIDA memory and knowledge systems
---

# Initialize AIDA

Set up your personal AIDA system for the first time.

## Process

### 1. Welcome
Greet the user and explain what's about to happen.

### 2. Create Directory Structure
```bash
mkdir -p ~/.claude/memory
mkdir -p ~/.claude/memory/history
mkdir -p ~/.claude/knowledge
mkdir -p ~/.claude/config
```

### 3. Initialize Memory Files

**~/.claude/memory/context.md:**
```markdown
# Current Context
Last Updated: {timestamp}

## Current Focus
Nothing set yet. Run /start-day to begin.

## Active Projects
No projects tracked yet.

## Pending Items
- Initialize your knowledge base
- Set up your first project
```

**~/.claude/memory/decisions.md:**
```markdown
# Decision Log

Decisions are logged here with full context.

## Format
Each decision includes:
- Date and title
- Context (why this came up)
- Decision (what was decided)
- Rationale (why this choice)
- Alternatives considered
- Expected impact

---
```

### 4. Initialize Knowledge Files

**~/.claude/knowledge/system.md:**
Ask user questions to populate:
- Operating system
- Primary directories (Development, Documents, etc.)
- Tools and applications used
- Backup locations
- Important paths

**~/.claude/knowledge/preferences.md:**
Ask about:
- Work style preferences
- Communication preferences
- Scheduling preferences
- Organizational preferences

**~/.claude/knowledge/projects.md:**
```markdown
# Active Projects

## Format
Each project should include:
- Name and description
- Current status
- Key files/directories
- Important notes

---

## Getting Started

No projects yet. When you start working on something, 
I'll help you track it here.
```

### 5. Confirm Setup
```
Setup complete! Your AIDA system is ready.

Created:
✓ ~/.claude/memory/ (context and decision tracking)
✓ ~/.claude/knowledge/ (your personal knowledge base)
✓ ~/.claude/config/ (settings)

Next steps:
1. Run /start-day to begin your first day
2. Use /remember to start building your knowledge
3. Customize your knowledge files as needed

Let's get started!
```
