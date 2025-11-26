# AIDA Core Plugin Makefile
# Run `make help` for available targets

PLUGIN_PATH := $(shell pwd)
PLUGIN_NAME := aida-core

.PHONY: help dev-mode-enable dev-mode-disable dev-mode test lint lint-py lint-yaml lint-md lint-frontmatter lint-fix install clean \
        docker-build docker-build-base docker-build-all docker-shell-% docker-clean docker-clean-all \
        docker-test-% docker-test-all

help: ## Show this help message
	@echo "AIDA Core Plugin - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# Development Mode
dev-mode-enable: ## Enable dev mode - register local plugin with Claude Code
	@python3 scripts/dev_mode.py enable

dev-mode-disable: ## Disable dev mode - unregister local plugin from Claude Code
	@python3 scripts/dev_mode.py disable

dev-mode: ## Show dev mode status
	@python3 scripts/dev_mode.py status

# Testing
test: ## Run pytest tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=skills/aida-dispatch/scripts --cov-report=term-missing

# Docker Test Environments
docker-build-base: ## Build base Docker test image (required first)
	cd test-environments && docker-compose build base

docker-build-all: docker-build-base ## Build all Docker test environments
	cd test-environments && docker-compose build

docker-build-%: docker-build-base ## Build specific environment (e.g., docker-build-php)
	cd test-environments && docker-compose build $*

docker-test-%: ## Run automated tests in specific environment (e.g., docker-test-php)
	cd test-environments && $(MAKE) test-$*

docker-test-all: ## Run automated tests in all Docker environments
	cd test-environments && $(MAKE) test-all

docker-shell-%: ## Enter a Docker test environment (e.g., docker-shell-php)
	cd test-environments && docker-compose run --build --rm $*

docker-clean: ## Stop containers and remove volumes
	cd test-environments && docker-compose down -v

docker-clean-all: ## Remove containers, volumes, and images
	cd test-environments && docker-compose down -v --rmi all

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
