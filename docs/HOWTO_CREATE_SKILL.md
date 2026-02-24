---
type: guide
title: "How to Create a Skill"
description: "Step-by-step guide to creating custom Claude Code skills"
audience: users
---

# How to Create a Skill

Skills provide execution capabilities - scripts, templates, and reference materials that
Claude can use to accomplish tasks. They're the operational playbook.

## Quick Start

```bash
/aida skill create
```

AIDA will guide you through the process interactively.

## When to Create a Skill

Create a skill when you need:

- **Execution scripts** - Python/bash scripts that perform actions
- **Templates** - Jinja2 templates for generating files
- **Reference materials** - Documentation Claude should follow
- **Reusable capabilities** - Tools used across multiple skills

Don't create a skill for:

- Domain expertise (use an [agent](HOWTO_CREATE_AGENT.md))
- Background context (use a knowledge file in an agent)

## Interactive Creation

### Step 1: Start the Wizard

```bash
/aida skill create
```

### Step 2: Describe Your Skill

AIDA will ask what the skill should do. Be specific:

```text
A database migration skill that generates migration files,
validates schema changes, and can rollback if needed.
```

### Step 3: Choose Location

- **User** (`~/.claude/skills/`) - Available in all projects
- **Project** (`.claude/skills/`) - Only for current project

### Step 4: Review and Confirm

AIDA generates the skill structure. Review it and confirm to create.

## Skill Structure

Skills have a standard directory structure:

```text
skills/
└── db-migrate/
    ├── SKILL.md           # Skill definition (required)
    ├── scripts/           # Executable scripts
    │   ├── migrate.py
    │   └── rollback.py
    ├── templates/         # Jinja2 templates
    │   └── migration.sql.jinja2
    └── references/        # Reference documentation
        └── schema-standards.md
```

## Skill Definition Format

```markdown
---
type: skill
name: db-migrate
description: Database migration management with validation and rollback
version: 0.1.0
tags:
  - database
  - migration
---

# Database Migration

Manage database schema migrations with validation and rollback capabilities.

## Activation

This skill activates when:
- User needs to create a database migration
- Schema changes need validation
- Migration rollback is required

## Scripts

### migrate.py

Creates and applies migrations.

\`\`\`bash
python {base_directory}/scripts/migrate.py --create "add_users_table"
python {base_directory}/scripts/migrate.py --apply
python {base_directory}/scripts/migrate.py --status
\`\`\`

### rollback.py

Reverts migrations.

\`\`\`bash
python {base_directory}/scripts/rollback.py --steps 1
python {base_directory}/scripts/rollback.py --to "20240115_initial"
\`\`\`

## Templates

### migration.sql.jinja2

Template for new migration files. Variables:
- `migration_name`: Name of the migration
- `timestamp`: Creation timestamp
- `tables`: List of affected tables

## References

- `schema-standards.md`: Database naming conventions and standards
```

## Writing Scripts

### Two-Phase API Pattern

For complex scripts, use the two-phase API:

```python
#!/usr/bin/env python3
"""Database migration script with two-phase API."""

import argparse
import json

def get_questions(context):
    """Phase 1: Return questions and inferred data."""
    return {
        "questions": [
            {
                "id": "migration_type",
                "question": "What type of migration?",
                "options": ["create_table", "alter_table", "add_index"]
            }
        ],
        "inferred": {
            "database": detect_database_type(),
            "existing_migrations": list_migrations()
        }
    }

def execute(context, responses):
    """Phase 2: Execute with user responses."""
    migration_type = responses.get("migration_type")
    # Create the migration...
    return {"success": True, "file": "migrations/001_create_users.sql"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get-questions", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--context", type=str)
    parser.add_argument("--responses", type=str)
    args = parser.parse_args()

    if args.get_questions:
        context = json.loads(args.context) if args.context else {}
        print(json.dumps(get_questions(context)))
    elif args.execute:
        context = json.loads(args.context) if args.context else {}
        responses = json.loads(args.responses) if args.responses else {}
        print(json.dumps(execute(context, responses)))
```

### Simple Scripts

For straightforward operations, simple scripts work fine:

```python
#!/usr/bin/env python3
"""Simple migration status script."""

import sys
from pathlib import Path

def main():
    migrations_dir = Path("migrations")
    if not migrations_dir.exists():
        print("No migrations directory found")
        return 1

    migrations = sorted(migrations_dir.glob("*.sql"))
    print(f"Found {len(migrations)} migrations:")
    for m in migrations:
        print(f"  - {m.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Creating Templates

Use Jinja2 for file generation:

```jinja2
-- Migration: {{ migration_name }}
-- Created: {{ timestamp }}

-- Up
{% if migration_type == "create_table" %}
CREATE TABLE {{ table_name }} (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    {%- for column in columns %},
    {{ column.name }} {{ column.type }}{% if column.nullable %} NULL{% else %} NOT NULL{% endif %}
    {%- endfor %}
);
{% endif %}

-- Down
{% if migration_type == "create_table" %}
DROP TABLE IF EXISTS {{ table_name }};
{% endif %}
```

## Using Your Skill

Skills are invoked directly by Claude or from other skills:

```markdown
# In a skill definition:

### Step 3: Create Migration

Use the db-migrate skill to generate the migration:

\`\`\`bash
python {skill:db-migrate}/scripts/migrate.py --create "{{ migration_name }}"
\`\`\`
```

## Best Practices

### Do

- Use the two-phase API for complex operations
- Include validation and error handling
- Provide clear output messages
- Document all script arguments

### Don't

- Include domain expertise (use agents)
- Hardcode project-specific values

## Examples

### Report Generator

```bash
/aida skill create
# Description: "A report generator that creates markdown reports
# from JSON data using customizable templates"
```

### Test Runner

```bash
/aida skill create
# Description: "A test runner that executes tests, collects coverage,
# and generates summary reports"
```

### Code Formatter

```bash
/aida skill create
# Description: "A code formatter that applies project style rules
# and fixes common issues automatically"
```

## Troubleshooting

### Skill not activating?

- Check it's in the correct location (`~/.claude/skills/` or `.claude/skills/`)
- Verify the SKILL.md frontmatter is valid
- Ensure scripts are executable (`chmod +x`)

### Script errors?

- Check Python path and dependencies
- Verify JSON input/output format
- Add logging for debugging

## Next Steps

- [Create an Agent](HOWTO_CREATE_AGENT.md) - Add expertise for your skill
- [Extension Framework](EXTENSION_FRAMEWORK.md) - Understand the architecture
