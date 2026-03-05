---
type: issue
issue: 34
title: "AIDA-managed virtual environment for Python dependencies"
status: "In Progress"
created: "2026-03-05"
estimated_effort: 5
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/34"
---

# Issue #34: AIDA-managed virtual environment for Python dependencies

**Status**: In Progress
**Labels**: enhancement, infrastructure
**Milestone**: v1.1
**Assignees**: oakensoul

## Description

AIDA core plugin scripts depend on Python packages (jinja2, PyYAML,
jsonschema) but currently expect users to install them into whatever
Python environment happens to be active. This leads to two problems:

1. **Poor dependency checking** -- scripts fail with cryptic import
   errors or print ad-hoc "Install with: pip install ..." messages
   when dependencies are missing. There is no unified pre-flight
   check.

2. **Global environment pollution** -- `pip install -r requirements.txt`
   without a virtual environment installs packages globally (or into
   the user's base environment), which can conflict with other
   projects and is generally bad practice.

AIDA should manage its own virtual environment so that plugin scripts
"just work" without asking users to manually install packages or
pollute their global Python installation.

## Requirements

### AIDA-managed Virtual Environment

- [ ] Create a dedicated venv at `~/.aida/venv/` (or a configurable
      path) for AIDA plugin Python dependencies
- [ ] Venv creation should happen automatically on first use (lazy
      initialization) -- not require an explicit setup step
- [ ] Venv should be created with the system Python 3 (`python3 -m
      venv`) and not require any pre-installed tools beyond Python
      itself
- [ ] Install `requirements.txt` dependencies into the managed venv
      automatically when the venv is created or when dependencies
      change
- [ ] Track installed dependency versions (e.g., a stamp file) so
      that `pip install` only runs when `requirements.txt` changes

### Unified Dependency Bootstrap

- [ ] Create a shared utility function (e.g., in `scripts/shared/`)
      that all AIDA scripts call early to ensure the venv exists and
      dependencies are available
- [ ] The bootstrap should:
  - Check if the managed venv exists; create it if not
  - Compare `requirements.txt` hash against the stamp file; update
    if changed
  - Add the venv's `site-packages` to `sys.path` so imports work
    transparently
  - Print clear status messages during initial setup (e.g.,
    "Setting up AIDA environment...")
- [ ] If venv creation fails (e.g., `python3 -m venv` not available),
      fall back gracefully with a clear error message explaining
      what's needed

### Script Migration

- [ ] Remove ad-hoc "Install with: pip install ..." error messages
      from individual scripts:
  - `scripts/validate_frontmatter.py` (lines 29, 35)
  - `scripts/shared/utils.py` (line 274)
  - `skills/memento/scripts/memento.py` (line 647)
  - `skills/aida/scripts/configure.py` (line 799)
  - `skills/aida/scripts/utils/questionnaire.py` (line 271)
  - `skills/aida/scripts/utils/files.py` (line 251)
- [ ] Update all scripts to call the bootstrap function instead
- [ ] Update `Makefile` targets to use the managed venv Python
      (for `make lint`, `make test`, etc.) during development

### Doctor Integration

- [ ] Add venv health check to `skills/aida/scripts/doctor.py`:
  - Venv exists and is valid
  - All required packages are installed
  - Package versions meet minimum requirements
- [ ] Doctor should offer to recreate the venv if it's corrupted

### Extension Template Updates

- [ ] Update skill template (`skills/skill-manager/templates/skill/
      SKILL.md.jinja2`) to optionally include bootstrap import
      guidance in generated scripts
- [ ] Add a question during skill creation: "Use AIDA managed
      environment for Python dependencies?" (default: yes if AIDA
      is detected, no otherwise)
- [ ] When opted in, generated script stubs should include the
      `ensure_aida_environment()` import and call
- [ ] When opted out, generated scripts should use standard
      try/except import patterns with user-facing install messages
- [ ] Update create-workflow reference to document both approaches
- [ ] Update plugin scaffold templates to mention managed venv as
      an option rather than defaulting to global `pip install`

### Documentation Updates

- [ ] Update `docs/DEVELOPMENT.md` to document the managed venv
      approach
- [ ] Update `README.md` installation section
- [ ] Update `docs/USER_GUIDE_INSTALL.md` requirements section
- [ ] Update troubleshooting guide in
      `agents/aida/knowledge/troubleshooting.md`

## Technical Design

### Venv Location

```text
~/.aida/
  venv/                    # Managed virtual environment
    bin/python3            # Isolated Python interpreter
    lib/python3.x/site-packages/  # Installed packages
  .venv-stamp              # Hash of requirements.txt at install time
```

### Bootstrap Flow

```python
def ensure_aida_environment():
    """Ensure AIDA venv exists with current dependencies."""
    aida_dir = Path.home() / ".aida"
    venv_dir = aida_dir / "venv"
    stamp_file = aida_dir / ".venv-stamp"

    # 1. Create venv if missing
    if not (venv_dir / "bin" / "python3").exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])

    # 2. Check if deps need updating
    req_hash = hash_file(requirements_txt)
    if stamp_file.exists() and stamp_file.read_text().strip() == req_hash:
        add_venv_to_path(venv_dir)
        return

    # 3. Install/update dependencies
    pip = venv_dir / "bin" / "pip"
    subprocess.run([str(pip), "install", "-r", str(requirements_txt)])
    stamp_file.write_text(req_hash)
    add_venv_to_path(venv_dir)
```

### Path Injection

Rather than requiring scripts to be run with the venv's Python
interpreter, the bootstrap adds the venv's `site-packages` to
`sys.path` at runtime. This means scripts can be invoked with any
Python 3 interpreter and still find AIDA's dependencies.

### Cross-Platform Considerations

- Use `bin/` on macOS/Linux, `Scripts/` on Windows
- Use `python3` / `python` appropriately per platform
- Handle the case where `venv` module is not installed (common on
  some Linux distros where `python3-venv` is a separate package)

## Acceptance Criteria

- [ ] Running any AIDA script for the first time automatically
      creates the venv and installs dependencies without user
      intervention
- [ ] Subsequent script runs skip venv creation (fast path)
- [ ] Dependencies update automatically when `requirements.txt`
      changes
- [ ] No packages are installed into the user's global Python
      environment
- [ ] `aida doctor` reports venv health status
- [ ] All existing scripts work without manual `pip install`
- [ ] Clear error messages when Python 3 or venv module is
      unavailable
- [ ] Works on macOS and Linux (Windows support is stretch goal)

## Out of Scope (Future)

- Multiple isolated venvs per plugin (all plugins share one venv
  for now)
- Conda/mamba/uv support (standard venv + pip only)
- Automatic Python version management (pyenv, asdf, etc.)
- Plugin-declared Python dependencies merged into the managed venv

## Work Tracking

- Branch: `milestone-v1.1/feature/34-aida-managed-venv`
- Worktree: `../issue-34/`
- Started: 2026-03-05

## Related Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/34)
- Issue #20 - Plugin dependency management and agent registry
- Issue #23 - Plugin scaffolding (should use managed venv)
