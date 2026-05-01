---
type: reference
title: "Project Configuration Facts"
description: "All facts AIDA needs for project configuration, categorized by detection method"
---

<!-- SPDX-FileCopyrightText: 2026 The AIDA Core Authors -->
<!-- SPDX-License-Identifier: MPL-2.0 -->

# Project Configuration Facts

This document defines all facts AIDA needs for project configuration, categorized by detection method.

## Auto-Detectable Facts (No Questions Needed)

### File System Facts

- ✅ **Project name** - from directory name
- ✅ **Project root** - from context
- ✅ **Has README** - check for README.md/README.rst/README.txt
- ✅ **Has LICENSE** - check for LICENSE/LICENSE.md/LICENSE.txt
- ✅ **Has CHANGELOG** - check for CHANGELOG.md/HISTORY.md/RELEASES.md
- ✅ **Has CONTRIBUTING** - check for CONTRIBUTING.md
- ✅ **Has .gitignore** - file exists
- ✅ **Has Dockerfile** - file exists
- ✅ **Has docker-compose** - docker-compose.yml exists
- ✅ **Docs directory** - check for docs/, doc/, documentation/

### Version Control Facts

- ✅ **Is git repo** - check for .git/
- ✅ **Main branch name** - git symbolic-ref refs/remotes/origin/HEAD
- ✅ **Uses worktrees** - detect from git config / .bare/ structure
- ✅ **Remote URL** - git remote get-url origin

### Language & Tools Facts

- ✅ **Primary language** - analyze file extensions
- ✅ **All languages** - analyze all file extensions
- ✅ **Package manager** - package.json, requirements.txt, Gemfile, go.mod, Cargo.toml, composer.json
- ✅ **Build tools** - Makefile, CMakeLists.txt, build.gradle, etc.

### Testing Facts

- ✅ **Has tests** - check for test/, tests/, spec/, **tests**/
- ✅ **Testing framework** - pytest.ini, jest.config.js, .rspec, etc.

### CI/CD Facts

- ✅ **Has CI/CD** - check for .github/workflows/, .gitlab-ci.yml, .circleci/, etc.
- ✅ **CI system** - which CI files exist

### Repository Facts

- ✅ **GitHub repo** - if remote URL contains github.com
- ✅ **GitLab repo** - if remote URL contains gitlab
- ✅ **Organization/Owner** - parse from remote URL
- ✅ **Repo name** - parse from remote URL

## Inferrable Facts (Can Guess, May Ask for Confirmation)

### Project Classification

- 🔍 **Project type** - infer from structure/files
  - Web app (backend) - has server framework files
  - Web app (frontend) - has React/Vue/Angular
  - Full-stack - has both
  - Library/framework - has setup.py, package.json with "main"
  - CLI tool - has bin/ or "bin" in package.json
  - Data/ML - has notebooks, models
  - Documentation site - has Sphinx/MkDocs/Jekyll

- 🔍 **Team collaboration** - infer from commit count/contributors
  - Solo project - 1 contributor
  - Small team - 2-5 contributors
  - Large team - 5+ contributors

- 🔍 **Documentation level** - infer from docs size
  - Minimal - README only
  - Moderate - README + some docs
  - Comprehensive - extensive docs/

- 🔍 **Code organization** - infer from directory structure
  - Flat - few top-level files
  - By layer - controllers/, models/, views/
  - By feature - features/, modules/
  - Monorepo - packages/, apps/

## Facts We Must Ask (Cannot Detect)

### Preferences & Intentions

- ❓ **Branching model** - GitHub Flow vs Git Flow vs Trunk-based
  - Skip if: solo project with no specific workflow

- ❓ **Issue tracking system** - which system
  - Default: GitHub Issues if GitHub repo
  - Default: None if no remote

- ❓ **Project conventions** - coding patterns, architecture decisions
  - Optional: only ask if useful

- ❓ **API documentation approach** - if project has public API
  - Skip if: not a library or backend API

### Integration Configuration (Only if Using)

- ❓ **GitHub Project board** - only if issue_tracking = "GitHub Projects"
  - Need: org/user, project name

- ❓ **JIRA config** - only if issue_tracking = "JIRA"
  - Need: project key, URL

- ❓ **Confluence spaces** - only if using JIRA
  - Need: space names/keys

### Setup Offers (Only if Missing)

- ❓ **Create missing files** - only if they don't exist
  - README, LICENSE, .gitignore, CHANGELOG, CONTRIBUTING
  - Docker files
  - Test setup
  - CI/CD

## Configuration Strategy

### Phase 1: Detection

1. Detect all auto-detectable facts
2. Infer all inferrable facts
3. Build confidence scores for inferences

### Phase 2: Smart Questions

Only ask about:

1. **Missing critical facts** we couldn't detect or infer
2. **Low-confidence inferences** that need confirmation
3. **User preferences** we can't know (branching model, conventions)
4. **Integration details** for systems they're using

Never ask about:

- Facts we already detected (don't ask "do you have a README?" if we see one)
- Things that don't apply (don't ask about JIRA if using GitHub)
- Optional details unless relevant

### Phase 3: Minimal Friction

- If we detected everything important, ask 0-3 questions
- If project is simple/solo, ask 0-1 questions
- If complex/team project, ask 3-8 questions max
- Group related questions together

## Example Question Counts

### Simple Solo Project (Personal script)

- **Detected:** Git repo, Python, no tests, no CI, README only
- **Questions:** 0-1

- Maybe ask about branching model preference (or skip if solo)

### Standard GitHub Project

- **Detected:** Git, GitHub remote, has tests, has CI, good docs
- **Questions:** 2-3

- Branching model preference
- GitHub Project board? (if using)
- Project conventions (optional)

### Complex Team Project

- **Detected:** Git, JIRA in commits, multiple languages, extensive tests
- **Questions:** 5-8

- Branching model
- JIRA project key/URL
- Confluence spaces?
- Project conventions
- API documentation approach
