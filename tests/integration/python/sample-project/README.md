---
type: readme
title: Python Test Project
description: Sample Python project for testing AIDA functionality
---

# Python Test Project

Sample Python project for testing AIDA functionality in Python environments.

## Structure

- `src/calculator/` - Calculator module
- `tests/` - Unit tests
- `requirements.txt` - Python dependencies
- `venv/` - Virtual environment (created during build)

## Purpose

Tests AIDA functionality in a typical Python project environment:

- pip/venv dependency management
- Python package structure
- pytest testing
- Python-specific workflows

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest

# Format code
black src/

# Lint code
pylint src/
```
