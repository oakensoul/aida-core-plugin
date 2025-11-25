.PHONY: help build build-base build-all clean clean-all shell-% up down

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
	@echo "Shell Commands (auto-rebuild before entering):"
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
	@echo "  make shell-php      # Enter PHP environment"

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
