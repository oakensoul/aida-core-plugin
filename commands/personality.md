---
name: personality
description: Set or change your AIDA personality
---

# Personality Command

**IMPORTANT**: This command requires you to execute bash commands. Do not just explain - actually run them!

## Usage
```
/personality jarvis
/personality list
/personality none
```

## Execution Instructions

### When user runs: `/personality <argument>`

**Step 1: Determine the action**

- If argument is empty → Show current personality and usage
- If argument is "list" → Execute list action
- If argument is "none" → Execute disable action
- Otherwise → Execute enable action with that personality name

---

### Action: Show Current (no argument)

**Run this command:**
```bash
if [ -f ~/.claude/config/personality.txt ]; then
    cat ~/.claude/config/personality.txt
else
    echo "none"
fi
```

**Then tell the user:**
```
Current personality: <result>

Usage:
  /personality jarvis   - Enable JARVIS personality
  /personality list     - Show available personalities  
  /personality none     - Disable personality
```

---

### Action: List Available Personalities

**Run this command to find installed personalities:**
```bash
ls -d ~/.claude/plugins/cache/aida-personality-* 2>/dev/null | sed 's|.*/aida-personality-||'
```

**Check current personality:**
```bash
cat ~/.claude/config/personality.txt 2>/dev/null || echo "none"
```

**Then show the user:**
```
Available AIDA personalities:

<list each found personality>
- <name> - <read description from plugin.json if available>
  Status: Installed

Current: <current personality>

To activate: /personality <name>
```

---

### Action: Disable Personality

**Run these commands:**
```bash
mkdir -p ~/.claude/config
rm -f ~/.claude/config/personality.txt
```

**Then tell the user:**
```
✓ Personality disabled

AIDA will use neutral core behavior.
Restart Claude Code to apply this change.
```

---

### Action: Enable Personality (e.g., "jarvis")

**Step 1: Verify the personality plugin exists**

Run this command (replace <name> with the personality name):
```bash
test -d ~/.claude/plugins/cache/aida-personality-<name> && echo "exists" || echo "missing"
```

**If "missing":**
- Tell user: "Personality '<name>' is not installed"
- Run the list command to show available personalities
- Suggest: `/plugin install personality-<name>@aida`
- STOP here

**If "exists":**

**Step 2: Write the configuration**

Run these commands:
```bash
mkdir -p ~/.claude/config
echo "<name>" > ~/.claude/config/personality.txt
```

**Step 3: Verify it was written**
```bash
cat ~/.claude/config/personality.txt
```

**Step 4: Tell the user:**
```
✓ Personality set to: <name>

The <name> personality will be loaded at the start of your next Claude Code session.

To activate now:
1. Exit Claude Code (type 'exit' or Ctrl+D)
2. Start Claude Code again

The session-start hook will load your personality automatically.
```

---

## Implementation Notes

- **You MUST execute the bash commands** - use the bash tool
- The personality is loaded by the session-start hook (see hooks/session-start.sh)
- Config file location: `~/.claude/config/personality.txt`
- Plugin location: `~/.claude/plugins/cache/aida-personality-<name>/`
- Changes require Claude Code restart to take effect

## Error Handling

- If bash commands fail, show the error to the user
- If personality doesn't exist, show available options
- If config directory can't be created, explain the issue