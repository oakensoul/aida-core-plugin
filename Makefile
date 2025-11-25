# AIDA Core Plugin Makefile
# Run `make help` for available targets

PLUGIN_PATH := $(shell pwd)
PLUGIN_NAME := aida-core

.PHONY: help dev-mode-enable dev-mode-disable dev-mode test lint lint-py lint-yaml lint-md lint-frontmatter lint-fix install clean

help: ## Show this help message
	@echo "AIDA Core Plugin - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# Development Mode
dev-mode-enable: ## Enable dev mode - use local plugin in Claude Code
	@echo "=== AIDA Dev Mode: ENABLE ==="
	@echo ""
	@echo "Run these commands in Claude Code:"
	@echo ""
	@echo "  1. Remove installed version (if any):"
	@echo "     /plugin remove $(PLUGIN_NAME)"
	@echo ""
	@echo "  2. Add local development version:"
	@echo "     /plugin add $(PLUGIN_PATH)"
	@echo ""
	@echo "  3. Verify it's loaded:"
	@echo "     /plugin list"
	@echo ""

dev-mode-disable: ## Disable dev mode - switch back to released plugin
	@echo "=== AIDA Dev Mode: DISABLE ==="
	@echo ""
	@echo "Run these commands in Claude Code:"
	@echo ""
	@echo "  1. Remove local version:"
	@echo "     /plugin remove $(PLUGIN_NAME)"
	@echo ""
	@echo "  2. Install released version:"
	@echo "     /plugin install $(PLUGIN_NAME)@aida-marketplace"
	@echo ""
	@echo "  3. Verify it's loaded:"
	@echo "     /plugin list"
	@echo ""

dev-mode: ## Show dev mode status and options
	@echo "=== AIDA Dev Mode ==="
	@echo ""
	@echo "Plugin path: $(PLUGIN_PATH)"
	@echo "Plugin name: $(PLUGIN_NAME)"
	@echo ""
	@echo "Commands:"
	@echo "  make dev-mode-enable   - Switch to local development version"
	@echo "  make dev-mode-disable  - Switch back to released version"
	@echo ""

# Testing
test: ## Run pytest tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=skills/aida-dispatch/scripts --cov-report=term-missing

# Linting
lint: lint-py lint-yaml lint-md lint-frontmatter ## Run all linters (Python, YAML, Markdown, Frontmatter)

lint-py: ## Run ruff linter on Python files
	ruff check skills/ tests/ scripts/

lint-yaml: ## Run yamllint on YAML files
	yamllint -c .yamllint.yml .github/ skills/ templates/

lint-md: ## Run markdownlint on Markdown files
	markdownlint '**/*.md' --ignore node_modules

lint-frontmatter: ## Validate frontmatter in SKILL.md files
	python3 scripts/validate_frontmatter.py

lint-fix: ## Run ruff linter with auto-fix
	ruff check skills/ tests/ scripts/ --fix

lint-fix-md: ## Run markdownlint with auto-fix
	markdownlint '**/*.md' --ignore node_modules --fix

# Dependencies
install: ## Install Python dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov ruff

# Cleanup
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
