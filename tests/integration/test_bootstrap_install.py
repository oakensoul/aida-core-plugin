# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Integration test for AIDA managed virtual environment bootstrap.

Tests the real venv creation and dependency installation flow using
a temporary directory as the AIDA home. This test actually runs
pip install, so it takes a few seconds.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from shared.bootstrap import (  # noqa: E402
    _find_requirements_txt,
    _hash_file,
    ensure_aida_environment,
    is_aida_environment_ready,
)
import shared.bootstrap as bootstrap_module  # noqa: E402


@pytest.fixture()
def aida_home(tmp_path, monkeypatch):
    """Override AIDA paths to use a temp directory."""
    monkeypatch.setattr(bootstrap_module, "AIDA_DIR", tmp_path)
    monkeypatch.setattr(bootstrap_module, "VENV_DIR", tmp_path / "venv")
    monkeypatch.setattr(bootstrap_module, "STAMP_FILE", tmp_path / ".venv-stamp")
    return tmp_path


class TestBootstrapInstall:
    """Tests that exercise the real venv creation and pip install."""

    def test_creates_venv_on_first_run(self, aida_home):
        """First call creates the venv and installs dependencies."""
        venv_dir = aida_home / "venv"
        assert not venv_dir.exists()

        ensure_aida_environment()

        assert venv_dir.exists()
        assert (venv_dir / "bin" / "python3").exists() or (
            venv_dir / "bin" / "python"
        ).exists()
        assert (venv_dir / "bin" / "pip").exists()

    def test_stamp_file_created(self, aida_home):
        """Stamp file is written after successful install."""
        stamp = aida_home / ".venv-stamp"
        assert not stamp.exists()

        ensure_aida_environment()

        assert stamp.exists()
        req = _find_requirements_txt()
        expected_hash = _hash_file(req)
        assert stamp.read_text().strip() == expected_hash

    def test_packages_installed(self, aida_home):
        """Required packages are actually installed in the venv."""
        ensure_aida_environment()

        pip = aida_home / "venv" / "bin" / "pip"
        result = subprocess.run(
            [str(pip), "list", "--format=columns"],
            capture_output=True,
            text=True,
        )
        installed = result.stdout.lower()
        assert "jinja2" in installed
        assert "pyyaml" in installed
        assert "jsonschema" in installed

    def test_fast_path_on_second_run(self, aida_home):
        """Second call fast-paths without running pip again."""
        ensure_aida_environment()

        assert is_aida_environment_ready()

        # Second call should be near-instant (no subprocess)
        ensure_aida_environment()

        # Still ready
        assert is_aida_environment_ready()

    def test_reinstalls_on_stamp_mismatch(self, aida_home):
        """Deps reinstall when stamp file doesn't match requirements."""
        ensure_aida_environment()

        # Corrupt the stamp
        stamp = aida_home / ".venv-stamp"
        stamp.write_text("stale_hash\n")

        assert not is_aida_environment_ready()

        # Should reinstall and fix the stamp
        ensure_aida_environment()

        assert is_aida_environment_ready()

    def test_site_packages_on_sys_path(self, aida_home):
        """After bootstrap, venv site-packages is on sys.path."""
        ensure_aida_environment()

        venv_dir = aida_home / "venv"
        lib_dir = venv_dir / "lib"
        site_packages = sorted(lib_dir.glob("python*/site-packages"))
        assert len(site_packages) > 0
        assert str(site_packages[-1]) in sys.path
