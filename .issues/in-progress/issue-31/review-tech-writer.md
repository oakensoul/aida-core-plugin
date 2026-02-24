---
title: "Technical Writer Review: Claude Code Expert Knowledge Files"
description: "Documentation quality review of 7 knowledge files for the claude-code-expert agent"
category: "review"
tags: ["documentation", "review", "knowledge", "claude-code-expert", "issue-31"]
last_updated: "2026-02-24"
status: "published"
audience: "developers"
---

# Technical Writer Review: Claude Code Expert Knowledge Files

**Reviewer:** Technical Writer Agent
**Date:** 2026-02-24
**Scope:** 7 knowledge files under `agents/claude-code-expert/knowledge/`
**Audience for reviewed files:** An AI agent (claude-code-expert) that generates
Claude Code extensions

---

## Review Summary

Overall, this is a strong documentation set. The files are well-structured, use
consistent formatting, and provide actionable guidance for an AI agent generating
extensions. The major strengths are clear table-driven reference sections, good
use of code examples, and logical progressive disclosure from concepts to details.

The most significant issues are: (1) frontmatter does not match the project
convention declared in CLAUDE.md, (2) a few cross-file inconsistencies in
terminology and cross-references, and (3) some scattered redundancy that could
be consolidated.

---

## File 1: skills.md (NEW - 603 lines)

**Quality Score: 8/10**

### Issues by Severity

#### HIGH

1. **Frontmatter does not match project convention.** The project CLAUDE.md
   requires frontmatter fields: `type`, `name`, `description`, `version`. The
   file has `type`, `title`, `description` but is missing `name` and `version`.
   Additionally, `title` is not the same as `name` per the project spec.

   Current:

   ```yaml
   ---
   type: reference
   title: Claude Code Skills Guide
   description: Comprehensive reference for creating and configuring skills in Claude Code
   ---
   ```

   Suggested:

   ```yaml
   ---
   type: reference
   name: skills
   title: Claude Code Skills Guide
   description: Comprehensive reference for creating and configuring skills in Claude Code
   version: "1.0.0"
   ---
   ```

   *This applies to all 7 files. I will note it once here and reference it in
   subsequent file reviews.*

2. **Conflicting information about required fields.** Line 100 says "All
   frontmatter fields are optional. Only `description` is recommended" but the
   Agent Skills standard section (line 137-148) says `name` and `description`
   are "Required by standard." The skills.md Core Fields table (line 108) says
   `name` defaults to directory name. This creates ambiguity about what is truly
   required. The document should clarify: "All fields are optional for Claude
   Code; `name` and `description` are required by the Agent Skills open standard
   for cross-tool compatibility."

#### MEDIUM

3. **Context budget section could be more actionable.** Lines 189-203 describe
   the budget mechanism but do not tell the agent what to do about it when
   generating skills. Add a recommendation like: "Keep skill descriptions under
   200 characters to maximize how many skills fit within the budget."

4. **"ultrathink" appears without explanation.** Line 545 says "Include the word
   'ultrathink' to enable extended thinking" but does not explain what extended
   thinking is, when to use it, or any caveats. This is a single bullet point
   that reads like an insider tip rather than documentation.

5. **Missing mention of `templates/` subdirectory in the Agent Skills standard
   section.** Line 30 lists `scripts/`, `references/`, and `assets/` as optional
   subdirectories per the standard, but line 57 in the file structure shows
   `templates/` as well. Clarify whether `templates/` is a Claude Code extension
   or part of the standard.

#### LOW

6. **Inconsistent backtick usage for field names in prose.** Some paragraphs
   reference field names without backticks (e.g., line 100 "Only `description`
   is recommended" vs. line 279 "Use `context: fork` when"). This is minor but
   noticeable.

7. **The "Backward Compatibility with Commands" section (line 169) could note
   deprecation status.** Is `commands/` actively deprecated or just legacy? The
   plugin-development.md file says "Use `skills/` for new development" which is
   stronger guidance. Align the messaging.

### Strengths

- Excellent invocation matrix table (line 119-126) -- immediately actionable.
- Progressive disclosure model (lines 446-457) is well explained.
- Clean separation between core fields, invocation control, and execution env.
- Common patterns section provides copy-paste-ready examples.

---

## File 2: subagents.md (NEW - 858 lines)

**Quality Score: 8/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue as skills.md -- see File 1, Issue 1.)

2. **Built-in agent "Bash" lacks tool information.** Lines 77-83 describe the
   Bash agent but omit the `Tools` field that every other built-in has. Is it
   Bash-only? All tools? This is a gap an AI agent would need to fill.

   Suggested addition after line 83:

   ```markdown
   - **Tools:** Bash
   ```

3. **Built-in agent "Claude Code Guide" lacks tool information.** Lines 93-97
   similarly omit the Tools field.

#### MEDIUM

4. **Agent teams section is substantial (~100 lines) but marked experimental.**
   The section (lines 563-661) is thorough, but the "experimental, disabled by
   default" status should appear more prominently -- perhaps as an admonition
   at the start of the section rather than inline in the third paragraph.

5. **`statusline-setup` and `Claude Code Guide` agents use informal names.**
   Lines 85-97 use names that don't follow kebab-case convention. Are these the
   actual system names? If so, note the inconsistency. If not, use the actual
   names. The claude-code-expert agent generating subagents might try to match
   this style.

6. **Missing guidance on system prompt length.** The document explains what goes
   in the markdown body but never says how long it should be. Skills.md has
   "Keep `SKILL.md` under 500 lines." Subagents should have analogous guidance.

7. **The `tools` field description (lines 152-170) shows two syntax options
   (comma-separated and YAML array) but does not state which is preferred.**
   For an AI agent generating files, a clear recommendation prevents
   inconsistency.

#### LOW

8. **The "Read-Only Reviewer" common pattern (line 693) includes `Bash` in the
   tools list, which contradicts the "read-only" name.** Bash can execute
   arbitrary commands including writes. Either rename to "Reviewer" or remove
   Bash from the tool list for consistency with the pattern's purpose.

9. **Minor formatting inconsistency.** The "Subagents vs Skills" comparison
   table (line 663) is great, but some cells are very dense. The "Use when" row
   could be split into sub-bullets for readability.

### Strengths

- Comprehensive coverage from built-in types through custom agents to teams.
- The "Subagents vs Skills" comparison table is excellent for decision-making.
- Complete example subagent file (lines 784-834) is production-quality.
- Background vs foreground execution section is clear and practical.
- Good coverage of CLI-defined subagents.

---

## File 3: settings.md (REWRITTEN - 1173 lines)

**Quality Score: 9/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue -- see File 1, Issue 1.)

#### MEDIUM

2. **Environment variables section is extremely long (~130 lines of tables).**
   Lines 735-862 contain 9 categorized tables of environment variables. While
   comprehensive, this creates a reference dump that may overwhelm the AI agent.
   Consider adding a "Most commonly used" callout with the top 5-8 variables
   before the full categorized listing.

3. **The `disableBypassPermissionsMode` field uses a string `"disable"` instead
   of a boolean.** Line 286-293 shows `"disableBypassPermissionsMode": "disable"`
   which is unusual. The document should note why this is a string and not a
   boolean, or confirm this is intentional.

4. **Permission evaluation order description could be clearer.** Line 160 says
   "Rules are evaluated in order: deny -> ask -> allow. The first matching rule
   wins." But this contradicts "first matching rule wins" -- if deny is always
   evaluated first, that is priority order, not first-match. Suggested
   replacement:

   Current: "Rules are evaluated in order: **deny -> ask -> allow**. The first
   matching rule wins, so deny rules always take precedence."

   Suggested: "Rules are evaluated by priority: **deny** rules are checked
   first, then **ask**, then **allow**. The highest-priority matching rule wins,
   so deny always takes precedence over allow."

5. **Sandbox section missing `allowUnsandboxedCommands` behavior details.** Line
   477 describes the field but doesn't explain what "escape hatch" means. Does
   it re-run outside sandbox? Prompt the user? This matters for an agent
   generating sandbox configurations.

#### LOW

6. **JSON schema URL not verified.** Line 80 references
   `https://json.schemastore.org/claude-code-settings.json`. If this schema
   doesn't exist or has moved, users get no validation. Worth noting that this
   URL should be verified.

7. **The "Auto-format on file write" example (line 1060) reads stdin as a file
   path from jq.** This pattern `"$(jq -r '.tool_input.file_path')"` reads from
   stdin in a subshell, but the hook receives JSON on stdin to the command, not
   to jq. The command should pipe stdin to jq:

   Current (line 1069):

   ```json
   "command": "prettier --write \"$(jq -r '.tool_input.file_path')\""
   ```

   The hooks.md file (line 511) uses a different pattern for the same task:

   ```json
   "command": "jq -r '.tool_input.file_path' | xargs -I {} prettier --write {}"
   ```

   These are functionally different approaches. The settings.md version relies
   on command substitution consuming stdin, which works but is fragile. The
   hooks.md version is clearer. Align both files to the same pattern.

### Strengths

- Excellent organization by concern (core, permissions, hooks, MCP, sandbox,
  auth, UI, enterprise).
- The example configurations section (lines 864-1008) provides 5 complete,
  realistic scenarios.
- The Settings vs CLAUDE.md comparison table at the top immediately orients
  the reader.
- Permission rule syntax section is thorough with clear examples.
- Troubleshooting section addresses real pain points.

---

## File 4: hooks.md (REWRITTEN - 889 lines)

**Quality Score: 9/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue -- see File 1, Issue 1.)

#### MEDIUM

2. **"Block Sensitive Files" example uses exit code 1, not exit code 2.** Line
   531 shows:

   ```json
   "command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 1 || exit 0"
   ```

   But the exit code reference table (line 368) specifies exit code 2 for
   blocking errors. Exit code 1 is "Other: Non-blocking error." The matching
   pattern in settings.md (line 1088) correctly uses exit 2. This example should
   use `exit 2`:

   Suggested replacement:

   ```json
   "command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 2 || exit 0"
   ```

3. **The "Hooks vs Other Extension Types" table (line 24) only compares hooks
   to skills.** The file is titled as a comprehensive hooks guide but the
   comparison table omits subagents, knowledge, and plugins. Either expand the
   table to match the one in skills.md (line 356) or rename the section to
   "Hooks vs Skills" for accuracy.

4. **`ConfigChange` listed as "Can Block?" = Yes in the lifecycle table (line
   200) but the text at line 206 says policy_settings changes cannot be
   blocked.** This partial exception should be noted in the table itself, not
   just the prose. Suggested: Change the table entry to "Yes (except
   policy_settings)".

#### LOW

5. **`once` field described as "skills only" in the structure breakdown (line
   263) but the common handler fields table (line 273) says "skills/agents
   only."** These should match. Which is correct?

   Line 263: `└── once: run only once per session (skills only)`
   Line 273: `If true, runs only once per session then removed (skills/agents only)`

   Suggested: Use "skills/agents only" in both locations.

6. **The link on line 188 uses an absolute URL path format.**
   `[agent teams](/en/agent-teams)` appears to reference an external doc site
   URL, but this is a markdown file, not a web page. This link will not resolve
   when the file is read as local markdown. Consider changing to a relative
   reference or removing the link entirely.

7. **Missing guidance on hook ordering when multiple hooks match.** If two
   matcher groups both match a tool name, do both run? In what order? Is it
   sequential or concurrent? This is relevant for an agent generating hook
   configurations.

### Strengths

- The hook type support by event section (lines 118-143) is an excellent
  quick-reference that prevents misconfiguration.
- Exit code behavior per event table (lines 373-391) is a standout -- highly
  actionable.
- The three-type taxonomy (command/prompt/agent) is clearly explained with
  distinct use cases for each.
- JSON output format section with decision control patterns is thorough.
- Security considerations section is appropriately prominent.

---

## File 5: plugin-development.md (REWRITTEN - 1030 lines)

**Quality Score: 8/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue -- see File 1, Issue 1.)

2. **The `aida-config.json` section (lines 738-803) is AIDA-specific content
   in a Claude Code reference doc.** This section describes AIDA framework
   concepts (`config`, `recommendedPermissions`) that are not part of the Claude
   Code plugin specification. An AI agent using this as a Claude Code reference
   would conflate AIDA-specific features with standard Claude Code plugin
   capabilities.

   Suggested: Either (a) clearly label this section as "AIDA Framework
   Extension" with a note that these fields are not part of the Claude Code
   plugin spec, or (b) move it to a separate AIDA-specific knowledge file.

#### MEDIUM

3. **The `settings.json` plugin component (lines 372-387) says "Currently, only
   the `agent` key is supported."** This is a significant limitation that could
   change. The document should note the version or date this was verified, so
   the AI agent knows to check for updates.

4. **Dependencies section (lines 847-867) lacks context on support status.** Are
   plugin dependencies actually resolved by Claude Code? Or is this a planned
   feature? The section presents version operators but doesn't clarify whether
   Claude Code currently enforces these constraints. If not yet implemented,
   this should be marked clearly.

5. **Marketplace `strict` field description (lines 730-737) is confusing.** The
   table says `true` (default) means "plugin.json is authoritative" and
   marketplace can "supplement." But `false` means "Marketplace entry is the
   entire definition." The relationship between strict mode and who controls
   what is not intuitive. Adding a concrete example of each mode would help.

6. **The "complete structure" diagram (lines 74-103) includes both `commands/`
   and `skills/` but the component location table (lines 110-121) describes
   them separately.** Consider adding a note to the diagram that `commands/`
   is legacy.

#### LOW

7. **The CLI commands section (lines 440-500) lists commands but does not show
   expected output.** For an AI agent that might need to parse or interpret CLI
   output, showing sample output would be valuable.

8. **Plugin caching explanation (lines 542-570) is practical but could use a
   diagram.** The concept that marketplace plugins are copied to a cache and
   path traversal breaks is important. A simple before/after path diagram would
   help.

9. **Missing cross-reference to hooks.md for plugin hooks details.** The hooks
   section (lines 258-289) duplicates some information from hooks.md (the three
   hook types, `$ARGUMENTS` syntax) rather than referencing hooks.md and adding
   only plugin-specific details.

### Strengths

- The "When to Use Plugins vs Standalone Configuration" section (lines 30-53)
  is immediately useful for decision-making.
- Comprehensive plugin.json schema documentation with both required and optional
  fields.
- Multiple marketplace source types (GitHub, Git URL, NPM, pip) well documented.
- The converting standalone to plugin section provides a clear migration path.
- Quality checklist (lines 889-900) is practical and complete.
- Plugin organization patterns (lines 911-966) show three levels of complexity.

---

## File 6: framework-design-principles.md (UPDATED)

**Quality Score: 8/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue -- see File 1, Issue 1.)

#### MEDIUM

2. **The document references itself as the "authoritative source" (line 14) with
   a copy at `docs/EXTENSION_FRAMEWORK.md`, but this synchronization burden is
   not automated.** Over time, the copy will drift. Consider either removing the
   copy or adding tooling to keep them in sync.

3. **Quality Standards for Hooks section (lines 537-568) now covers three hook
   types but the "What Belongs" section could be more specific about when to
   choose each type.** The current text lists all three types but the "Excellent"
   criteria focus on `command` hooks (mentioning `jq` for JSON parsing). Add
   parallel "Excellent" criteria for `prompt` and `agent` hooks.

4. **Plugins "Contains" list (lines 158-160) is sparse compared to the actual
   plugin capabilities documented in plugin-development.md.** The list says
   "Bundled agents and skills" but plugins also contain hooks, MCP servers, LSP
   servers, output styles, and settings. Update to match:

   Current (lines 157-160):

   ```markdown
   - Bundled agents and skills
   - Plugin metadata (plugin.json)
   - Documentation (README)
   ```

   Suggested:

   ```markdown
   - Bundled agents, skills, hooks, MCP servers, LSP servers, and output styles
   - Plugin metadata (plugin.json)
   - Default settings (settings.json)
   - Documentation (README)
   ```

#### LOW

5. **The Mermaid diagram (lines 238-261) is useful but may not render in all
   contexts where the AI agent reads the file.** Consider adding the text-based
   layer stack (which already exists at lines 265-283) as the primary diagram
   and the Mermaid version as supplementary.

6. **Auto memory description (line 143) could conflict with subagent memory.**
   The document describes auto memory as system-maintained, but subagent memory
   (documented in subagents.md) is agent-maintained via explicit read/write.
   A brief note distinguishing these would prevent confusion.

### Strengths

- The Consultant Rule (lines 307-324) is excellent conceptual framing.
- Context Layering visual model provides two representations (Mermaid + text).
- Quality standards sections have clear "What Belongs / Does NOT Belong / Good
  Enough / Excellent" structure.
- The "Extensions Are Definitions" section (lines 328-358) is a critical insight
  well articulated.
- Hooks section properly covers all three types with the determinism distinction.

---

## File 7: index.md (UPDATED)

**Quality Score: 7/10**

### Issues by Severity

#### HIGH

1. **Frontmatter missing `name` and `version` per project convention.** (Same
   issue -- see File 1, Issue 1.)

2. **References two files that were not included in this review and may not
   exist yet: `extension-types.md` and `design-patterns.md`.** Lines 29 and
   37 reference these documents in the index. If these files don't exist, the
   index is misleading. If they do exist, they should be reviewed for
   consistency with the other 7 files.

   The quick reference table (lines 131-161) routes multiple questions to these
   files. If they don't exist, those entries should be removed or marked as
   "planned."

#### MEDIUM

3. **External resources URLs (lines 168-169) may be incorrect.** The URLs
   `https://code.claude.com/docs/en/overview` and
   `https://platform.claude.com/docs/en/agent-sdk/overview` should be verified.
   If they 404, the AI agent following this guidance will waste time fetching
   dead links.

4. **The `claude-md-files.md` entry (lines 60-70) references features like the
   import system and `/memory` command.** These are specific enough that if
   `claude-md-files.md` doesn't document them accurately, the index description
   becomes misleading. Cross-verify that the actual file covers all listed
   topics.

5. **Missing document summaries for the new files.** The entries for
   `skills.md`, `subagents.md`, `hooks.md`, and `settings.md` now cover
   significantly more content than the index descriptions suggest. For example,
   the `hooks.md` entry mentions "3 hook types" which is correct, but the
   `settings.md` entry doesn't mention sandbox network configuration, which is
   a major new section.

#### LOW

6. **The quick reference table has inconsistent question formatting.** Some
   questions use quotes and some don't. Some are questions and some are
   statements. Standardize to quoted questions consistently.

7. **No document for "How do I configure MCP servers?"** The settings.md file
   covers MCP configuration, but the quick reference table doesn't have an entry
   for MCP. Add one.

### Strengths

- Clear "When to use" framing for each document.
- The quick reference table is excellent for rapid navigation.
- External resources section with WebFetch guidance is practical.

---

## Cross-File Consistency Issues

### 1. Frontmatter Convention Mismatch (ALL FILES)

All 7 files use `type`, `title`, `description` but the project CLAUDE.md
specifies frontmatter should include `type`, `name`, `description`, `version`.
Every file is missing `name` and `version`. The `title` field is not mentioned
in the project convention. This needs resolution: either update the project
convention to match what the files use, or update all files to match the
convention.

### 2. Hook Example Inconsistency Between settings.md and hooks.md

The "block sensitive files" pattern appears in both files with different exit
codes:

- **hooks.md line 531:** Uses `exit 1` (incorrect per the documented spec)
- **settings.md line 1088:** Uses `exit 2` (correct per the documented spec)

Both files should use `exit 2` for blocking behavior.

### 3. Auto-Format Example Inconsistency Between settings.md and hooks.md

- **settings.md line 1069:** Uses `$(jq -r '.tool_input.file_path')` command
  substitution
- **hooks.md line 511:** Uses `jq -r '.tool_input.file_path' | xargs` pipe
  pattern

Both accomplish the same goal. Pick one canonical pattern and use it
consistently.

### 4. Terminology: "Subagent" vs "Agent"

The files are mostly consistent in using "subagent" for the definitions in
`agents/` directories, but there are occasional slips:

- framework-design-principles.md line 44: "Agents represent expertise" should
  be "Subagents represent expertise" (the section header already says "Subagent"
  but the extended text sometimes drops the "sub-" prefix)
- plugin-development.md line 89: "Subagent definitions" but line 241: "Agents
  in Plugins" (header inconsistency)

The convention established in framework-design-principles.md is clear: Claude
Code is the agent, `/agents` files define subagents. Apply this consistently.

### 5. Hook Events Count

- hooks.md line 147: "Claude Code supports 17 hook events"
- framework-design-principles.md line 207-217: Lists 17 events

These match. However, if events are added in the future, two files must be
updated. Consider having only hooks.md state the count and having
framework-design-principles.md reference hooks.md for the complete list.

### 6. Skills "commands/" Backward Compatibility Messaging

- skills.md line 169: "Files in `.claude/commands/` still work"
- plugin-development.md line 131: "Use `skills/` for new development;
  `commands/` is maintained for backward compatibility"

These are consistent but skills.md is softer about deprecation. Consider
matching the plugin-development.md tone in skills.md.

### 7. Cross-Reference Gaps

- skills.md references "subagents documentation" (line 317) without a specific
  filename.
- hooks.md line 298 says "For full hook documentation, see the dedicated hooks
  knowledge file" -- but this IS the hooks file. This text appears to be copied
  from settings.md where it makes sense.
- plugin-development.md line 239 says "see the skills knowledge file" without
  a path.

All cross-references should use the actual filename:
`knowledge/subagents.md`, `knowledge/hooks.md`, `knowledge/skills.md`.

### 8. MCP Server Configuration Split

MCP server configuration appears in settings.md (lines 404-445) and
plugin-development.md (lines 293-316). The overlap is minimal and each focuses
on its own scope (global config vs plugin-bundled), which is appropriate.
However, neither cross-references the other. Add cross-references.

---

## Redundancy Assessment

### Acceptable Duplication

The following duplication is intentional and helpful -- each file provides
context-appropriate coverage:

- **Hook configuration structure** appears in settings.md and hooks.md. The
  settings.md version is a summary; hooks.md is the full reference. This is
  appropriate progressive disclosure.

- **Extension type comparison tables** appear in skills.md, subagents.md, and
  framework-design-principles.md. Each is tailored to the file's perspective.

### Unnecessary Duplication

1. **Plugin hooks section** (plugin-development.md lines 258-289) duplicates
   hook type descriptions from hooks.md. The plugin file should focus on
   plugin-specific hook mechanics (hooks.json location, `CLAUDE_PLUGIN_ROOT`,
   plugin label in /hooks menu) and reference hooks.md for the general hook
   model.

2. **Hook handler fields** appear in both settings.md (lines 369-389) and
   hooks.md (lines 266-287). The settings.md version should be a brief summary
   referencing hooks.md, not a duplicate table.

---

## Specific Fix Suggestions

### Fix 1: hooks.md Exit Code Error

**Location:** hooks.md line 531
**Problem:** Exit code 1 used instead of exit code 2 for blocking

Current:

```json
"command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 1 || exit 0"
```

Replacement:

```json
"command": "jq -e '.tool_input.file_path | test(\"\\\\.env|\\\\.git/\")' && exit 2 || exit 0"
```

### Fix 2: hooks.md Stale Self-Reference

**Location:** hooks.md line 298 (appears via settings.md copy)
**Problem:** This text is not present in hooks.md but the pattern exists in
settings.md line 298: "For full hook documentation, see the dedicated hooks
knowledge file." This makes sense in settings.md. Verify this reference points
to `knowledge/hooks.md` explicitly.

### Fix 3: skills.md Cross-Reference

**Location:** skills.md line 317
**Problem:** Vague reference to "subagents documentation"

Current: "see the subagents documentation"
Replacement: "see `knowledge/subagents.md`"

### Fix 4: plugin-development.md Cross-Reference

**Location:** plugin-development.md line 239
**Problem:** Vague reference to "skills knowledge file"

Current: "see the skills knowledge file"
Replacement: "see `knowledge/skills.md`"

### Fix 5: hooks.md `once` Field Inconsistency

**Location:** hooks.md line 263 vs line 273
**Problem:** "skills only" vs "skills/agents only"

Replace line 263 text from:
`└── once: run only once per session (skills only)`
To:
`└── once: run only once per session (skills/agents only)`

### Fix 6: hooks.md Dead Link

**Location:** hooks.md line 188
**Problem:** Link format `/en/agent-teams` is an absolute URL path, not a
relative markdown link

Current: `[agent teams](/en/agent-teams)`
Replacement: `agent teams (see `knowledge/subagents.md`, Agent Teams section)`

### Fix 7: subagents.md Missing Bash Agent Tools

**Location:** subagents.md after line 83
**Problem:** Bash built-in agent has no Tools field

Add: `- **Tools:** Bash`

### Fix 8: framework-design-principles.md Plugin Contains List

**Location:** framework-design-principles.md lines 157-160
**Problem:** Incomplete plugin component list

Current:

```markdown
- Bundled agents and skills
- Plugin metadata (plugin.json)
- Documentation (README)
```

Replacement:

```markdown
- Bundled agents, skills, hooks, MCP servers, LSP servers, and output styles
- Plugin metadata (plugin.json)
- Default settings (settings.json)
- Documentation (README)
```

---

## Overall Quality Scores

| File | Score | Assessment |
| ---- | ----- | ---------- |
| skills.md | 8/10 | Strong reference. Fix the required-fields ambiguity and add cross-refs. |
| subagents.md | 8/10 | Comprehensive. Fill in missing built-in agent details and add length guidance. |
| settings.md | 9/10 | Excellent reference. Align examples with hooks.md patterns. |
| hooks.md | 9/10 | Best file in the set. Fix the exit code error and stale link. |
| plugin-development.md | 8/10 | Thorough. Separate AIDA-specific content and improve cross-references. |
| framework-design-principles.md | 8/10 | Good conceptual foundation. Update plugin section to match reality. |
| index.md | 7/10 | Functional but references potentially missing files. Verify and update. |

**Overall Set Score: 8.1/10**

This is a well-crafted documentation set that provides an AI agent with
actionable, structured reference material for generating Claude Code extensions.
The primary areas for improvement are: consistent frontmatter, cross-file
reference accuracy, and a few incorrect code examples. No structural
reorganization is needed.
