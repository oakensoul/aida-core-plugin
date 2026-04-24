---
type: reference
title: Extension Prompts
description: >-
  Per-type question banks for the brainstorm skill, organized
  by category.
---

# Extension Prompts

Question banks for the brainstorm dialogue, organized by
extension type and category. Pick questions that fit the
user's idea -- do not ask all of them.

## Question Categories

### Behavior (always ask 1-2)

How should this work end to end? What does success look like?

### Quality Gates (ask when relevant)

What checks, validations, or guardrails matter?

### Edge Cases (ask when relevant)

What happens when things go wrong or input is ambiguous?

### Integration (ask when relevant)

How does this interact with existing tools or workflows?

## Agent Questions

### Behavior

- When this agent gets a task, what's its decision-making
  process? (e.g., always ask clarifying questions first /
  try the simplest approach / follow a strict checklist)
- What does a successful outcome look like for this agent?
- What information does the agent need before it can start
  working?

### Quality Gates

- What should it refuse to do or flag for human review?
- Are there outputs that need validation before the agent
  reports success?

### Edge Cases

- What should it do when it encounters ambiguous
  instructions?
- If it gets stuck, should it ask for help or try
  alternatives on its own?

### Integration

- What tools or external services does it need access to?
- Does it need to coordinate with other agents or skills?

## Skill Questions

### Behavior

- Walk me through what a successful run looks like end to
  end.
- What inputs does it need and what does it produce?
- Should it be interactive (ask questions during execution)
  or run to completion autonomously?

### Quality Gates

- What makes a run "good" vs. "acceptable" vs. "failed"?
- Are there preconditions that must be true before it starts?

### Edge Cases

- What should happen if required input is missing or
  malformed?
- If the skill partially completes, should it roll back or
  report partial results?

### Integration

- Does this skill build on or replace an existing workflow?
- What other skills or tools does the user currently use for
  this task?

## Plugin Questions

### Behavior

- What's the core workflow this plugin enables?
- What does a user see when it works well vs. when it fails?
- Who is the target audience -- individual developers, teams,
  or both?

### Quality Gates

- What standards or conventions should the plugin enforce?
- Should it validate its own output before presenting it to
  the user?

### Edge Cases

- What happens if the plugin is used in a project that
  doesn't match its assumptions (e.g., wrong language,
  missing config)?
- How should it handle version conflicts with other plugins?

### Integration

- What existing tools or workflows does this replace or
  complement?
- Does it need to work across multiple projects or is it
  project-specific?
