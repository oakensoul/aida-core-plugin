---
name: start-day
description: Begin your daily workflow - review yesterday, plan today
---

# Start Day

Your morning routine to set context and priorities for the day.

## Process

### 1. Check Memory
- Read `~/.claude/memory/context.md`
- Review what happened yesterday
- Identify any pending items

### 2. Check Today's Schedule
- Look for daily note: `~/Knowledge/Obsidian-Vault/Daily/YYYY-MM-DD.md`
- Read scheduled tasks and events
- If daily note doesn't exist, offer to create it

### 3. Review Active Projects
- Read `~/.claude/knowledge/projects.md`
- Identify projects needing attention
- Check for blockers or urgent items

### 4. Generate Priorities
- Analyze pending work
- Consider deadlines and importance
- Suggest top 3-5 priorities for today

### 5. Update Context
- Update `~/.claude/memory/context.md` with today's plan
- Note focus areas
- Set expectations

## Output Format
```
{Greeting based on personality}

YESTERDAY:
{Summary of what happened}

TODAY'S PRIORITIES:
1. {Top priority with context}
2. {Second priority}
3. {Third priority}

ACTIVE PROJECTS:
- {Project}: {Status}
- {Project}: {Status}

{Personalized question or prompt}
```

## File Initialization

If files don't exist, offer to create them:
- Create `~/.claude/memory/context.md` with template
- Create `~/.claude/knowledge/projects.md` with template
- Create daily note if needed
