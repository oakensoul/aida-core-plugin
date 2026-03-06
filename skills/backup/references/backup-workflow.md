---
type: reference
name: backup-workflow
title: Backup Workflow Guide
description: >-
  End-to-end workflow guide for the AIDA backup skill
  with examples for every operation
---

# Backup Workflow Guide

This document provides end-to-end workflows for every backup
operation. Use it as a reference when executing backup commands
on behalf of the user.

## Overview

The backup skill provides seven operations:

| Operation | Purpose                                  |
| --------- | ---------------------------------------- |
| `save`    | Create a versioned backup of a file      |
| `restore` | Restore a file from a previous version   |
| `diff`    | Compare two versions of a file           |
| `list`    | List backup versions for a file or all   |
| `status`  | Show analytics and configuration summary |
| `config`  | Configure backup settings interactively  |
| `clean`   | Remove old backups per retention policy  |

## Save Workflow

### Basic Save

```text
User: /aida backup /path/to/CLAUDE.md

1. Parse: operation=save, file="/path/to/CLAUDE.md"
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "save",
                 "file": "/path/to/CLAUDE.md"}'
3. Expected output (new backup):
   {
     "success": true,
     "skipped": false,
     "backup_path": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
     "checksum": "a1b2c3d4e5f6..."
   }
4. Report: "Backed up CLAUDE.md (checksum: a1b2c3...)"
```

### Save with Message

```text
User: /aida backup /path/to/config.yml -m "before refactor"

1. Parse: operation=save, file="/path/to/config.yml",
          message="before refactor"
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "save",
                 "file": "/path/to/config.yml",
                 "message": "before refactor"}'
3. Expected output:
   {
     "success": true,
     "skipped": false,
     "backup_path": "~/.claude/.backups/.../config.yml.aida-backup.20260305-141500",
     "checksum": "b2c3d4e5f6a1..."
   }
4. Report: "Backed up config.yml with note: before refactor"
```

### Dedup Skip

When the file has not changed since the last backup:

```text
Expected output:
{
  "success": true,
  "skipped": true,
  "reason": "unchanged",
  "checksum": "a1b2c3d4e5f6..."
}

Report: "File unchanged since last backup, skipped."
```

## Restore Workflow

### Restore Latest Version

```text
User: /aida backup restore /path/to/CLAUDE.md

1. Parse: operation=restore, file="/path/to/CLAUDE.md"
2. Run execute phase with version="latest":
   python backup.py --execute \
     --context='{"operation": "restore",
                 "file": "/path/to/CLAUDE.md",
                 "version": "latest"}'
3. Expected output:
   {
     "success": true,
     "restored_from": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
     "timestamp": "2026-03-05T14:00:00+00:00"
   }
4. Report: "Restored CLAUDE.md from backup at 2026-03-05 14:00 UTC.
            A safety backup of the previous state was created."
```

### Restore Specific Version

```text
User: /aida backup restore /path/to/CLAUDE.md 20260304-093000

1. Parse: operation=restore, file="/path/to/CLAUDE.md",
          version="20260304-093000"
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "restore",
                 "file": "/path/to/CLAUDE.md",
                 "version": "20260304-093000"}'
3. Expected output:
   {
     "success": true,
     "restored_from": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260304-093000",
     "timestamp": "2026-03-04T09:30:00+00:00"
   }
```

### Restore with Version Selection

When the user does not specify a version and multiple backups
exist, use Phase 1 to present choices:

```text
1. Run Phase 1:
   python backup.py --get-questions \
     --context='{"operation": "restore",
                 "file": "/path/to/CLAUDE.md"}'
2. Phase 1 output:
   {
     "success": true,
     "questions": [{
       "id": "version",
       "type": "select",
       "message": "Which version to restore?",
       "choices": [
         {"label": "2026-03-05T14:00:00+00:00 - before refactor",
          "value": "2026-03-05T14:00:00+00:00"},
         {"label": "2026-03-04T09:30:00+00:00 - initial save",
          "value": "2026-03-04T09:30:00+00:00"}
       ],
       "default": "latest"
     }]
   }
3. Present choices to user via AskUserQuestion
4. Run Phase 2 with selected version
```

## Diff Workflow

### Latest Backup vs Current File

The default comparison when no versions are specified:

```text
User: /aida backup diff /path/to/CLAUDE.md

1. Parse: operation=diff, file="/path/to/CLAUDE.md"
2. Run execute phase (defaults: version1=latest, version2=current):
   python backup.py --execute \
     --context='{"operation": "diff",
                 "file": "/path/to/CLAUDE.md",
                 "version1": "latest",
                 "version2": "current"}'
3. Expected output:
   {
     "success": true,
     "diff": "--- CLAUDE.md (latest)\n+++ CLAUDE.md (current)\n@@ -1,3 +1,4 @@\n ...",
     "version1": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
     "version2": "/path/to/CLAUDE.md",
     "has_changes": true
   }
4. Present the unified diff to the user
```

### Comparing Two Specific Versions

```text
User: /aida backup diff /path/to/CLAUDE.md 20260304-093000 20260305-140000

1. Parse: operation=diff, file="/path/to/CLAUDE.md",
          version1="20260304-093000", version2="20260305-140000"
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "diff",
                 "file": "/path/to/CLAUDE.md",
                 "version1": "20260304-093000",
                 "version2": "20260305-140000"}'
3. Expected output:
   {
     "success": true,
     "diff": "--- CLAUDE.md (20260304-093000)\n+++ ...",
     "version1": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260304-093000",
     "version2": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
     "has_changes": true
   }
```

### No Changes Detected

```text
Expected output:
{
  "success": true,
  "diff": "",
  "version1": "...",
  "version2": "...",
  "has_changes": false
}

Report: "No differences found between the two versions."
```

## List Workflow

### List Versions of a Specific File

```text
User: /aida backup list /path/to/CLAUDE.md

1. Parse: operation=list, file="/path/to/CLAUDE.md"
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "list",
                 "file": "/path/to/CLAUDE.md"}'
3. Expected output:
   {
     "success": true,
     "file": "/path/to/CLAUDE.md",
     "versions": [
       {
         "original_path": "/path/to/CLAUDE.md",
         "timestamp": "2026-03-05T14:00:00+00:00",
         "message": "before refactor",
         "file_size": 2048,
         "checksum": "a1b2c3d4e5f6...",
         "backup_path": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
         "git_hash": "abc1234",
         "git_dirty": false
       },
       {
         "original_path": "/path/to/CLAUDE.md",
         "timestamp": "2026-03-04T09:30:00+00:00",
         "message": "initial save",
         "file_size": 1920,
         "checksum": "c3d4e5f6a1b2...",
         "backup_path": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260304-093000",
         "git_hash": "def5678",
         "git_dirty": true
       }
     ],
     "count": 2
   }
4. Present as a formatted table:
   Version   | Date                | Message          | Size   | Git
   latest    | 2026-03-05 14:00    | before refactor  | 2.0 KB | abc1234
   #2        | 2026-03-04 09:30    | initial save     | 1.9 KB | def5678*
```

### List All Backed-Up Files

```text
User: /aida backup list

1. Parse: operation=list (no file)
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "list"}'
3. Expected output:
   {
     "success": true,
     "files": [
       {"original_path": "/path/to/CLAUDE.md", "versions": 3},
       {"original_path": "/path/to/config.yml", "versions": 1}
     ],
     "total_files": 2
   }
4. Present as a summary:
   2 files backed up:
   - /path/to/CLAUDE.md (3 versions)
   - /path/to/config.yml (1 version)
```

## Status Workflow

```text
User: /aida backup status

1. Parse: operation=status
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "status"}'
3. Expected output:
   {
     "success": true,
     "config": {
       "enabled": true,
       "scope": "always",
       "storage": "global",
       "custom_command": "",
       "retention": {
         "max_versions": 10,
         "max_age_days": 30,
         "auto_enforce": true
       }
     },
     "stats": {
       "total_files_backed_up": 5,
       "total_backup_versions": 23,
       "total_size_bytes": 524288,
       "total_size_human": "512.0 KB",
       "oldest_backup": "2026-02-01T10:00:00+00:00",
       "newest_backup": "2026-03-05T14:00:00+00:00",
       "files": [
         {
           "original_path": "/path/to/CLAUDE.md",
           "versions": 8,
           "total_size_bytes": 16384,
           "total_size_human": "16.0 KB",
           "oldest": "2026-02-15T09:00:00+00:00",
           "newest": "2026-03-05T14:00:00+00:00"
         }
       ]
     }
   }
4. Present formatted status:
   Backup Status
   =============
   Enabled: yes | Scope: always | Storage: global
   Retention: 10 versions, 30 days, auto-enforce on

   Stats: 5 files, 23 versions, 512.0 KB total
   Oldest: 2026-02-01 | Newest: 2026-03-05

   Top files:
   - CLAUDE.md: 8 versions (16.0 KB)
   ...
```

## Config Workflow

```text
User: /aida backup config

1. Parse: operation=config
2. Run Phase 1:
   python backup.py --get-questions \
     --context='{"operation": "config"}'
3. Phase 1 returns questions with current values as defaults:
   - backup_enabled (confirm): Enable file backups?
   - backup_scope (select): always | outside-git-only
   - backup_storage (select): global | local | custom
   - backup_retention_versions (input): Max versions per file
   - backup_retention_days (input): Max age in days
   - backup_retention_auto_enforce (confirm): Enforce after save?
   - backup_custom_command (input): Custom backup command
4. Present questions to user via AskUserQuestion
5. Run Phase 2 with responses:
   python backup.py --execute \
     --context='{"operation": "config"}' \
     --responses='{"backup_enabled": true, ...}'
6. Expected output:
   {
     "success": true,
     "message": "Backup config saved to ~/.claude/aida.yml",
     "config": { ... }
   }
7. Report: "Backup configuration saved."
```

## Clean Workflow

### Dry Run

Always offer a dry run first so the user can review what
would be removed:

```text
User: /aida backup clean --dry-run

1. Parse: operation=clean, dry_run=true
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "clean", "dry_run": true}'
3. Expected output:
   {
     "success": true,
     "files_scanned": 5,
     "backups_found": 23,
     "backups_removed": 8,
     "space_freed_bytes": 131072,
     "space_freed_human": "128.0 KB",
     "dry_run": true
   }
4. Report: "Dry run: would remove 8 of 23 backups across
            5 files, freeing 128.0 KB. Run without --dry-run
            to execute."
```

### Execute Clean

```text
User: /aida backup clean

1. Parse: operation=clean, dry_run=false
2. Run execute phase:
   python backup.py --execute \
     --context='{"operation": "clean", "dry_run": false}'
3. Expected output:
   {
     "success": true,
     "files_scanned": 5,
     "backups_found": 23,
     "backups_removed": 8,
     "space_freed_bytes": 131072,
     "space_freed_human": "128.0 KB",
     "dry_run": false
   }
4. Report: "Cleaned 8 backups across 5 files, freed 128.0 KB."
```

### No Retention Policy

When both `max_versions` and `max_age_days` are `0`:

```text
Expected output:
{
  "success": true,
  "files_scanned": 0,
  "backups_found": 0,
  "backups_removed": 0,
  "space_freed_bytes": 0,
  "space_freed_human": "0 B",
  "note": "No retention policy configured, nothing to clean"
}

Report: "No retention policy is configured. Use /aida backup
         config to set max_versions or max_age_days first."
```

## Storage Locations

### Global Storage (default)

All backups go to `~/.claude/.backups/` with the original file's
absolute directory path mirrored underneath:

```text
Original: /Users/mat/project/src/config.yml
Backup:   ~/.claude/.backups/Users/mat/project/src/
            config.yml.aida-backup.20260305-140000
            config.yml.aida-backup.20260305-140000.meta.json
```

The `.backups` directory uses `0o700` permissions for privacy.

### Local Storage

Backups live in the same directory as the original file. No
directory mirroring is needed:

```text
Original: /Users/mat/project/src/config.yml
Backup:   /Users/mat/project/src/
            config.yml.aida-backup.20260305-140000
            config.yml.aida-backup.20260305-140000.meta.json
```

Note: `list` without a file argument is not supported in local
storage mode because there is no central scan directory.

### Custom Path

Works like global storage but rooted at the user-specified path:

```text
Config:   storage: "/Volumes/external/backups"
Original: /Users/mat/project/src/config.yml
Backup:   /Volumes/external/backups/Users/mat/project/src/
            config.yml.aida-backup.20260305-140000
            config.yml.aida-backup.20260305-140000.meta.json
```

## Retention Policy Examples

### Keep Last 5 Versions

```yaml
backup:
  retention:
    max_versions: 5
    max_age_days: 0
    auto_enforce: true
```

After saving the 6th backup of a file, the oldest backup is
automatically removed.

### Keep Backups for 30 Days

```yaml
backup:
  retention:
    max_versions: 0
    max_age_days: 30
    auto_enforce: true
```

Backups older than 30 days are removed after each save.

### Combined: 10 Versions or 90 Days

```yaml
backup:
  retention:
    max_versions: 10
    max_age_days: 90
    auto_enforce: true
```

A backup is removed if it exceeds either limit. The newest 10
are always kept, and any older than 90 days are also removed.

### Manual Cleanup Only

```yaml
backup:
  retention:
    max_versions: 10
    max_age_days: 30
    auto_enforce: false
```

Retention is only applied when the user runs
`/aida backup clean` explicitly.

## Custom Command Override Examples

### Using cpb

```yaml
backup:
  custom_command: "cpb {file}"
```

Runs `cpb /path/to/file` for every save. If `cpb` fails, the
built-in Python backup is used as a fallback.

### Git Stash-Based Backup

```yaml
backup:
  custom_command: "cd $(dirname {file}) && git stash push -m '{message}' -- {file}"
```

### Rsync to Remote

```yaml
backup:
  custom_command: "rsync -av {file} backup-server:/backups/"
```

The custom command has a 30-second timeout. If it exits with a
non-zero code or times out, the built-in backup runs instead.

## Metadata Sidecar Format

Every backup file has a companion `.meta.json` sidecar:

```json
{
  "original_path": "/Users/mat/project/CLAUDE.md",
  "timestamp": "2026-03-05T14:00:00+00:00",
  "message": "before refactor",
  "file_size": 2048,
  "checksum": "a1b2c3d4e5f67890...",
  "backup_path": "~/.claude/.backups/.../CLAUDE.md.aida-backup.20260305-140000",
  "git_hash": "abc1234",
  "git_dirty": false
}
```

If a sidecar is missing or corrupted, the backup skill
automatically rebuilds it from the backup file itself.
Rebuilt sidecars have the message `"(metadata rebuilt)"`.

## Troubleshooting

### "File not found" Error

**Cause:** The file path does not exist on disk.

**Resolution:** Verify the path is correct and absolute. Use
tab completion or `ls` to confirm the file exists.

### "No backups found" Error

**Cause:** No backups exist for the requested file in the
configured storage location.

**Resolution:**

- Check which storage mode is active: `/aida backup status`
- Verify the file was backed up: `/aida backup list`
- If storage was recently changed, old backups may be in the
  previous storage location

### "Version not found" Error

**Cause:** The specified timestamp does not match any backup.

**Resolution:** List available versions with
`/aida backup list <file>` and use an exact timestamp from the
output.

### Dedup Keeps Skipping

**Cause:** The file has not changed since the last backup.
The MD5 checksum matches.

**Resolution:** This is expected behavior. The backup skill
only creates new versions when the file content has actually
changed. If you need to force a new version, make a small
edit and save again.

### Backup Directory Permissions

**Cause:** The backup directory cannot be created or written to.

**Resolution:**

- For global storage, check `~/.claude/.backups/` permissions
- For custom paths, verify the target directory is writable
- For local storage, verify the file's parent directory is
  writable

### Custom Command Failures

**Cause:** The custom backup command exits non-zero or times
out (30-second limit).

**Resolution:**

- Test the command manually with actual file paths
- Check that `{file}` and `{message}` placeholders expand
  correctly
- The built-in backup runs as automatic fallback, so data
  is not lost

### Config Not Taking Effect

**Cause:** Project-level config may be overriding global config.

**Resolution:** Check both config files:

- Global: `~/.claude/aida.yml`
- Project: `.claude/aida-project-context.yml`

Project settings override global settings via shallow merge.
Run `/aida backup status` to see the effective configuration.

### Clean Removes Nothing

**Cause:** No retention policy is configured (both
`max_versions` and `max_age_days` are `0`).

**Resolution:** Set a retention policy first:
`/aida backup config` or edit `aida.yml` directly.
