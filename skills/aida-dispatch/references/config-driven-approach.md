# Config-Driven Configuration Approach

## Overview

Instead of complex conditional logic, use a simple **detect → save → ask about gaps** flow:

1. **Detect facts** → Save to config file with nulls for unknowns
2. **Load config** → Identify which fields are null/unknown
3. **Ask questions** → Only about the gaps
4. **Update config** → Fill in the answers

## Flow Diagram

```
/aida config
    ↓
┌─────────────────────────┐
│ 1. Detect Facts         │
│    configure.py         │
│    --detect             │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 2. Save to Config       │
│    .claude/project.yml  │
│    (with nulls)         │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 3. Identify Gaps        │
│    configure.py         │
│    --get-questions      │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 4. Ask User (if needed) │
│    AskUserQuestion      │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 5. Update Config        │
│    configure.py         │
│    --update             │
└─────────────────────────┘
```

## Config File Structure

### Location Options

**Option A: Project-specific file**
```
.claude/
  aida.yml          # Global settings (existing)
  project.yml       # THIS project's config (new)
```

**Option B: Nested in aida.yml**
```yaml
# .claude/aida.yml
version: "0.2.0"
global:
  plugins: [...]

projects:
  feature-53:
    # Project config here
```

**Recommendation:** Option A - separate file is cleaner

### Project Config Schema

```yaml
# .claude/project.yml
---
# Metadata
version: "0.2.0"
last_updated: "2025-11-06T02:24:56Z"
config_complete: false  # true when all required fields filled

# Basic Info (auto-detected)
project_name: "feature-53-create-aida-dispatcher-command"
project_root: "/Users/oakensoul/Developer/..."

# Version Control (auto-detected)
vcs:
  type: "git"                    # git | svn | hg | none
  uses_worktrees: true           # boolean
  main_branch: "main"            # detected from git
  remote_url: "https://..."      # detected
  is_github: true                # inferred from remote
  is_gitlab: false               # inferred from remote

# Files (auto-detected booleans)
files:
  has_readme: true
  has_license: false
  has_gitignore: true
  has_dockerfile: true
  has_docker_compose: true
  has_tests: true
  has_ci_cd: true
  has_docs_directory: true
  has_changelog: false
  has_contributing: false

# Languages & Tools (auto-detected)
languages:
  primary: "Python"
  all: ["Python", "YAML", "Shell"]

tools:
  package_manager: "pip"        # npm, pip, gem, cargo, etc.
  build_tool: null              # make, cmake, gradle, etc.
  testing_framework: "pytest"   # pytest, jest, rspec, etc.
  ci_system: "github-actions"   # github-actions, gitlab-ci, etc.

# Inferred Facts (high confidence)
inferred:
  project_type: "Monorepo with multiple packages"
  team_size: "Solo project - just me"
  documentation_level: "Comprehensive"
  code_organization: "Monorepo with multiple packages"

# User Preferences (unknown - need to ask)
preferences:
  branching_model: null         # MUST ASK
  issue_tracking: null          # Can infer: "GitHub Issues" if is_github
  github_project_board: null    # Only if issue_tracking = GitHub Projects
  jira_config: null             # Only if issue_tracking = JIRA
  confluence_spaces: null       # Only if using JIRA
  project_conventions: null     # SHOULD ASK (optional but helpful)
  api_docs_approach: null       # Only if has public API
```

## Detection Logic

### Enhanced detect_project_info()

```python
def detect_project_info(project_root: Path) -> Dict[str, Any]:
    """Detect ALL facts we can, return with nulls for unknowns."""

    config = {
        "version": AIDA_VERSION,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "config_complete": False,

        # Basic
        "project_name": project_root.name,
        "project_root": str(project_root),

        # VCS
        "vcs": detect_vcs_info(project_root),

        # Files
        "files": detect_files(project_root),

        # Languages & tools
        "languages": detect_languages_info(project_root),
        "tools": detect_tools_info(project_root),

        # Inferred
        "inferred": infer_project_facts(project_root),

        # Preferences (all null initially)
        "preferences": {
            "branching_model": None,
            "issue_tracking": None,
            "github_project_board": None,
            "jira_config": None,
            "confluence_spaces": None,
            "project_conventions": None,
            "api_docs_approach": None,
        }
    }

    # Auto-fill some preferences if we can infer with high confidence
    if config["vcs"].get("is_github"):
        # Default to GitHub Issues for GitHub repos
        config["preferences"]["issue_tracking"] = "GitHub Issues"

    return config
```

## Question Generation Logic

### Simple Gap Detection

```python
def get_questions_from_config(config_path: Path) -> List[Question]:
    """Load config and generate questions for null fields."""

    config = load_yaml(config_path)
    questions = []

    # Check each preference field
    prefs = config.get("preferences", {})

    # Branching model (always ask if null and using git)
    if prefs.get("branching_model") is None and config["vcs"]["type"] == "git":
        questions.append(branching_model_question())

    # Issue tracking (ask if null)
    if prefs.get("issue_tracking") is None:
        questions.append(issue_tracking_question())

    # GitHub Project (only if using GitHub Projects)
    if prefs.get("issue_tracking") == "GitHub Projects" and prefs.get("github_project_board") is None:
        questions.append(github_project_question())

    # JIRA (only if using JIRA)
    if prefs.get("issue_tracking") == "JIRA/Atlassian":
        if prefs.get("jira_config") is None:
            questions.append(jira_config_question())
        if prefs.get("confluence_spaces") is None:
            questions.append(confluence_question())

    # Conventions (optional but helpful)
    if prefs.get("project_conventions") is None:
        questions.append(conventions_question())

    return questions
```

## Benefits

1. **Single Source of Truth** - Config file is authoritative
2. **Idempotent** - Can run multiple times safely
3. **Transparent** - User can see/edit config file
4. **Simple Logic** - No complex conditionals
5. **Update Friendly** - Re-run to update specific fields
6. **Auditable** - See what was detected vs asked

## Migration from Current Approach

1. Keep existing questionnaire YAML as question definitions
2. Replace conditional evaluation with gap detection
3. Update configure.py to work in 3 phases:
   - `--detect` → Create config with nulls
   - `--get-questions` → Load config, return questions for nulls
   - `--update` → Update config with responses

## Example Usage

```bash
# First time
/aida config
  → Detects facts
  → Saves to .claude/project.yml with nulls
  → Asks 2-3 questions about branching model, conventions
  → Updates config
  → Done!

# Update later
/aida config
  → Loads .claude/project.yml
  → Shows current config
  → Offers to update specific fields
  → Updates only what changed

# View without changes
/aida config
  → Loads and displays current config
  → No questions if complete
```
