#!/bin/bash
set -e

# AIDA Installation Script for Test Environments
# Installs AIDA plugin from mounted directory

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PLUGIN_MOUNT="/mnt/aida-plugin"

log_info() {
    echo -e "${BLUE}[INSTALL]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[INSTALL]${NC} $1"
}

log_error() {
    echo -e "${RED}[INSTALL]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[INSTALL]${NC} $1"
}

# Check if plugin directory is mounted
if [ ! -d "$PLUGIN_MOUNT" ]; then
    log_error "Plugin directory not mounted at $PLUGIN_MOUNT"
    exit 1
fi

log_info "AIDA plugin mounted at $PLUGIN_MOUNT"

# Show plugin structure
log_info "Plugin contents:"
ls -la "$PLUGIN_MOUNT/"

# Check for plugin.json (Claude Code plugin manifest)
if [ -f "$PLUGIN_MOUNT/.claude-plugin/plugin.json" ]; then
    log_success "Found plugin.json - valid Claude Code plugin"
    log_info "Plugin manifest:"
    cat "$PLUGIN_MOUNT/.claude-plugin/plugin.json"
else
    log_warning "No .claude-plugin/plugin.json found - may not be a valid Claude Code plugin"
fi

# Check for skills directory
if [ -d "$PLUGIN_MOUNT/skills" ]; then
    log_info "Found skills directory:"
    ls -la "$PLUGIN_MOUNT/skills/"
fi

# Check for agents directory
if [ -d "$PLUGIN_MOUNT/agents" ]; then
    log_info "Found agents directory:"
    ls -la "$PLUGIN_MOUNT/agents/"
fi

# Try to add local plugin using Claude CLI
if command -v claude >/dev/null 2>&1; then
    log_info "Claude CLI is available ($(claude --version 2>&1 | head -1))"

    # Add local plugin
    log_info "Adding local plugin from $PLUGIN_MOUNT..."
    log_info "Run in Claude Code: /plugin add $PLUGIN_MOUNT"

    # Note: The actual plugin add command needs to be run interactively in Claude Code
    # This script validates the plugin structure and provides instructions

    log_success "Plugin validation complete"
    log_info ""
    log_info "To install the plugin, run these commands in Claude Code:"
    log_info "  /plugin add $PLUGIN_MOUNT"
    log_info "  /plugin list"
else
    log_error "Claude CLI not found in PATH"
    exit 1
fi

log_success "AIDA installation script complete"

exit 0
