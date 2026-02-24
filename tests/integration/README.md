---
type: guide
title: AIDA Test Environments
name: test-environments
description: Docker-based test environments for validating AIDA across project types
version: 0.2.0
tags:
  - testing
  - docker
  - environments
---

# AIDA Test Environments

Docker-based test environments for validating AIDA functionality across different project types.

## Overview

This directory contains Docker configurations for testing AIDA in various project environments:

- **AIDA** - AIDA development project
- **PHP** - PHP project with Composer
- **Node.js** - Node.js project with npm
- **Python** - Python project with pip/venv
- **Monorepo** - Multi-package monorepo with npm workspaces

## Quick Start

### Build All Environments

```bash
cd test-environments

# Build base image first (required by all others)
docker-compose build base

# Build all test environments
docker-compose build
```

### Run a Specific Environment

```bash
# Start and enter the AIDA test environment
docker-compose run --rm aida

# Or any other environment
docker-compose run --rm php
docker-compose run --rm nodejs
docker-compose run --rm python
docker-compose run --rm monorepo
```

### Clean Up

```bash
# Stop all containers
docker-compose down

# Remove volumes (resets all state)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Directory Structure

```text
test-environments/
├── base/                    # Base image with Claude Code CLI
│   └── Dockerfile
├── aida/                    # AIDA project environment
│   ├── Dockerfile
│   └── sample-project/
├── php/                     # PHP project environment
│   ├── Dockerfile
│   └── sample-project/
├── nodejs/                  # Node.js project environment
│   ├── Dockerfile
│   └── sample-project/
├── python/                  # Python project environment
│   ├── Dockerfile
│   └── sample-project/
├── monorepo/                # Monorepo environment
│   ├── Dockerfile
│   └── sample-project/
├── docker-compose.yml       # Orchestration
└── README.md               # This file
```

## Testing Workflow

### 1. Build Environment

```bash
docker-compose build <environment>
```

### 2. Enter Environment

```bash
docker-compose run --rm <environment>
```

### 3. Inside Container

Once inside a container, you're in the test project directory with:

- Git repository initialized
- Dependencies installed
- Claude Code CLI available
- Ready to test AIDA functionality

Example workflow inside container:

```bash
# Check git status
git status

# Run Claude Code commands
claude --version

# Test AIDA commands (once installed)
# /init-aida
# /start-day
# etc.
```

### 4. Test AIDA Installation

Inside any container:

```bash
# Install AIDA (adjust path/method as needed)
# This will depend on how AIDA is distributed

# Test basic commands
# /help
# /init-aida
```

### 5. Test Project-Specific Behavior

Each environment has project-specific tools:

**PHP:**

```bash
composer --version
php --version
```

**Node.js:**

```bash
npm --version
node --version
npm run start
```

**Python:**

```bash
python3 --version
source venv/bin/activate
pip list
```

**Monorepo:**

```bash
npm run build
npm run test
```

## Environment Details

### Base Image

- Ubuntu 24.04
- Node.js 20.x (for Claude Code CLI)
- Git
- Claude Code CLI
- Non-root `tester` user

### AIDA Environment

- Based on base image
- Sample AIDA project structure
- `.claude/` directory with skills/agents
- Git repository initialized

### PHP Environment

- PHP 8.3
- Composer
- Sample PHP project with PSR-4 autoloading
- PHPUnit for testing

### Node.js Environment

- Node.js 20.x (from base)
- npm
- Sample Node.js project with ES modules
- ESLint for linting

### Python Environment

- Python 3.x
- pip and venv
- Sample Python project with package structure
- pytest, black, pylint

### Monorepo Environment

- npm workspaces
- Multiple packages (Node.js and Python)
- Cross-package dependencies
- Complex project structure

## Volumes

Each environment has a named volume for persistence:

- `aida-home` - AIDA environment home directory
- `php-home` - PHP environment home directory
- `nodejs-home` - Node.js environment home directory
- `python-home` - Python environment home directory
- `monorepo-home` - Monorepo environment home directory

This allows you to:

- Exit and re-enter containers without losing state
- Test installations and configurations
- Maintain git history between sessions

To reset an environment, remove its volume:

```bash
docker-compose down -v
```

## Troubleshooting

### Build Failures

If a build fails:

1. Build base image first:

   ```bash
   docker-compose build base
   ```

2. Check Dockerfile syntax in the failing environment

3. Verify sample project files exist

### Container Won't Start

```bash
# Check logs
docker-compose logs <environment>

# Remove and rebuild
docker-compose down
docker-compose build <environment>
```

### Dependencies Not Installing

Inside container:

```bash
# PHP
composer install

# Node.js
npm install

# Python
source venv/bin/activate
pip install -r requirements.txt
```

## Manual Testing Checklist

For each environment, test:

- [ ] Container builds successfully
- [ ] Claude Code CLI is installed and accessible
- [ ] Git is configured and working
- [ ] Project dependencies install correctly
- [ ] Sample code runs/compiles
- [ ] AIDA can be installed
- [ ] AIDA commands work
- [ ] Memory system functions
- [ ] Project-specific workflows work

## Notes

- All containers run as non-root `tester` user
- Git is pre-configured with test credentials
- Each environment is isolated with its own volume
- Base image must be built before other images
- Containers are ephemeral but volumes persist

## Future Enhancements

Possible additions:

- Ruby/Rails environment
- Go environment
- Java/Maven environment
- Docker-in-Docker for testing containerized workflows
- CI/CD integration examples
- Multi-stage builds for smaller images
- Automated test scripts
