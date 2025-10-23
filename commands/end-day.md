---
name: end-day
description: End of day routine - summarize work, prepare for tomorrow
---

# End Day

Wrap up your day, log progress, and prepare for tomorrow.

## Process

### 1. Review Today's Work
- What was accomplished?
- What's still pending?
- Any unexpected developments?

### 2. Log Progress
- Update `~/.claude/memory/context.md`
- Add significant events to history
- Archive completed items

### 3. Update Projects
- Update project statuses in `~/.claude/knowledge/projects.md`
- Note any blockers or changes

### 4. Prepare for Tomorrow
- Carry over unfinished priorities
- Note what needs attention tomorrow
- Set expectations

### 5. Archive to History
- If it's month-end, archive context to `history/YYYY-MM.md`

## Output Format
```
{Closing based on personality}

TODAY'S SUMMARY:
✓ {Completed item}
✓ {Completed item}
⚠ {Incomplete item - reason}

TOMORROW'S FOCUS:
1. {Carried over priority}
2. {New priority}
3. {Scheduled item}

{Personalized closing remark}
```
