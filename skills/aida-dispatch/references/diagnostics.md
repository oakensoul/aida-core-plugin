---
type: reference
title: "Diagnostics Actions"
description: "Handles /aida status, /aida doctor, and /aida upgrade commands"
---

# Diagnostics Actions

Handles `/aida status`, `/aida doctor`, and `/aida upgrade` commands.

## Quick Start

These are non-interactive commands - just run the script and display output.

### /aida status

```bash
python3 {base_directory}/scripts/status.py
```

Display the output directly to the user.

### /aida doctor

```bash
python3 {base_directory}/scripts/doctor.py
```

Display the diagnostic results and any recommendations.

### /aida upgrade

```bash
python3 {base_directory}/scripts/upgrade.py
```

Display upgrade information and follow any instructions provided.

---

## Progressive Disclosure

### Level 1: Basic Execution

1. Get the base directory from skill context
2. Construct the full path to the script
3. Run `python3 {path_to_script}`
4. Capture output (stdout and stderr)
5. Display to user

**That's it.** These commands require no user interaction.

### Level 2: Error Handling

#### If script fails (non-zero exit code)

- Display the error message
- Suggest next steps:
  - For `status` errors: Try `/aida doctor`
  - For `doctor` errors: Check Python version, file permissions
  - For `upgrade` errors: Check network connectivity, permissions

#### If script succeeds

- Display output as-is
- No additional formatting needed (scripts format their own output)

### Level 3: Output Examples

**Status output:**

```text
AIDA Status
========================================
✓ Global Installation: /path/to/.claude
✓ Project Configuration: /path/to/project/.claude
...
```

**Doctor output:**

```text
Running AIDA Diagnostics...
========================================
✓ Python version: 3.11.0
✓ Global config: Found
⚠ Project config: Missing
...
```

**Upgrade output:**

```text
Checking for AIDA updates...
========================================
Current version: 0.2.0
Latest version: 0.3.0
...
```

---

## Script Details

See `docs/API.md` for complete script interfaces and return codes.
