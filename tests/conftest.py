# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Shared test fixtures for pytest.

Handles sys.modules restoration to prevent cross-skill module
pollution when multiple test files import different skills'
``operations`` packages in a single pytest session.
"""

import sys


def pytest_runtest_setup(item):
    """Restore the correct operations modules before each test.

    Each test module saves its own ``_ops_snapshot`` dict right
    after importing the operations modules it needs.  This hook
    reinstates that snapshot so that relative imports inside the
    source code (e.g. ``from ..scaffold_ops.context import ...``)
    resolve to the correct skill's package.
    """
    snapshot = getattr(item.module, "_ops_snapshot", None)
    if snapshot is None:
        return

    # Clear any operations modules currently cached
    for key in list(sys.modules):
        if key == "operations" or key.startswith("operations."):
            del sys.modules[key]

    # Restore this test module's snapshot
    sys.modules.update(snapshot)
