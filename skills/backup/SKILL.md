---
type: skill
name: backup
title: File Backup Manager
description: >-
  Manages file backups with checksum dedup, metadata sidecars,
  and configurable retention
version: 0.1.0
tags:
  - core
  - safety
  - backup
---

# Backup

File Backup Manager provides versioned file backups with checksum
deduplication, JSON metadata sidecars, git context capture, and
configurable retention policies. It works as a safety net for
destructive edits, especially outside version-controlled projects.

## Activation

This skill activates when:

- User invokes `/aida backup [save|restore|diff|list|status|config|clean]`
- User mentions "backup", "back up", or "save version"
- User asks to "restore file" or view "version history"
- User wants to "diff versions" or manage "file backup"

## Command Routing

When this skill activates, parse the command to determine:

1. **Operation**: `save`, `restore`, `diff`, `list`, `status`,
   `config`, `clean`
2. **Arguments**: file path, version identifier, message, flags

### Save

Back up a file with checksum deduplication.

**Usage:** `/aida backup <file> [-m message]`

**Script invocation:**

```bash
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "save", "file": "/path/to/file", "message": "optional note"}'
```

**Process:**

1. Compute MD5 checksum of current file
2. Compare to most recent backup -- skip if identical (dedup)
3. Create timestamped copy in backup directory
4. Write JSON metadata sidecar alongside backup
5. Enforce retention policy if `auto_enforce` is enabled

### Restore

Restore a file from a previous backup version.

**Usage:** `/aida backup restore <file> [version]`

**Script invocation:**

```bash
# Phase 1: Get available versions (when version not specified)
python {base_directory}/scripts/backup.py \
  --get-questions \
  --context='{"operation": "restore", "file": "/path/to/file"}'

# Phase 2: Execute restore
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "restore", "file": "/path/to/file", "version": "latest"}'
```

**Process:**

1. Resolve the requested version (`latest`, timestamp, or
   user selection from Phase 1)
2. Create a safety backup of the current file before restoring
3. Copy the selected backup version over the original file

### Diff

Show differences between two versions of a file.

**Usage:** `/aida backup diff <file> [version1] [version2]`

Defaults to comparing the latest backup against the current file
when versions are omitted.

**Script invocation:**

```bash
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "diff", "file": "/path/to/file", "version1": "latest", "version2": "current"}'
```

**Version identifiers:**

- `latest` -- most recent backup by timestamp
- `current` -- the original file on disk right now
- `YYYYMMDD-HHMMSS` -- exact timestamp of a specific backup

### List

List backup versions for a specific file or all backed-up files.

**Usage:** `/aida backup list [file]`

**Script invocation:**

```bash
# List versions of a specific file
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "list", "file": "/path/to/file"}'

# List all backed-up files
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "list"}'
```

### Status

Show backup analytics and current configuration summary.

**Usage:** `/aida backup status`

**Script invocation:**

```bash
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "status"}'
```

**Returns:**

- Current configuration summary
- Total files backed up and version counts
- Total storage used (human-readable)
- Oldest and newest backup timestamps
- Per-file breakdown with version counts and sizes

### Config

Configure backup settings interactively. Uses the two-phase API
to present questions and write responses to `aida.yml`.

**Usage:** `/aida backup config`

**Script invocation:**

```bash
# Phase 1: Get configuration questions
python {base_directory}/scripts/backup.py \
  --get-questions \
  --context='{"operation": "config"}'

# Phase 2: Write configuration
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "config"}' \
  --responses='{"backup_enabled": true, "backup_scope": "always", "backup_storage": "global", "backup_retention_versions": "10", "backup_retention_days": "30", "backup_retention_auto_enforce": true, "backup_custom_command": ""}'
```

**Process:**

1. Phase 1 returns current settings as defaults with questions
2. Present questions to user via AskUserQuestion
3. Phase 2 writes responses to `~/.claude/aida.yml` backup section

### Clean

Apply retention policy to remove old backups.

**Usage:** `/aida backup clean [--dry-run]`

**Script invocation:**

```bash
# Dry run (preview what would be removed)
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "clean", "dry_run": true}'

# Execute cleanup
python {base_directory}/scripts/backup.py \
  --execute \
  --context='{"operation": "clean", "dry_run": false}'
```

**Returns:**

- Files scanned and backups found
- Number of backups removed (or would be removed in dry run)
- Space freed in human-readable format

## Path Resolution

**Base Directory:** Provided when skill loads via `<command-message>`
tags.

**Script Execution:**

```text
{base_directory}/scripts/backup.py
```

**Reference Files:**

```text
{base_directory}/references/backup-workflow.md
```

## Two-Phase API

This skill uses a two-phase API pattern:

### Phase 1: Get Questions

Analyzes context and returns:

- Validation results (file existence, available versions)
- Questions that need user input (version selection, config)
- Current settings as defaults

**Operations using Phase 1:**

- `restore` -- returns available versions for selection when
  multiple backups exist
- `config` -- returns configuration questions with current
  values as defaults

### Phase 2: Execute

Performs the operation with:

- User responses from Phase 1 questions (if any)
- Context data (file path, operation, flags)
- Merged configuration from global and project settings

**All operations use Phase 2** for execution.

## Configuration

Backup settings live in `~/.claude/aida.yml` under the `backup:`
key. Project-level overrides can be set in
`.claude/aida-project-context.yml`.

### Full Schema

```yaml
backup:
  enabled: true
  scope: "always"              # "always" | "outside-git-only"
  storage: "global"            # "global" | "local" | "/custom/path"
  custom_command: ""
  retention:
    max_versions: 0
    max_age_days: 0
    auto_enforce: true
```

### Config Merge Order

1. Built-in defaults (all fields have safe defaults)
2. Global config: `~/.claude/aida.yml` backup section
3. Project config: `.claude/aida-project-context.yml` backup
   section (overrides global, shallow merge)

## Retention Policy

Retention controls how many backup versions are kept and for
how long.

| Setting        | Default | Description                       |
| -------------- | ------- | --------------------------------- |
| `max_versions` | `0`     | Max backups per file (0=unlimited)|
| `max_age_days` | `0`     | Max age in days (0=unlimited)     |
| `auto_enforce` | `true`  | Enforce after every save          |

**Behavior:**

- When both `max_versions` and `max_age_days` are `0`,
  retention is unlimited and `clean` is a no-op.
- When `auto_enforce` is `true`, retention runs automatically
  after every `save` operation for the file just backed up.
- The `clean` command applies retention globally across all
  backed-up files.
- Newest backups are always kept first. Excess versions and
  expired backups are removed oldest-first.

## Scope Options

Controls when backups are created:

| Scope              | Description                          |
| ------------------ | ------------------------------------ |
| `always`           | Back up every file regardless of git |
| `outside-git-only` | Skip files tracked by git            |

The `outside-git-only` scope checks whether the file is tracked
by git using `git ls-files --error-unmatch`. Untracked files
inside a git repo are still backed up.

## Storage Options

Controls where backups are stored on disk.

### Global (default)

```text
~/.claude/.backups/
```

Backups are stored with mirrored directory paths. For example,
backing up `/Users/mat/project/src/config.yml` creates:

```text
~/.claude/.backups/Users/mat/project/src/
  config.yml.aida-backup.20260305-140000
  config.yml.aida-backup.20260305-140000.meta.json
```

The backup directory is created with `0o700` permissions.

### Local

Backups are stored in the same directory as the original file.
No mirrored path structure is needed.

### Custom Path

Specify any absolute path. Mirrored directory structure is used
just like global storage, but rooted at the custom path instead
of `~/.claude/.backups/`.

```yaml
backup:
  storage: "/Volumes/external/backups"
```

## Custom Command Override

When `custom_command` is set, the backup skill runs the custom
command instead of the built-in Python backup for `save`
operations. If the custom command fails, it falls back to the
built-in provider automatically.

**Placeholders:**

| Placeholder | Replaced With                     |
| ----------- | --------------------------------- |
| `{file}`    | Absolute path to the file         |
| `{message}` | User-provided backup message      |

**Example:**

```yaml
backup:
  custom_command: "cpb {file}"
```

The custom command runs with a 30-second timeout and must exit
with code 0 to be considered successful.

## Internal API

Other AIDA skills can invoke backup operations programmatically
using subprocess-based cross-skill invocation (per ADR-012).

Example — saving a backup from another skill:

```python
import subprocess
import json

result = subprocess.run(
    [
        "python3",
        f"{base_directory}/scripts/backup.py",
        "--execute",
        "--context",
        json.dumps({
            "operation": "save",
            "file": "/path/to/file",
            "message": "auto-backup before edit",
        }),
    ],
    capture_output=True,
    text=True,
    timeout=30,
)
response = json.loads(result.stdout)
```

This pattern keeps skills decoupled while enabling composition.
Each skill communicates via JSON over CLI arguments and stdout.

## Resources

### scripts/

- **backup.py** -- Main management script with two-phase API
- **operations/backup_ops.py** -- Core backup operations
  (checksum dedup, restore, diff, list, status, clean,
  retention enforcement, custom command override)

### references/

- **backup-workflow.md** -- End-to-end workflow guide with
  examples for every operation
