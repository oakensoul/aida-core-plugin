"""Core backup operations for the AIDA backup skill.

Built-in Python backup provider with zero external dependencies.
Supports checksum dedup, JSON metadata sidecars, git context capture,
smart version resolution, diff between versions, configurable storage,
and retention policies.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "scope": "always",
    "storage": "global",
    "custom_command": "",
    "retention": {
        "max_versions": 0,
        "max_age_days": 0,
        "auto_enforce": True,
    },
}

BACKUP_SUFFIX = ".aida-backup"
META_SUFFIX = ".meta.json"
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"
GLOBAL_BACKUP_DIR = Path.home() / ".claude" / ".backups"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_backup_config() -> dict[str, Any]:
    """Load backup config with global + project merge.

    1. Read global config from ~/.claude/aida.yml backup: section
    2. Read project config from .claude/aida-project-context.yml
       backup: section (if exists)
    3. Merge: project values override global values (shallow merge)
    4. Apply defaults for any missing keys
    """
    config = dict(DEFAULT_CONFIG)
    config["retention"] = dict(DEFAULT_CONFIG["retention"])

    global_cfg = _read_yaml_backup_section(
        Path.home() / ".claude" / "aida.yml"
    )
    if global_cfg:
        _merge_config(config, global_cfg)

    project_cfg = _read_yaml_backup_section(
        Path.cwd() / ".claude" / "aida-project-context.yml"
    )
    if project_cfg:
        _merge_config(config, project_cfg)

    return config


def _read_yaml_backup_section(path: Path) -> Optional[dict[str, Any]]:
    """Read the backup: section from a YAML config file."""
    if not path.is_file():
        return None
    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict) and "backup" in data:
            return data["backup"]
    except Exception:
        pass
    return None


def _merge_config(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Shallow merge override into base config."""
    for key, value in override.items():
        if key == "retention" and isinstance(value, dict):
            if "retention" not in base:
                base["retention"] = dict(DEFAULT_CONFIG["retention"])
            for rk, rv in value.items():
                base["retention"][rk] = rv
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Scope checking
# ---------------------------------------------------------------------------

def should_backup(file_path: Path, config: dict[str, Any]) -> bool:
    """Check if a file should be backed up based on config."""
    if not config.get("enabled", True):
        return False
    if not file_path.is_file():
        return False
    scope = config.get("scope", "always")
    if scope == "outside-git-only" and _is_git_tracked(file_path):
        return False
    return True


def _is_git_tracked(file_path: Path) -> bool:
    """Check if a file is tracked by git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(file_path)],
            capture_output=True,
            timeout=5,
            cwd=str(file_path.parent),
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired,
            subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Storage location
# ---------------------------------------------------------------------------

def _validate_path(file_path: Path) -> None:
    """Validate that a file path is safe (no symlink traversal).

    Raises ValueError if the resolved path differs from the given path
    in a way that indicates symlink traversal.
    """
    resolved = file_path.resolve()
    if resolved.is_symlink():
        raise ValueError(f"Refusing to operate on symlink: {file_path}")


def _get_backup_dir(file_path: Path, config: dict[str, Any]) -> Path:
    """Resolve where backups are stored for a given file.

    - "global" (default): ~/.claude/.backups/ with mirrored path
    - "local": same directory as the original file
    - "/custom/path": user-specified directory with mirrored path
    """
    storage = config.get("storage", "global")
    resolved = file_path.resolve()

    if storage == "local":
        return resolved.parent

    if storage == "global":
        base = GLOBAL_BACKUP_DIR
    else:
        base = Path(storage).expanduser().resolve()

    # Mirror the original file's directory structure
    # e.g., /project/src/CLAUDE.md -> base/project/src/
    try:
        relative = resolved.parent.relative_to(Path("/"))
    except ValueError:
        relative = Path(str(resolved.parent).lstrip("/"))
    return base / relative


def _ensure_backup_dir(backup_dir: Path, config: dict[str, Any]) -> None:
    """Create backup directory with appropriate permissions."""
    storage = config.get("storage", "global")
    if storage == "local":
        return  # directory already exists (same as file's dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        backup_dir.chmod(0o700)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------

def _compute_checksum(file_path: Path) -> str:
    """Compute MD5 checksum of file contents."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


# ---------------------------------------------------------------------------
# Git context capture
# ---------------------------------------------------------------------------

def _get_git_context(file_path: Path) -> dict[str, Any]:
    """Capture git state at backup time.

    Returns git_hash (short SHA) and git_dirty (boolean).
    Graceful fallback to nulls if not in a git repo or on error.
    """
    result: dict[str, Any] = {"git_hash": None, "git_dirty": None}
    cwd = str(file_path.parent) if file_path.is_file() else None

    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if proc.returncode == 0:
            result["git_hash"] = proc.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired,
            subprocess.SubprocessError):
        return result

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if proc.returncode == 0:
            result["git_dirty"] = bool(proc.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired,
            subprocess.SubprocessError):
        pass

    return result


# ---------------------------------------------------------------------------
# Metadata sidecar
# ---------------------------------------------------------------------------

def _write_metadata(backup_path: Path, metadata: dict[str, Any]) -> None:
    """Write .meta.json sidecar alongside a backup file."""
    meta_path = Path(str(backup_path) + META_SUFFIX)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)


def _read_metadata(backup_path: Path) -> Optional[dict[str, Any]]:
    """Read .meta.json sidecar for a backup file.

    If the metadata file is missing or corrupted, automatically
    repairs it from the backup file itself.
    """
    meta_path = Path(str(backup_path) + META_SUFFIX)
    if meta_path.is_file():
        try:
            with open(meta_path, encoding="utf-8") as fh:
                text = fh.read()
            if len(text) > 100 * 1024:
                return _repair_metadata(backup_path)
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return _repair_metadata(backup_path)


def _repair_metadata(backup_path: Path) -> dict[str, Any]:
    """Rebuild missing or corrupted .meta.json from the backup file.

    Recovers: original_path (from path structure), timestamp (from
    filename), file_size (from stat), checksum (recomputed MD5).
    Sets message to "(metadata rebuilt)".
    """
    if not backup_path.is_file():
        return {}

    # Parse timestamp from filename: *.aida-backup.YYYYMMDD-HHMMSS
    name = backup_path.name
    ts_str = ""
    timestamp_iso = ""
    marker = BACKUP_SUFFIX + "."
    idx = name.find(marker)
    if idx >= 0:
        ts_str = name[idx + len(marker):]
        # Strip any extra extension (shouldn't exist, but be safe)
        if "." in ts_str:
            ts_str = ts_str.split(".")[0]
        try:
            dt = datetime.strptime(ts_str, TIMESTAMP_FMT)
            dt = dt.replace(tzinfo=timezone.utc)
            timestamp_iso = dt.isoformat()
        except ValueError:
            timestamp_iso = ""

    # Reconstruct original path from backup path + storage structure
    # The original filename is everything before .aida-backup.*
    original_name = name[:idx] if idx >= 0 else name

    metadata: dict[str, Any] = {
        "original_path": str(backup_path.parent / original_name),
        "timestamp": timestamp_iso,
        "message": "(metadata rebuilt)",
        "file_size": backup_path.stat().st_size,
        "checksum": _compute_checksum(backup_path),
        "backup_path": str(backup_path),
        "git_hash": None,
        "git_dirty": None,
    }

    _write_metadata(backup_path, metadata)
    return metadata


def _list_backups_with_metadata(
    file_path: Path, config: dict[str, Any]
) -> list[dict[str, Any]]:
    """List all backups for a file with metadata, sorted newest first."""
    backup_dir = _get_backup_dir(file_path, config)
    if not backup_dir.is_dir():
        return []

    resolved = file_path.resolve()
    prefix = resolved.name + BACKUP_SUFFIX + "."
    backups = []

    for entry in backup_dir.iterdir():
        if (entry.name.startswith(prefix)
                and not entry.name.endswith(META_SUFFIX)
                and entry.is_file()):
            meta = _read_metadata(entry)
            if meta:
                meta["backup_path"] = str(entry)
                backups.append(meta)

    backups.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    return backups


# ---------------------------------------------------------------------------
# Smart version resolution
# ---------------------------------------------------------------------------

def _resolve_version(
    file_path: Path, version: str, config: dict[str, Any]
) -> Optional[Path]:
    """Resolve a version reference to a backup file path.

    Accepts:
      - "latest": most recent backup by timestamp
      - "current": the original file itself
      - "YYYYMMDD-HHMMSS": exact timestamp match
    """
    if version == "current":
        return file_path.resolve()

    backups = _list_backups_with_metadata(file_path, config)

    if version == "latest":
        if not backups:
            return None
        return Path(backups[0]["backup_path"])

    # Match exact timestamp
    for backup in backups:
        bp = Path(backup["backup_path"])
        if bp.name.endswith(f"{BACKUP_SUFFIX}.{version}"):
            return bp

    return None


# ---------------------------------------------------------------------------
# Built-in backup operations
# ---------------------------------------------------------------------------

def builtin_backup(
    file_path: Path, config: dict[str, Any], message: str = ""
) -> dict[str, Any]:
    """Create a backup of a file with checksum dedup.

    1. Compute checksum of current file
    2. Compare to most recent backup - skip if identical
    3. Create timestamped copy
    4. Write metadata sidecar
    5. Optionally enforce retention
    """
    _validate_path(file_path)
    resolved = file_path.resolve()
    checksum = _compute_checksum(resolved)

    # Check for dedup
    backups = _list_backups_with_metadata(file_path, config)
    if backups:
        latest_checksum = backups[0].get("checksum", "")
        if latest_checksum == checksum:
            return {
                "success": True,
                "skipped": True,
                "reason": "unchanged",
                "checksum": checksum,
            }

    # Create backup
    backup_dir = _get_backup_dir(file_path, config)
    _ensure_backup_dir(backup_dir, config)

    now = datetime.now(timezone.utc)
    ts = now.strftime(TIMESTAMP_FMT)
    backup_name = f"{resolved.name}{BACKUP_SUFFIX}.{ts}"
    backup_path = backup_dir / backup_name

    # Handle same-second collisions by appending a counter
    counter = 1
    while backup_path.exists():
        backup_name = f"{resolved.name}{BACKUP_SUFFIX}.{ts}-{counter}"
        backup_path = backup_dir / backup_name
        counter += 1

    shutil.copy2(str(resolved), str(backup_path))

    # Write metadata
    git_ctx = _get_git_context(resolved)
    metadata = {
        "original_path": str(resolved),
        "timestamp": now.isoformat(),
        "message": message,
        "file_size": resolved.stat().st_size,
        "checksum": checksum,
        "backup_path": str(backup_path),
        "git_hash": git_ctx["git_hash"],
        "git_dirty": git_ctx["git_dirty"],
    }
    _write_metadata(backup_path, metadata)

    # Enforce retention if configured
    retention = config.get("retention", {})
    if retention.get("auto_enforce", True):
        _maybe_enforce_retention(file_path, config)

    return {
        "success": True,
        "skipped": False,
        "backup_path": str(backup_path),
        "checksum": checksum,
    }


def builtin_restore(
    file_path: Path,
    config: dict[str, Any],
    version: str = "latest",
) -> dict[str, Any]:
    """Restore a file from a backup version.

    1. Resolve the requested version
    2. Back up current file as safety net
    3. Copy backup over original
    """
    _validate_path(file_path)
    resolved = file_path.resolve()
    version_path = _resolve_version(file_path, version, config)

    if version_path is None:
        return {
            "success": False,
            "error": f"Version not found: {version}",
        }

    if version_path == resolved:
        return {
            "success": False,
            "error": "Cannot restore from 'current' - that's the file itself",
        }

    # Safety backup of current file
    if resolved.is_file():
        builtin_backup(file_path, config, message="pre-restore safety backup")

    # Restore
    shutil.copy2(str(version_path), str(resolved))

    meta = _read_metadata(version_path)
    return {
        "success": True,
        "restored_from": str(version_path),
        "timestamp": meta.get("timestamp", "") if meta else "",
    }


def builtin_diff(
    file_path: Path,
    config: dict[str, Any],
    version1: str = "latest",
    version2: str = "current",
) -> dict[str, Any]:
    """Generate a unified diff between two versions.

    Uses difflib.unified_diff for Python-native diff output.
    """
    path1 = _resolve_version(file_path, version1, config)
    path2 = _resolve_version(file_path, version2, config)

    if path1 is None:
        return {"success": False, "error": f"Version not found: {version1}"}
    if path2 is None:
        return {"success": False, "error": f"Version not found: {version2}"}

    try:
        lines1 = path1.read_text(encoding="utf-8").splitlines(keepends=True)
        lines2 = path2.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "Cannot diff binary files",
        }
    except OSError as e:
        return {"success": False, "error": str(e)}

    label1 = f"{file_path.name} ({version1})"
    label2 = f"{file_path.name} ({version2})"

    diff_lines = list(difflib.unified_diff(
        lines1, lines2, fromfile=label1, tofile=label2
    ))
    diff_text = "".join(diff_lines)

    return {
        "success": True,
        "diff": diff_text,
        "version1": str(path1),
        "version2": str(path2),
        "has_changes": bool(diff_lines),
    }


def builtin_list(
    file_path: Optional[Path], config: dict[str, Any]
) -> dict[str, Any]:
    """List backup versions.

    If file specified: list all versions of that file with metadata.
    If no file: list all backed-up files with version counts.
    """
    if file_path is not None:
        backups = _list_backups_with_metadata(file_path, config)
        return {
            "success": True,
            "file": str(file_path),
            "versions": backups,
            "count": len(backups),
        }

    # List all backed-up files
    storage = config.get("storage", "global")
    if storage == "global":
        scan_dir = GLOBAL_BACKUP_DIR
    elif storage == "local":
        return {
            "success": True,
            "files": [],
            "total_files": 0,
            "note": "Local storage requires a specific file path to list",
        }
    else:
        scan_dir = Path(storage).expanduser().resolve()

    if not scan_dir.is_dir():
        return {"success": True, "files": [], "total_files": 0}

    # Group backups by original file
    files_map: dict[str, int] = {}
    for bp in scan_dir.rglob(f"*{BACKUP_SUFFIX}.*"):
        if bp.name.endswith(META_SUFFIX) or not bp.is_file():
            continue
        meta = _read_metadata(bp)
        orig = meta.get("original_path", str(bp)) if meta else str(bp)
        files_map[orig] = files_map.get(orig, 0) + 1

    files_list = [
        {"original_path": k, "versions": v}
        for k, v in sorted(files_map.items())
    ]
    return {
        "success": True,
        "files": files_list,
        "total_files": len(files_list),
    }


def builtin_clean(
    config: dict[str, Any], dry_run: bool = False
) -> dict[str, Any]:
    """Apply retention policy to clean old backups.

    Enforces max_versions (per file) and max_age_days.
    If both are 0 (unlimited), does nothing.
    """
    retention = config.get("retention", {})
    max_versions = retention.get("max_versions", 0)
    max_age_days = retention.get("max_age_days", 0)

    if max_versions == 0 and max_age_days == 0:
        return {
            "success": True,
            "files_scanned": 0,
            "backups_found": 0,
            "backups_removed": 0,
            "space_freed_bytes": 0,
            "space_freed_human": "0 B",
            "note": "No retention policy configured, nothing to clean",
        }

    storage = config.get("storage", "global")
    if storage == "global":
        scan_dir = GLOBAL_BACKUP_DIR
    elif storage == "local":
        return {
            "success": True,
            "files_scanned": 0,
            "backups_found": 0,
            "backups_removed": 0,
            "space_freed_bytes": 0,
            "space_freed_human": "0 B",
            "note": "Local storage clean requires per-file enforcement",
        }
    else:
        scan_dir = Path(storage).expanduser().resolve()

    if not scan_dir.is_dir():
        return {
            "success": True,
            "files_scanned": 0,
            "backups_found": 0,
            "backups_removed": 0,
            "space_freed_bytes": 0,
            "space_freed_human": "0 B",
        }

    # Group backups by original file
    grouped: dict[str, list[Path]] = {}
    for bp in scan_dir.rglob(f"*{BACKUP_SUFFIX}.*"):
        if bp.name.endswith(META_SUFFIX) or not bp.is_file():
            continue
        meta = _read_metadata(bp)
        orig = meta.get("original_path", "") if meta else ""
        if orig not in grouped:
            grouped[orig] = []
        grouped[orig].append(bp)

    total_found = sum(len(v) for v in grouped.values())
    to_remove: list[Path] = []
    now = datetime.now(timezone.utc)

    for orig, backup_paths in grouped.items():
        # Sort newest first
        backup_paths.sort(
            key=lambda p: p.name.split(BACKUP_SUFFIX + ".")[-1],
            reverse=True,
        )
        for i, bp in enumerate(backup_paths):
            remove = False

            # max_versions check
            if max_versions > 0 and i >= max_versions:
                remove = True

            # max_age_days check
            if max_age_days > 0 and not remove:
                meta = _read_metadata(bp)
                if meta and meta.get("timestamp"):
                    try:
                        ts = datetime.fromisoformat(meta["timestamp"])
                        age_days = (now - ts).days
                        if age_days > max_age_days:
                            remove = True
                    except (ValueError, TypeError):
                        pass

            if remove:
                to_remove.append(bp)

    space_freed = 0
    if not dry_run:
        for bp in to_remove:
            try:
                space_freed += bp.stat().st_size
                bp.unlink()
                # Remove companion metadata
                meta_path = Path(str(bp) + META_SUFFIX)
                if meta_path.is_file():
                    meta_path.unlink()
            except OSError:
                pass
    else:
        for bp in to_remove:
            try:
                space_freed += bp.stat().st_size
            except OSError:
                pass

    return {
        "success": True,
        "files_scanned": len(grouped),
        "backups_found": total_found,
        "backups_removed": len(to_remove),
        "space_freed_bytes": space_freed,
        "space_freed_human": _format_size(space_freed),
        "dry_run": dry_run,
    }


def _maybe_enforce_retention(
    file_path: Path, config: dict[str, Any]
) -> None:
    """Enforce retention policy for a single file's backups.

    Called after every builtin_backup() when auto_enforce is true.
    No-op when auto_enforce is false or both limits are 0.
    """
    retention = config.get("retention", {})
    if not retention.get("auto_enforce", True):
        return
    max_versions = retention.get("max_versions", 0)
    max_age_days = retention.get("max_age_days", 0)
    if max_versions == 0 and max_age_days == 0:
        return

    backups = _list_backups_with_metadata(file_path, config)
    now = datetime.now(timezone.utc)

    for i, meta in enumerate(backups):
        remove = False
        bp = Path(meta["backup_path"])

        if max_versions > 0 and i >= max_versions:
            remove = True

        if max_age_days > 0 and not remove and meta.get("timestamp"):
            try:
                ts = datetime.fromisoformat(meta["timestamp"])
                if (now - ts).days > max_age_days:
                    remove = True
            except (ValueError, TypeError):
                pass

        if remove:
            try:
                bp.unlink()
                meta_path = Path(str(bp) + META_SUFFIX)
                if meta_path.is_file():
                    meta_path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Status and analytics
# ---------------------------------------------------------------------------

def get_status(config: dict[str, Any]) -> dict[str, Any]:
    """Return comprehensive backup analytics."""
    storage = config.get("storage", "global")
    if storage == "global":
        scan_dir = GLOBAL_BACKUP_DIR
    elif storage == "local":
        return {
            "success": True,
            "config": _config_summary(config),
            "stats": {
                "total_files_backed_up": 0,
                "total_backup_versions": 0,
                "total_size_bytes": 0,
                "total_size_human": "0 B",
                "oldest_backup": None,
                "newest_backup": None,
                "files": [],
                "note": "Local storage: use /aida backup list <file>",
            },
        }
    else:
        scan_dir = Path(storage).expanduser().resolve()

    if not scan_dir.is_dir():
        return {
            "success": True,
            "config": _config_summary(config),
            "stats": {
                "total_files_backed_up": 0,
                "total_backup_versions": 0,
                "total_size_bytes": 0,
                "total_size_human": "0 B",
                "oldest_backup": None,
                "newest_backup": None,
                "files": [],
            },
        }

    # Scan all backups
    grouped: dict[str, list[dict[str, Any]]] = {}
    for bp in scan_dir.rglob(f"*{BACKUP_SUFFIX}.*"):
        if bp.name.endswith(META_SUFFIX) or not bp.is_file():
            continue
        meta = _read_metadata(bp)
        if not meta:
            continue
        orig = meta.get("original_path", str(bp))
        if orig not in grouped:
            grouped[orig] = []
        meta["backup_path"] = str(bp)
        grouped[orig].append(meta)

    total_versions = sum(len(v) for v in grouped.values())
    total_size = 0
    all_timestamps: list[str] = []
    files_info: list[dict[str, Any]] = []

    for orig, metas in sorted(grouped.items()):
        metas.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        file_size = sum(m.get("file_size", 0) for m in metas)
        total_size += file_size
        timestamps = [m["timestamp"] for m in metas if m.get("timestamp")]
        all_timestamps.extend(timestamps)

        files_info.append({
            "original_path": orig,
            "versions": len(metas),
            "total_size_bytes": file_size,
            "total_size_human": _format_size(file_size),
            "oldest": timestamps[-1] if timestamps else None,
            "newest": timestamps[0] if timestamps else None,
        })

    all_timestamps.sort()

    return {
        "success": True,
        "config": _config_summary(config),
        "stats": {
            "total_files_backed_up": len(grouped),
            "total_backup_versions": total_versions,
            "total_size_bytes": total_size,
            "total_size_human": _format_size(total_size),
            "oldest_backup": all_timestamps[0] if all_timestamps else None,
            "newest_backup": all_timestamps[-1] if all_timestamps else None,
            "files": files_info,
        },
    }


def _config_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Extract a summary of current config for status display."""
    return {
        "enabled": config.get("enabled", True),
        "scope": config.get("scope", "always"),
        "storage": config.get("storage", "global"),
        "custom_command": config.get("custom_command", ""),
        "retention": config.get("retention", dict(DEFAULT_CONFIG["retention"])),
    }


def _format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# ---------------------------------------------------------------------------
# Custom command override
# ---------------------------------------------------------------------------

def _run_custom_command(
    command: str, file_path: Path, message: str
) -> dict[str, Any]:
    """Execute user-defined backup command with placeholder substitution."""
    expanded = command.replace("{file}", shlex.quote(str(file_path)))
    expanded = expanded.replace("{message}", shlex.quote(message))

    try:
        result = subprocess.run(
            expanded,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout.strip()}
        return {
            "success": False,
            "error": result.stderr.strip() or f"Exit code {result.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Custom command timed out"}
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_backup(file_path: Path, message: str = "") -> dict[str, Any]:
    """Main backup API. Load config, check scope, dispatch.

    Must never raise — always returns a dict.
    """
    try:
        config = load_backup_config()
        if not should_backup(file_path, config):
            return {"success": True, "skipped": True, "reason": "not in scope"}

        custom = config.get("custom_command", "")
        if custom:
            result = _run_custom_command(custom, file_path, message)
            if result.get("success"):
                return result
            # Fall back to builtin on custom command failure

        return builtin_backup(file_path, config, message=message)
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_restore(
    file_path: Path, version: str = "latest"
) -> dict[str, Any]:
    """Dispatch restore operation."""
    try:
        config = load_backup_config()
        return builtin_restore(file_path, config, version)
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_list(file_path: Optional[Path] = None) -> dict[str, Any]:
    """Dispatch list operation."""
    try:
        config = load_backup_config()
        return builtin_list(file_path, config)
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_diff(
    file_path: Path,
    version1: str = "latest",
    version2: str = "current",
) -> dict[str, Any]:
    """Dispatch diff operation."""
    try:
        config = load_backup_config()
        return builtin_diff(file_path, config, version1, version2)
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_status() -> dict[str, Any]:
    """Return full status with analytics."""
    try:
        config = load_backup_config()
        return get_status(config)
    except Exception as e:
        return {"success": False, "error": str(e)}
