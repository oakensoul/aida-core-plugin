---
type: adr
title: "ADR-012: Cross-Skill Communication via Subprocess"
status: accepted
date: "2026-03-05"
deciders:
  - "@oakensoul"
---

# ADR-012: Cross-Skill Communication via Subprocess

## Context

As AIDA's skill ecosystem grows, skills increasingly need to
coordinate with each other. For example, the `claude-md-manager`
skill should trigger a backup (via the `backup` skill) before
overwriting a managed file. Other future cases include skills
that validate, lint, or post-process output from another skill.

Three approaches were considered for enabling this cross-skill
communication:

1. **Direct Python import**: One skill imports another skill's
   modules directly (e.g., `from backup.scripts.backup import
   execute`).
2. **Shared module in scripts/shared/**: Place cross-skill
   coordination logic in the project-level `scripts/shared/`
   directory.
3. **Subprocess calls through the two-phase API**: One skill
   invokes another skill's script as a subprocess, passing
   context via `--execute --context '{...}'`.

The chosen approach must respect AIDA's skills-first architecture
(ADR-001), where each skill is a self-contained, independently
installable unit.

## Decision

Cross-skill communication uses **subprocess calls** through the
existing two-phase API (ADR-010). The calling skill:

1. **Discovers** the target skill script via a path derived from
   `PROJECT_ROOT / "skills" / "{name}" / "scripts" / "{name}.py"`
2. **Checks existence** before calling (`Path.is_file()`)
3. **Invokes** via `subprocess.run()` with `--execute` and
   `--context` JSON, exactly as the LLM orchestrator would
4. **Handles absence** gracefully: if the target skill is not
   installed, the calling skill logs a warning and continues

### Implementation Pattern

The `_trigger_backup` helper below shows how `claude-md-manager`
would call the `backup` skill before overwriting a file:

```python
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _trigger_backup(
    project_root: Path,
    file_path: Path,
    message: str = "",
) -> bool:
    """Trigger a pre-write backup via the backup skill.

    Uses subprocess to call backup.py --execute, following
    the two-phase API (ADR-010). Degrades gracefully if the
    backup skill is not installed.

    Returns True if backup succeeded or was skipped (skill
    not installed). Returns False only on backup failure.
    """
    backup_script = (
        project_root / "skills" / "backup"
        / "scripts" / "backup.py"
    )

    if not backup_script.is_file():
        logger.info(
            "Backup skill not installed, skipping pre-write "
            "backup for %s",
            file_path,
        )
        return True  # graceful degradation

    context = json.dumps({
        "operation": "save",
        "file": str(file_path),
        "message": message or f"Pre-write backup of {file_path.name}",
    })

    try:
        result = subprocess.run(
            [
                "python3",
                str(backup_script),
                "--execute",
                "--context",
                context,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("success"):
                logger.info("Backup created: %s", file_path)
                return True

        logger.warning(
            "Backup failed for %s: %s",
            file_path,
            result.stderr or result.stdout,
        )
        return False

    except FileNotFoundError:
        logger.warning("python3 not found, skipping backup")
        return True
    except subprocess.TimeoutExpired:
        logger.warning("Backup timed out for %s", file_path)
        return False
```

A caller in `claude-md-manager` would use it like:

```python
# Back up before overwriting
if not _trigger_backup(PROJECT_ROOT, target_path):
    return {
        "success": False,
        "error": "Pre-write backup failed; aborting write",
    }

# Proceed with the write operation
target_path.write_text(new_content)
```

## Rationale

### Follows Skills-First Architecture (ADR-001)

Each skill remains a self-contained unit. The calling skill does
not embed knowledge of the target skill's internals -- it only
knows the script path convention and the two-phase API contract.

### Uses the Established Two-Phase API (ADR-010)

The subprocess call uses `--execute --context '{...}'`, the same
interface the LLM orchestrator uses. No special "internal" API
is needed. This means cross-skill calls are tested the same way
as LLM-initiated calls.

### Graceful Degradation

If the target skill is not installed, `Path.is_file()` returns
`False` and the caller skips the call. No `ImportError`, no
`ModuleNotFoundError`, no crash. The caller decides whether the
missing skill is fatal or advisory.

### No sys.path Manipulation or Import Coupling

Direct Python imports between skills would require `sys.path`
hacking to make one skill's modules visible to another. This
creates hidden coupling and breaks if either skill is relocated
or uninstalled. Subprocess calls avoid this entirely.

### Each Skill Can Be Tested in Isolation

Because the interface is JSON over subprocess, each skill's
tests remain fully independent. The calling skill can mock
`subprocess.run()` without importing the target skill at all.

## Alternatives Considered

### Alternative 1: Direct Python Import

**Approach**: Import the target skill's Python modules directly.

```python
# Would require sys.path manipulation
import sys
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "backup" / "scripts"))
from backup import execute  # noqa
```

**Pros**:

- No process spawn overhead
- Direct function call, type-checkable

**Cons**:

- Requires `sys.path` hacking at import time
- Couples skills at the module level
- Breaks with `ImportError` if target skill not installed
- Target skill's `_paths.py` bootstrap runs in caller's process,
  potentially conflicting with caller's own path setup
- Cannot test caller without target skill present

**Verdict**: Rejected -- violates skill isolation and creates
brittle import-time coupling.

### Alternative 2: Shared Module in scripts/shared/

**Approach**: Place cross-skill coordination functions in
`scripts/shared/cross_skill.py` or similar.

**Pros**:

- No subprocess overhead
- Centralized coordination logic

**Cons**:

- Puts skill-specific logic (e.g., "how to call backup") in a
  shared space with wrong ownership
- `scripts/shared/` is for truly shared utilities (JSON parsing,
  path helpers), not skill-to-skill wiring
- Every new cross-skill interaction adds to the shared module,
  creating a growing dependency magnet
- Still needs import-time path resolution for target skills

**Verdict**: Rejected -- wrong ownership model. The calling skill
should own its integration logic, not a shared module.

## Consequences

### Positive

- Skills remain independently installable and testable
- No new infrastructure required -- reuses two-phase API
- Interface boundary is explicit: JSON in, JSON out
- Graceful degradation is natural (file existence check)
- Same calling convention whether invoked by LLM or by
  another skill
- Easy to add new cross-skill interactions without modifying
  shared code

### Negative

- Process spawn overhead (~10ms per call) is higher than a
  direct function call
- JSON serialization/deserialization adds minor overhead
- Debugging requires following execution across process
  boundaries (mitigated by logging in both skills)
- Must handle subprocess edge cases (timeout, stderr, exit
  codes)

### Mitigation

**Process Overhead**:

- ~10ms is acceptable for pre-write backup operations
- Not on any hot path; these are pre-action safety checks
- If a future use case demands sub-millisecond cross-skill
  calls, revisit this decision

**Debugging**:

- Both skills log to stderr with standard Python logging
- Caller captures and logs subprocess stdout/stderr
- JSON interface makes request/response easy to inspect

## Related Decisions

- [ADR-001: Skills-First Architecture](001-skills-first-architecture.md)
  -- Skills as self-contained units; this ADR preserves that
  boundary
- [ADR-010: Two-Phase API Pattern](010-two-phase-api-pattern.md)
  -- The communication protocol reused for cross-skill calls

---

**Decision Record**: @oakensoul, 2026-03-05
**Status**: Accepted
