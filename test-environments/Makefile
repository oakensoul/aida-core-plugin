.PHONY: help build build-base build-all clean clean-all shell-% up down test-% test-all

# Test result directory
TEST_RESULTS_DIR := $(CURDIR)/test-results

help:
	@echo "AIDA Test Environments"
	@echo ""
	@echo "Build Commands:"
	@echo "  build-base     - Build base image (required first)"
	@echo "  build-all      - Build all environments"
	@echo "  build-aida     - Build AIDA environment"
	@echo "  build-php      - Build PHP environment"
	@echo "  build-nodejs   - Build Node.js environment"
	@echo "  build-python   - Build Python environment"
	@echo "  build-monorepo - Build monorepo environment"
	@echo ""
	@echo "Test Commands (automated):"
	@echo "  test-aida      - Run tests in AIDA environment"
	@echo "  test-php       - Run tests in PHP environment"
	@echo "  test-nodejs    - Run tests in Node.js environment"
	@echo "  test-python    - Run tests in Python environment"
	@echo "  test-monorepo  - Run tests in monorepo environment"
	@echo "  test-all       - Run tests in all environments"
	@echo ""
	@echo "Shell Commands (interactive, auto-rebuild):"
	@echo "  shell-aida     - Enter AIDA environment"
	@echo "  shell-php      - Enter PHP environment"
	@echo "  shell-nodejs   - Enter Node.js environment"
	@echo "  shell-python   - Enter Python environment"
	@echo "  shell-monorepo - Enter monorepo environment"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  clean          - Stop containers and remove volumes"
	@echo "  clean-all      - Remove containers, volumes, and images"
	@echo "  up             - Start all containers in background"
	@echo "  down           - Stop all containers"
	@echo ""
	@echo "Quick Start:"
	@echo "  make build-all      # Build everything"
	@echo "  make test-all       # Run all automated tests"
	@echo "  make shell-php      # Enter PHP environment (interactive)"

build-base:
	docker-compose build base

build-all: build-base
	docker-compose build

build-%: build-base
	docker-compose build $*

shell-%:
	docker-compose run --build --rm $*

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	docker-compose down -v

clean-all:
	docker-compose down -v --rmi all

# Automated test targets
test-%: build-%
	@mkdir -p $(TEST_RESULTS_DIR)
	@echo "Running tests in $* environment..."
	docker-compose run --rm \
		-e TEST_RESULT_FILE=/mnt/test-results/$*-result.json \
		-v $(TEST_RESULTS_DIR):/mnt/test-results \
		$* /usr/local/aida-test/scripts/run-tests.sh
	@echo "Results saved to $(TEST_RESULTS_DIR)/$*-result.json"

test-all: build-all
	@mkdir -p $(TEST_RESULTS_DIR)
	@echo "Running tests in all environments..."
	@for env in aida php nodejs python monorepo; do \
		echo ""; \
		echo "========================================"; \
		echo "Testing $$env environment"; \
		echo "========================================"; \
		docker-compose run --rm \
			-e TEST_RESULT_FILE=/mnt/test-results/$$env-result.json \
			-v $(TEST_RESULTS_DIR):/mnt/test-results \
			$$env /usr/local/aida-test/scripts/run-tests.sh || true; \
	done
	@echo ""
	@echo "========================================"
	@echo "All test results saved to $(TEST_RESULTS_DIR)/"
	@echo "========================================"
	@ls -la $(TEST_RESULTS_DIR)/
