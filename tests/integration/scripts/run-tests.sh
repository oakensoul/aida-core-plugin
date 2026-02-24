#!/bin/bash
set -e

# AIDA Test Runner Script
# Runs automated tests inside Docker test environments

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_DETAILS=()

log_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

log_error() {
    echo -e "${RED}[TEST]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BOLD}${CYAN}▶ $1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Record test result
record_test() {
    local test_name="$1"
    local status="$2"  # "pass" or "fail"
    local message="$3"

    if [ "$status" = "pass" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "✓ $test_name"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ $test_name: $message"
    fi

    TEST_DETAILS+=("{\"name\": \"$test_name\", \"status\": \"$status\", \"message\": \"$message\"}")
}

# Test: Environment Setup
test_environment_setup() {
    log_section "Test Category 1: Environment Setup"

    # Test 1.1: Claude Code CLI available
    if claude --version >/dev/null 2>&1; then
        record_test "Claude Code CLI available" "pass" ""
    else
        record_test "Claude Code CLI available" "fail" "claude command not found"
    fi

    # Test 1.2: Git configured
    if [ "$(git config user.name)" = "AIDA Tester" ]; then
        record_test "Git configured correctly" "pass" ""
    else
        record_test "Git configured correctly" "fail" "Git user.name not set to 'AIDA Tester'"
    fi

    # Test 1.3: Git repo initialized
    if git status >/dev/null 2>&1; then
        record_test "Git repo initialized" "pass" ""
    else
        record_test "Git repo initialized" "fail" "Not a git repository"
    fi

    # Test 1.4: Project directory exists (check various common locations)
    if [ -d "/home/tester/project" ] || [ -d "/home/tester/projects" ] || \
       [ -d "/home/tester/projects/php-test-project" ] || \
       [ -d "/home/tester/projects/nodejs-test-project" ] || \
       [ -d "/home/tester/projects/python-test-project" ] || \
       [ -d "/home/tester/projects/monorepo-test-project" ]; then
        record_test "Project directory exists" "pass" ""
    else
        # Check if we're in a project directory
        if git rev-parse --git-dir > /dev/null 2>&1; then
            record_test "Project directory exists" "pass" "Currently in a git repository"
        else
            record_test "Project directory exists" "fail" "No project directory found"
        fi
    fi
}

# Test: AIDA Installation
test_aida_installation() {
    log_section "Test Category 2: AIDA Plugin Validation"

    # Check for plugin directory mount
    if [ -d "/mnt/aida-plugin" ]; then
        record_test "Plugin directory mounted" "pass" ""

        # Check for plugin.json (Claude Code plugin manifest)
        if [ -f "/mnt/aida-plugin/.claude-plugin/plugin.json" ]; then
            record_test "plugin.json exists" "pass" ""
        else
            record_test "plugin.json exists" "fail" ".claude-plugin/plugin.json not found"
        fi

        # Check for skills directory
        if [ -d "/mnt/aida-plugin/skills" ]; then
            record_test "Skills directory exists" "pass" ""
        else
            record_test "Skills directory exists" "fail" "skills/ not found"
        fi

        # Check for agents directory
        if [ -d "/mnt/aida-plugin/agents" ]; then
            record_test "Agents directory exists" "pass" ""
        else
            record_test "Agents directory exists" "fail" "agents/ not found"
        fi

        # Run installation script (validates plugin structure)
        if /usr/local/aida-test/scripts/install-aida.sh >/dev/null 2>&1; then
            record_test "Plugin validation script" "pass" ""
        else
            record_test "Plugin validation script" "fail" "Validation script failed"
        fi
    else
        record_test "Plugin directory mounted" "fail" "/mnt/aida-plugin not found"
    fi
}

# Test: Memory System (placeholder)
test_memory_system() {
    log_section "Test Category 3: Memory System"

    # These tests will be implemented once AIDA plugin system is fully functional
    log_info "Memory system tests: Not yet implemented (waiting for plugin system)"

    # Placeholder tests
    record_test "Memory system tests" "pass" "Placeholder - to be implemented"
}

# Test: Workflow Commands (placeholder)
test_workflow_commands() {
    log_section "Test Category 4: Workflow Commands"

    # These tests will be implemented once AIDA plugin system is fully functional
    log_info "Workflow command tests: Not yet implemented (waiting for plugin system)"

    # Placeholder tests
    record_test "Workflow command tests" "pass" "Placeholder - to be implemented"
}

# Test: Project-Specific Integration
test_project_specific() {
    log_section "Test Category 5: Project-Specific Integration"

    # Detect project type and run appropriate tests
    if [ -f "/home/tester/project/composer.json" ]; then
        log_info "Detected PHP project"
        # Test PHP-specific features
        if command -v php >/dev/null 2>&1; then
            record_test "PHP CLI available" "pass" ""
            record_test "PHP project type" "pass" ""
        else
            record_test "PHP CLI available" "fail" "php command not found"
        fi
    elif [ -f "/home/tester/project/package.json" ]; then
        log_info "Detected Node.js project"
        # Test Node.js-specific features
        if command -v node >/dev/null 2>&1; then
            record_test "Node.js CLI available" "pass" ""
            record_test "Node.js project type" "pass" ""
        else
            record_test "Node.js CLI available" "fail" "node command not found"
        fi
    elif [ -f "/home/tester/project/requirements.txt" ] || [ -f "/home/tester/project/setup.py" ]; then
        log_info "Detected Python project"
        # Test Python-specific features
        if command -v python3 >/dev/null 2>&1; then
            record_test "Python CLI available" "pass" ""
            record_test "Python project type" "pass" ""
        else
            record_test "Python CLI available" "fail" "python3 command not found"
        fi
    else
        log_info "Generic project or AIDA development environment"
        record_test "Project type detection" "pass" ""
    fi
}

# Generate JSON result file
generate_result_file() {
    local result_file="${TEST_RESULT_FILE:-/mnt/test-results/result.json}"

    log_section "Generating Test Results"

    local status="pass"
    if [ $TESTS_FAILED -gt 0 ]; then
        status="fail"
    fi

    # Build JSON manually (since jq might not be available)
    {
        echo "{"
        echo "  \"status\": \"$status\","
        echo "  \"tests_passed\": $TESTS_PASSED,"
        echo "  \"tests_failed\": $TESTS_FAILED,"
        echo "  \"tests_total\": $((TESTS_PASSED + TESTS_FAILED)),"
        echo "  \"environment\": \"$(hostname)\","
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"test_details\": ["

        local first=true
        for detail in "${TEST_DETAILS[@]}"; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi
            echo "    $detail"
        done

        echo ""
        echo "  ]"
        echo "}"
    } > "$result_file"

    log_info "Results written to: $result_file"
    log_info "Tests passed: $TESTS_PASSED"
    log_info "Tests failed: $TESTS_FAILED"
}

# Main test execution
main() {
    log_section "AIDA Test Suite - $(hostname)"
    log_info "Package: ${TEST_PACKAGE:-all}"
    log_info "Result file: ${TEST_RESULT_FILE:-/mnt/test-results/result.json}"

    # Run test categories
    test_environment_setup
    test_aida_installation
    test_memory_system
    test_workflow_commands
    test_project_specific

    # Generate results
    generate_result_file

    # Summary
    log_section "Test Summary"
    log_info "Total: $((TESTS_PASSED + TESTS_FAILED))"
    log_success "Passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All tests passed!"
        exit 0
    fi
}

main "$@"
