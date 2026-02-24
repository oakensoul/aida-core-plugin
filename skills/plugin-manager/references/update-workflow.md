---
type: reference
title: Plugin Update Workflow
description: >-
  Detailed reference for the plugin-manager update process
  including file classification, merge strategies, version
  tracking, and backup recovery
---

# Plugin Update Workflow

Detailed reference for the plugin-manager update process.

## End-to-End Flow

1. User invokes `/aida plugin update`
2. Dispatch routes to `plugin-manager` skill
3. Skill runs `manage.py --get-questions` with plugin path
4. Script scans plugin, compares against current standards
5. Skill presents diff report and asks merge strategy
6. Skill runs `manage.py --execute` with strategy response
7. Script backs up files, applies patches, updates version
8. Skill presents summary and manual steps to user

## File Classification

The update operation classifies each scaffolded file into one of these categories:

| Category | Default Strategy | Override? | Rationale |
| --- | --- | --- | --- |
| Custom content | skip | No | CLAUDE.md, README.md, LICENSE |
| AIDA metadata | skip | No | aida-config.json |
| Plugin metadata | skip | No | plugin.json, marketplace.json |
| Boilerplate | overwrite | Yes (skip) | Linting configs, version files |
| Composite | merge | No | .gitignore, Makefile |
| CI workflow | add | Yes (skip) | .github/workflows/ci.yml |
| Dependencies | manual_review | No | pyproject.toml, package.json |
| Test scaffold | add | Yes (skip) | tests/conftest.py |

## Merge Strategy Details

### Overwrite

Replaces the file entirely with the current template output.
Used for pure boilerplate files that users rarely customize
(linting configs, version files).

### Skip

Never modifies the file. Used for user-authored content
(CLAUDE.md, README.md, LICENSE) and AIDA metadata
(aida-config.json).

### Add

Creates the file only if it does not exist on disk. Used
for CI workflows and test scaffolding. If the file already
exists, it is left untouched regardless of content.

### Merge: .gitignore

Append-only merge:

- Parses current and expected content into entry sets
- Identifies entries in expected but absent from current
- Appends missing entries under a comment header:
  `# Added by aida plugin update`
- Never removes or reorders existing entries

### Merge: Makefile

Conservative target-addition:

- Extracts target names from current and expected Makefiles
- Identifies targets in expected but absent from current
- Extracts full target blocks (definition + recipe lines)
- Appends missing blocks with `.PHONY` declarations under:
  `# Added by aida plugin update`
- Never modifies or removes existing targets

### Manual Review

Does not modify the file. Reports differences between
the current file and the template output in the post-update
summary. The user is responsible for reviewing and applying
changes manually. Used for dependency configs
(pyproject.toml, package.json).

## Version Tracking

### generator_version Field

The `generator_version` field in `.claude-plugin/aida-config.json`
records which version of the scaffolder created or last
updated the plugin.

- Written by scaffold when creating a new plugin
- Updated by update after successful patching
- Read by update to determine the version gap

### Missing generator_version

Plugins created before version tracking (or created manually)
will not have this field. The update operation treats missing
`generator_version` as `"0.0.0"` and performs a full scan
against current standards.

## Backup and Recovery

Before applying any patches, the update operation creates
a timestamped backup directory:

```text
{plugin_root}/.aida-backup/{YYYYMMDD_HHMMSS}/
```

Only files that will be modified are backed up. Missing files
(to be added) do not have backups. To restore from backup:

1. Navigate to the backup directory shown in the summary
2. Copy files back to their original locations
3. Or use `git checkout -- .` if changes were not committed

## Template Variable Resolution

During update, template variables are extracted from the
existing plugin rather than asked from the user:

| Variable | Source |
| --- | --- |
| `plugin_name` | `.claude-plugin/plugin.json` name field |
| `description` | `.claude-plugin/plugin.json` description |
| `version` | `.claude-plugin/plugin.json` version |
| `author_name` | plugin.json author or git config |
| `author_email` | git config |
| `license_id` | plugin.json license field |
| `language` | Detected from pyproject.toml / package.json |
| `keywords` | plugin.json keywords array |
| `repository_url` | plugin.json repository field |
| `generator_version` | Current GENERATOR_VERSION constant |

## Error Handling

| Error | Cause | Resolution |
| --- | --- | --- |
| "plugin_path is required" | No path provided | Provide plugin directory path |
| "not a valid plugin" | No plugin.json found | Verify the path or scaffold first |
| "Cannot detect language" | No pyproject.toml or package.json | Specify language in context |
| Partial patch failure | Write error on one file | Check summary; other files OK |
| "Plugin is up to date" | No changes needed | No action required |

## Post-Update Steps

After the update completes:

1. Review the summary of changes made
2. Check files flagged for manual review
3. Run `make lint` to verify the updated configuration
4. Run `make test` to ensure nothing is broken
5. Review changes with `git diff` before committing
6. Commit the update as a separate commit
