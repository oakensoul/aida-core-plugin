#!/bin/bash
# Switch Claude Code to use local development version

PLUGIN_PATH="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_NAME="aida-core"

echo "=== AIDA Dev Mode ==="
echo ""
echo "To use this local version of aida-core-plugin in Claude Code:"
echo ""
echo "  1. Remove installed version (if any):"
echo "     /plugin remove ${PLUGIN_NAME}"
echo ""
echo "  2. Add local development version:"
echo "     /plugin add ${PLUGIN_PATH}"
echo ""
echo "  3. Verify it's loaded:"
echo "     /plugin list"
echo ""
echo "To switch back to the released version:"
echo "     /plugin remove ${PLUGIN_NAME}"
echo "     /plugin install ${PLUGIN_NAME}@aida-marketplace"
echo ""
