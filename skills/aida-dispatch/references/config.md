---
type: reference
title: "Config Action"
description: "Handles /aida config - Smart configuration flow with progressive disclosure"
---

# Config Action

Handles `/aida config` - Smart configuration flow with progressive disclosure.

## Quick Start

Three-step flow:

1. Detect current installation state
2. Build dynamic menu based on state
3. Execute selected action

---

## Progressive Disclosure

### Level 1: The Flow

#### Step 1: Detect State

```bash
python3 {base_directory}/scripts/detect.py
```

Parse JSON response:

```json
{
  "global_installed": true/false,
  "project_configured": true/false,
  "global_path": "/path/to/.claude" or null,
  "project_path": "/path/to/.claude" or null,
  "project_name": "current-directory-name",
  "project_root": "/absolute/path"
}
```

#### Step 2: Build Menu

Use `AskUserQuestion` with options based on detection:

```javascript
{
  "questions": [{
    "question": "What would you like to do?",
    "header": "AIDA Config",
    "options": [
      // Add based on state (see Level 2)
    ],
    "multiSelect": false
  }]
}
```

#### Step 3: Execute

Route to appropriate script based on user selection (see Level 2).

### Level 2: Menu Options

Build dynamic options array based on detection state:

#### If `!global_installed`

```javascript
{
  "label": "Set up AIDA globally",
  "description": "Install AIDA to ~/.claude/ for use across all projects"
}
```

→ Execute: Two-phase installation (see Level 3)

#### If `global_installed && !project_configured`

```javascript
{
  "label": "Configure this project",
  "description": "Set up AIDA for this specific project"
}
```

→ Execute: Two-phase project configuration (see Level 3)

#### If `global_installed`

```javascript
{
  "label": "Update global preferences",
  "description": "Modify global AIDA settings"
}
```

→ Execute: Two-phase installation with update context (see Level 3)

#### If `project_configured`

```javascript
{
  "label": "Update project settings",
  "description": "Modify this project's AIDA configuration"
}
```

→ Execute: Two-phase project configuration with update context (see Level 3)

#### Always include

```javascript
{
  "label": "View current configuration",
  "description": "Show AIDA settings without making changes"
}
```

→ Display contents of detected config files

### Level 3: Script Execution

#### Global Installation: `install.py` (Fact-based, NO questions)

Global installation is completely automatic. It detects environment facts and installs.

##### Phase 1: Detect Environment

```bash
python3 {base_directory}/scripts/install.py --get-questions --context '{context_json}'
```

Context JSON:

```json
{
  "project_root": "{project_root}",
  "is_update": true/false
}
```

Returns:

```json
{
  "questions": [],         // Always empty - global install asks nothing
  "inferred": {...}        // Auto-detected environment facts
}
```

##### Phase 2: Install Automatically

Since there are no questions, proceed directly to installation:

```bash
python3 {base_directory}/scripts/install.py --install \
  --responses '{}' \
  --inferred '{inferred_json}'
```

Returns:

```json
{
  "success": true/false,
  "message": "Global AIDA installation complete",
  "config_path": "/Users/username/.claude"
}
```

---

#### Project Configuration: `configure.py` (YAML-Based)

Project configuration uses a **config-driven approach** with YAML as single source of truth.

##### Phase 1: Detect Facts & Save to YAML

```bash
python3 {base_directory}/scripts/configure.py --get-questions --context '{context_json}'
```

Context JSON:

```json
{
  "project_root": "{project_root}",
  "project_name": "{project_name}",
  "is_update": true/false
}
```

##### What happens in Phase 1

1. Detects all project facts (VCS, files, languages, tools)
2. **Saves to `.claude/aida-project-context.yml`** with nulls for unknown preferences
3. Identifies null preference fields
4. Returns only 0-3 questions for those gaps

Returns:

```json
{
  "questions": [...],      // 0-3 questions for null preferences only!
  "inferred": {...},       // Auto-detected facts
  "project_info": {...}    // Full detected config (saved to YAML)
}
```

##### YAML Config Created (`.claude/aida-project-context.yml`)

```yaml
version: 0.2.0
config_complete: false
vcs: {type: git, uses_worktrees: true, ...}
files: {has_readme: true, has_license: true, ...}
languages: {primary: Python, all: [...]}
tools: {detected: [Git], ...}
inferred: {project_type: Unknown, team_collaboration: Solo, ...}
preferences: {branching_model: null, issue_tracking: "GitHub Issues", ...}
```

##### Phase 2: Update YAML & Render Skill

Collect user responses with `AskUserQuestion`, then:

```bash
python3 {base_directory}/scripts/configure.py --configure \
  --responses '{responses_json}'
```

##### What happens in Phase 2

1. Loads `.claude/aida-project-context.yml`
2. Updates preferences with user responses
3. Marks `config_complete: true`
4. Saves updated YAML
5. Maps YAML → template variables
6. Renders `.claude/skills/project-context/SKILL.md`

Returns:

```json
{
  "success": true/false,
  "message": "Project configuration complete! Created project-context skill",
  "config_path": "/path/to/.claude/aida-project-context.yml",
  "files_created": [...]
}
```

##### For "View configuration"

1. Read files from detected paths (global_path or project_path)
2. Format and display nicely
3. Offer next actions

### Level 4: Error Handling

**No global installation when trying to configure project:**

```text
❌ AIDA not installed globally yet.

Please run /aida config and select 'Set up AIDA globally' first.
```

**Script errors:**

- Display error from script
- Suggest `/aida doctor`
- Don't proceed with next steps

**User cancellation:**

- Display "Configuration cancelled."
- Don't run any scripts

### Level 5: Success Messages

Parse the JSON response from Phase 2 and display appropriate message:

**After global setup:**

```text
✅ {response.message}

Configuration: {response.config_path}
Next steps:
- Run `/aida config` in a project to configure it
- Or just start using AIDA commands globally
```

**After project setup:**

```text
✅ {response.message}

Configuration: {response.config_path}
You can now use AIDA commands in this project.
```

**After updates:**

```text
✅ {response.message}

Run /aida status to verify changes.
```

**If script returns success=false:**
Display the error message and suggest troubleshooting:

```text
❌ {response.message}

Run /aida doctor for diagnostics.
```

---

## Script Details

### install.py - Global Installation (Fact-based, NO questions)

Two-phase fact-detection API:

1. `--get-questions --context '{json}'` → Detects environment, returns empty questions array
2. `--install --responses '{}' --inferred '{json}'` → Installs with detected facts

Context JSON format:

```json
{
  "project_root": "/absolute/path",
  "is_update": false
}
```

Phase 1 returns:

```json
{
  "questions": [],           // Always empty for global install
  "inferred": {              // Auto-detected environment facts
    "environment": {...}
  }
}
```

Phase 2 input:

- `responses`: Empty object `{}` (no user questions)
- `inferred`: Environment facts from Phase 1

Phase 2 returns:

```json
{
  "success": true,
  "message": "Global AIDA installation complete",
  "config_path": "/Users/username/.claude"
}
```

---

### configure.py - Project Configuration (May have questions)

Two-phase questionnaire API:

1. `--get-questions --context '{json}'` → Returns questions and inferred data
2. `--configure --responses '{json}' --inferred '{json}'` → Executes configuration

Context JSON format:

```json
{
  "project_root": "/absolute/path",
  "project_name": "directory-name",
  "is_update": false
}
```

Questions JSON format: Compatible with `AskUserQuestion` tool schema

Responses JSON format: Key-value pairs from user answers

Return JSON format:

```json
{
  "success": true,
  "message": "Human-readable status",
  "config_path": "/path/to/.claude"
}
```

---

## Plugin Configuration Discovery

During the configuration workflow, AIDA automatically discovers
installed plugins that provide configurable preferences.

### How It Works

1. **Discovery**: The system scans
   `~/.claude/plugins/cache/*/*/.claude-plugin/aida-config.json`
   for installed plugins with a `config` section
2. **Plugin Checklist**: If configurable plugins are found, a
   multi-select question is presented at the start of the wizard
3. **Preference Questions**: For each selected plugin, its
   preference questions (boolean, choice, string) are added
4. **Storage**: Plugin preferences are saved under `plugins:`
   in the YAML configuration

### Plugin Checklist

The checklist appears as the first question in the flow:

```text
Which plugins would you like to configure?
[ ] Plugin A - Description of plugin A
[ ] Plugin B - Description of plugin B
```

### Storage Format

Plugin preferences are saved in `.claude/aida-project-context.yml`:

```yaml
plugins:
  my-plugin:
    enabled: true
    feature.enabled: true
    output.format: JSON
  other-plugin:
    enabled: false
```

Plugins not selected in the checklist are marked `enabled: false`.

### Error Handling

Plugin discovery is non-critical. If scanning fails, the
configuration wizard continues normally without the plugin
section. Warnings are logged for debugging.
