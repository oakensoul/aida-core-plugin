---
issue: 5
title: "Add project-level permissions for team workflows"
status: "In Progress"
github_url: "https://github.com/oakensoul/aida-core-plugin/issues/5"
branch: "task/5-project-permissions"
worktree: "issue-5-project-permissions"
started: "2026-02-15"
assignee: "@me"
---

# Issue #5: Add project-level permissions for team workflows

**Status**: In Progress
**Branch**: `task/5-project-permissions`
**Worktree**: `issue-5-project-permissions`

## Description

When working on this repo — especially with agent teams — Claude Code prompts
for permission on nearly every shell command. This creates friction and slows
down automated workflows. Since this is a known development environment with
predictable tooling, we should declare sensible project-level permissions in
`.claude/settings.json` (committed to git) so all contributors and agents can
work without constant permission prompts.

## Proposed Permissions

### Allow (safe, expected development commands)

**Build & Test:**
- `Bash(make:*)` — linting, testing, formatting, clean
- `Bash(pytest:*)` — running tests directly
- `Bash(python:*)` — script execution
- `Bash(pip:*)` — dependency management
- `Bash(ruff:*)` — linting and formatting
- `Bash(yamllint:*)` — YAML linting
- `Bash(markdownlint:*)` — Markdown linting
- `Bash(jinja2:*)` — template rendering

**Git Operations:**
- `Bash(git status)`, `Bash(git diff:*)`, `Bash(git log:*)`
- `Bash(git show:*)`, `Bash(git branch:*)`, `Bash(git checkout:*)`
- `Bash(git add:*)`, `Bash(git commit:*)`, `Bash(git fetch:*)`
- `Bash(git pull:*)`, `Bash(git stash:*)`, `Bash(git merge:*)`
- `Bash(git rebase:*)`, `Bash(git remote:*)`, `Bash(git worktree:*)`

**GitHub CLI:**
- `Bash(gh issue:*)`, `Bash(gh pr:*)`, `Bash(gh label:*)`
- `Bash(gh repo view:*)`, `Bash(gh api:*)`

**File Operations:**
- `Bash(ls:*)`, `Bash(pwd)`, `Bash(mkdir:*)`, `Bash(cp:*)`
- `Bash(mv:*)`, `Bash(chmod:*)`, `Bash(wc:*)`, `Bash(sort:*)`
- `Bash(uniq:*)`, `Bash(diff:*)`

### Ask (potentially impactful, confirm first)

- `Bash(git push:*)` — pushing to remote
- `Bash(git reset:*)` — resetting state
- `Bash(rm:*)` — file deletion
- `Bash(curl:*)` — network requests
- `Bash(wget:*)` — network requests

### Deny (dangerous in any context)

- `Bash(rm -rf:*)` — recursive force delete
- `Bash(sudo rm:*)` — privileged deletion
- `Bash(git push --force:*)` — force push

## Files to Change

- `.claude/settings.json` — create or update with project permissions

## Acceptance Criteria

- [ ] `.claude/settings.json` exists with allow/ask/deny permissions
- [ ] `make lint` runs without permission prompts
- [ ] `make test` runs without permission prompts
- [ ] Git operations (add, commit, branch) run without prompts
- [ ] GitHub CLI operations run without prompts
- [ ] Pushing to remote still prompts for confirmation
- [ ] Destructive operations are denied
- [ ] All linters pass (`make lint`)
- [ ] All tests pass (`make test`)

## Work Tracking

- Started: 2026-02-15
- Branch: `task/5-project-permissions`
- Worktree: `issue-5-project-permissions`

## Links

- [GitHub Issue](https://github.com/oakensoul/aida-core-plugin/issues/5)

## Notes

Add your work notes here...
