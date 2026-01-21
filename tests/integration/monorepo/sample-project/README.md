---
type: readme
title: Monorepo Test Project
description: Sample monorepo for testing AIDA functionality
---

# Monorepo Test Project

Sample monorepo for testing AIDA functionality in monorepo environments.

## Structure

```text
packages/
├── api/              - Node.js API service
├── web-app/          - Node.js web application
├── python-service/   - Python service
└── shared/           - Shared utilities
```

## Purpose

Tests AIDA functionality in a complex monorepo environment:

- npm workspaces
- Multiple languages (Node.js, Python)
- Cross-package dependencies
- Monorepo-specific workflows

## Usage

```bash
# Install all dependencies
npm install

# Run all tests
npm test

# Run specific package
npm run start --workspace=@monorepo/api
```

## Python Service

```bash
cd packages/python-service
source venv/bin/activate
python app.py
```
