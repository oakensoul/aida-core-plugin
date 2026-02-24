---
type: reference
title: Plugin Development Guide
description: Comprehensive guide to creating, structuring, and distributing Claude Code plugins
---

# Plugin Development

Plugins are the unit of distribution for Claude Code extensions. They package
skills, agents, hooks, MCP servers, LSP servers, output styles, and default
settings into installable bundles that can be shared across projects and teams.

## What is a Plugin?

A plugin is a **distributable package** that can contain:

- Skills (process definitions + automation capabilities)
- Agents (expert personas / subagent definitions)
- Hooks (event handlers for lifecycle automation)
- MCP servers (external tool integrations)
- LSP servers (code intelligence / language server protocol)
- Output styles (response formatting customizations)
- Default settings (plugin-applied configuration)
- Shared resources (templates, scripts, references)
- Metadata for installation and discovery

Plugins solve the distribution problem: "How do I share my extensions with
others?"

## When to Use Plugins vs Standalone Configuration

| Approach | Skill Names | Best For |
| -------- | ----------- | -------- |
| **Standalone** (`.claude/` directory) | `/hello` | Personal workflows, project-specific customizations, quick experiments |
| **Plugins** (directories with `.claude-plugin/plugin.json`) | `/plugin-name:hello` | Sharing with teammates, distributing to community, versioned releases |

**Use standalone configuration when:**

- Customizing Claude Code for a single project
- The configuration is personal and does not need sharing
- Experimenting with skills or hooks before packaging
- You want short skill names like `/hello`

**Use plugins when:**

- You want to share functionality with your team or community
- You need the same skills/agents across multiple projects
- You want version control and easy updates
- You are distributing through a marketplace
- You accept namespaced skills like `/my-plugin:hello`

Start with standalone configuration for quick iteration, then convert to a
plugin when ready to share.

## Plugin Structure

### Required Files

The only required file is `.claude-plugin/plugin.json`:

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # Plugin manifest (name is the only required field)
└── (any components)
```

The manifest is technically optional -- Claude Code can auto-discover
components in default locations and derive the plugin name from the directory
name. Use a manifest when you need metadata or custom component paths.

### Complete Structure

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest
├── commands/                 # Legacy skills as markdown files
│   └── quick-action.md
├── skills/                   # Agent Skills with SKILL.md files
│   └── code-review/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── validate.sh
│       └── references/
│           └── checklist.md
├── agents/                   # Subagent definitions
│   ├── security-reviewer.md
│   └── performance-tester.md
├── hooks/                    # Hook configurations
│   └── hooks.json
├── settings.json             # Default settings (e.g., agent key)
├── .mcp.json                 # MCP server definitions
├── .lsp.json                 # LSP server configurations
├── outputStyles/             # Output style customizations
│   └── concise.md
├── scripts/                  # Utility scripts for hooks/skills
│   ├── format-code.sh
│   └── security-scan.py
├── README.md                 # Documentation
├── CHANGELOG.md              # Version history
├── LICENSE                   # License file
└── .gitignore
```

### Component Location Rules

All component directories must be at the plugin root, **not** inside
`.claude-plugin/`. Only `plugin.json` goes inside `.claude-plugin/`.

| Component | Default Location | Purpose |
| --------- | ---------------- | ------- |
| Manifest | `.claude-plugin/plugin.json` | Plugin metadata and configuration |
| Skills | `skills/` | Agent Skills with `<name>/SKILL.md` structure |
| Commands | `commands/` | Legacy skill markdown files (still supported) |
| Agents | `agents/` | Subagent markdown files |
| Hooks | `hooks/hooks.json` | Hook configuration |
| MCP servers | `.mcp.json` | MCP server definitions |
| LSP servers | `.lsp.json` | Language server configurations |
| Settings | `settings.json` | Default configuration applied when plugin is enabled |
| Output styles | `outputStyles/` | Response formatting customizations |

### Commands vs Skills (Backward Compatibility)

Both `commands/` and `skills/` directories are supported:

- `commands/` contains simple markdown files (legacy format)
- `skills/` contains directories with `SKILL.md` files (recommended)

If a command and skill share the same name, the skill takes precedence.
Use `skills/` for new development; `commands/` is maintained for backward
compatibility.

## plugin.json Schema

### Required Fields

If you include a manifest, `name` is the only required field:

```json
{
  "name": "my-plugin"
}
```

The name is used for namespacing components. For example, a skill `hello`
in plugin `my-plugin` becomes `/my-plugin:hello`.

### Complete Schema

```json
{
  "name": "my-plugin",
  "version": "2.1.0",
  "description": "Brief description of what this plugin provides",
  "author": {
    "name": "Your Name or Organization",
    "email": "author@example.com",
    "url": "https://github.com/username"
  },
  "license": "MIT",
  "repository": "https://github.com/username/my-plugin",
  "homepage": "https://your-plugin-docs.example.com",
  "keywords": ["keyword1", "keyword2"],
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "lspServers": "./.lsp.json",
  "outputStyles": "./styles/"
}
```

### Metadata Fields

| Field | Required | Description |
| ----- | -------- | ----------- |
| `name` | Yes | Unique identifier (kebab-case, no spaces) |
| `version` | No | Semantic version (X.Y.Z). If also set in marketplace entry, plugin.json takes priority. |
| `description` | No | One-line description shown in plugin manager |
| `author` | No | Creator info (`{name, email, url}` object) |
| `license` | No | SPDX license identifier |
| `repository` | No | Source code URL |
| `homepage` | No | Documentation URL |
| `keywords` | No | Discovery tags |

### Component Path Fields

Custom paths **supplement** default directories -- they do not replace them.
All paths must be relative to plugin root and start with `./`.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `commands` | string or array | Additional command files/directories |
| `agents` | string or array | Additional agent files |
| `skills` | string or array | Additional skill directories |
| `hooks` | string, array, or object | Hook config paths or inline config |
| `mcpServers` | string, array, or object | MCP config paths or inline config |
| `lspServers` | string, array, or object | LSP config paths or inline config |
| `outputStyles` | string or array | Additional output style files/directories |

Multiple paths can be specified as arrays:

```json
{
  "commands": [
    "./specialized/deploy.md",
    "./utilities/batch-process.md"
  ],
  "agents": [
    "./custom-agents/reviewer.md",
    "./custom-agents/tester.md"
  ]
}
```

## Plugin Component Details

### Skills in Plugins

Skills live in the `skills/` directory. Each skill is a folder containing
a `SKILL.md` file. The folder name becomes the skill name, prefixed with
the plugin namespace.

```text
skills/
├── code-review/
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
└── deploy/
    └── SKILL.md
```

Plugin skills are automatically discovered when installed. Claude can invoke
them based on task context, and users invoke them via `/plugin-name:skill-name`.

For complete skill authoring guidance, see the skills knowledge file.

### Agents in Plugins

Agents live in the `agents/` directory as markdown files with YAML frontmatter:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
---

You are a security expert. When reviewing code, check for...
```

Plugin agents appear in the `/agents` interface and can be invoked
automatically by Claude or manually by users.

### Hooks in Plugins

Plugin hooks are configured in `hooks/hooks.json` at the plugin root. The
format is the same as hooks in `settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

Hooks can also be defined inline in `plugin.json` under the `hooks` field.

Three hook types are supported:

- `command` -- Execute shell commands or scripts
- `prompt` -- Evaluate a prompt with an LLM (uses `$ARGUMENTS` for context)
- `agent` -- Run an agentic verifier with tool access

Use `${CLAUDE_PLUGIN_ROOT}` in hook commands to reference files within the
plugin directory (see Environment Variables section below).

### MCP Servers in Plugins

MCP server configurations go in `.mcp.json` at the plugin root, or inline
in `plugin.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    },
    "plugin-api-client": {
      "command": "npx",
      "args": ["@company/mcp-server", "--plugin-mode"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

Plugin MCP servers start automatically when the plugin is enabled and appear
as standard MCP tools in Claude's toolkit.

### LSP Servers in Plugins

LSP (Language Server Protocol) plugins give Claude real-time code intelligence:
diagnostics after edits, go-to-definition, find references, and hover info.

Configuration goes in `.lsp.json` at the plugin root, or inline in
`plugin.json` under `lspServers`:

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

**Required LSP fields:**

| Field | Description |
| ----- | ----------- |
| `command` | The LSP binary to execute (must be in PATH) |
| `extensionToLanguage` | Maps file extensions to language identifiers |

**Optional LSP fields:**

| Field | Description |
| ----- | ----------- |
| `args` | Command-line arguments for the LSP server |
| `transport` | Communication transport: `stdio` (default) or `socket` |
| `env` | Environment variables for the server |
| `initializationOptions` | Options passed during server initialization |
| `settings` | Settings via `workspace/didChangeConfiguration` |
| `workspaceFolder` | Workspace folder path |
| `startupTimeout` | Max time to wait for startup (ms) |
| `shutdownTimeout` | Max time for graceful shutdown (ms) |
| `restartOnCrash` | Auto-restart if server crashes |
| `maxRestarts` | Maximum restart attempts |

Users installing LSP plugins must have the language server binary installed
on their machine separately.

**Pre-built LSP plugins** from the official marketplace:

| Plugin | Language Server | Binary Required |
| ------ | -------------- | --------------- |
| `pyright-lsp` | Pyright (Python) | `pyright-langserver` |
| `typescript-lsp` | TypeScript Language Server | `typescript-language-server` |
| `rust-analyzer-lsp` | rust-analyzer | `rust-analyzer` |
| `gopls-lsp` | gopls (Go) | `gopls` |

### Plugin Settings (settings.json)

Plugins can include a `settings.json` file at the plugin root to apply
default configuration when enabled. Currently, only the `agent` key is
supported:

```json
{
  "agent": "security-reviewer"
}
```

This activates the named agent from the plugin's `agents/` directory as
the main thread, applying its system prompt, tool restrictions, and model.
Settings from `settings.json` take priority over settings declared in
`plugin.json`. Unknown keys are silently ignored.

### Output Styles in Plugins

Plugins can include an `outputStyles/` directory with markdown files that
customize how Claude responds. Reference them via the `outputStyles` field
in `plugin.json`.

## Environment Variables

### CLAUDE_PLUGIN_ROOT

The `${CLAUDE_PLUGIN_ROOT}` variable contains the absolute path to the
plugin's installation directory. Use it in hooks, MCP servers, and scripts
to ensure correct paths regardless of installation location:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
          }
        ]
      }
    ]
  }
}
```

This is essential because plugins are copied to a cache location when
installed from a marketplace (see Plugin Caching below).

## Plugin Installation Scopes

When installing a plugin, the scope determines where it is available:

| Scope | Settings File | Use Case |
| ----- | ------------- | -------- |
| `user` | `~/.claude/settings.json` | Personal plugins across all projects (default) |
| `project` | `.claude/settings.json` | Team plugins shared via version control |
| `local` | `.claude/settings.local.json` | Project-specific plugins, gitignored |
| `managed` | `managed-settings.json` | Enterprise-managed plugins (read-only) |

Install with a specific scope:

```bash
claude plugin install formatter@my-marketplace --scope project
```

## CLI Commands

Claude Code provides CLI commands for non-interactive plugin management:

### plugin install

```bash
claude plugin install <plugin> [--scope <user|project|local>]
```

Install a plugin from available marketplaces. Default scope is `user`.

### plugin uninstall

```bash
claude plugin uninstall <plugin> [--scope <user|project|local>]
```

Remove an installed plugin. Aliases: `remove`, `rm`.

### plugin enable

```bash
claude plugin enable <plugin> [--scope <user|project|local>]
```

Re-enable a disabled plugin.

### plugin disable

```bash
claude plugin disable <plugin> [--scope <user|project|local>]
```

Disable a plugin without uninstalling it.

### plugin update

```bash
claude plugin update <plugin> [--scope <user|project|local|managed>]
```

Update a plugin to the latest version.

### plugin validate

```bash
claude plugin validate .
```

Validate plugin or marketplace JSON syntax and structure. Also available
interactively as `/plugin validate`.

### Interactive Management

Within Claude Code, use `/plugin` to open the plugin manager with tabs:

- **Discover** -- browse available plugins from all marketplaces
- **Installed** -- view and manage installed plugins
- **Marketplaces** -- add, remove, or update marketplaces
- **Errors** -- view plugin loading errors

## Development and Testing

### Local Testing with --plugin-dir

Use the `--plugin-dir` flag to load plugins during development without
installing them:

```bash
claude --plugin-dir ./my-plugin
```

Load multiple plugins simultaneously:

```bash
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

Restart Claude Code to pick up changes during development.

### Debugging

Use `claude --debug` (or `/debug` in the TUI) to see:

- Which plugins are being loaded
- Errors in plugin manifests
- Command, agent, and hook registration
- MCP and LSP server initialization

### Common Development Issues

| Issue | Cause | Solution |
| ----- | ----- | -------- |
| Plugin not loading | Invalid `plugin.json` | Validate with `claude plugin validate` |
| Commands not appearing | Wrong directory structure | Ensure `commands/` at root, not in `.claude-plugin/` |
| Hooks not firing | Script not executable | Run `chmod +x script.sh` |
| MCP server fails | Missing `${CLAUDE_PLUGIN_ROOT}` | Use variable for all plugin paths |
| Path errors | Absolute paths used | All paths must be relative, starting with `./` |
| LSP binary not found | Server not installed | Install the language server binary |

## Plugin Caching and File Resolution

Marketplace plugins are copied to `~/.claude/plugins/cache` rather than
used in place. This has important implications:

### Path Traversal Limitations

Installed plugins cannot reference files outside their directory. Paths
like `../shared-utils` will not work after installation because external
files are not copied to the cache.

### Working with External Dependencies

Use symbolic links within your plugin directory to reference external files.
Symlinks are followed during the copy process:

```bash
# Inside your plugin directory
ln -s /path/to/shared-utils ./shared-utils
```

### Cache Management

If plugins are not appearing or behaving unexpectedly:

```bash
rm -rf ~/.claude/plugins/cache
```

Then restart Claude Code and reinstall plugins.

## Plugin Marketplaces

### marketplace.json Schema

Create `.claude-plugin/marketplace.json` in your repository root:

```json
{
  "name": "company-tools",
  "owner": {
    "name": "DevTools Team",
    "email": "devtools@example.com"
  },
  "metadata": {
    "description": "Internal development tools",
    "version": "1.0.0",
    "pluginRoot": "./plugins"
  },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting",
      "version": "2.1.0"
    }
  ]
}
```

**Required marketplace fields:**

| Field | Description |
| ----- | ----------- |
| `name` | Marketplace identifier (kebab-case). Users see it in install commands. |
| `owner` | Maintainer info. `name` is required, `email` is optional. |
| `plugins` | Array of plugin entries |

**Optional metadata:**

| Field | Description |
| ----- | ----------- |
| `metadata.description` | Brief marketplace description |
| `metadata.version` | Marketplace version |
| `metadata.pluginRoot` | Base directory prepended to relative source paths |

### Plugin Source Types

| Source | Type | Fields | Notes |
| ------ | ---- | ------ | ----- |
| Relative path | string | -- | Local directory within marketplace repo. Must start with `./` |
| GitHub | object | `repo`, `ref?`, `sha?` | `"source": "github"` |
| Git URL | object | `url` (must end `.git`), `ref?`, `sha?` | `"source": "url"` |
| NPM | object | `package`, `version?`, `registry?` | `"source": "npm"` |
| pip | object | `package`, `version?`, `registry?` | `"source": "pip"` |

Examples:

```json
{
  "name": "local-plugin",
  "source": "./plugins/my-plugin"
}
```

```json
{
  "name": "github-plugin",
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo",
    "ref": "v2.0.0"
  }
}
```

```json
{
  "name": "git-plugin",
  "source": {
    "source": "url",
    "url": "https://gitlab.com/team/plugin.git"
  }
}
```

### Adding Marketplaces

```bash
# GitHub repository
/plugin marketplace add owner/repo

# Git URL (GitLab, Bitbucket, self-hosted)
/plugin marketplace add https://gitlab.com/company/plugins.git

# Specific branch or tag
/plugin marketplace add https://gitlab.com/company/plugins.git#v1.0.0

# Local directory
/plugin marketplace add ./my-marketplace

# Remote URL
/plugin marketplace add https://example.com/marketplace.json
```

### Marketplace Management

```bash
/plugin marketplace list       # List all configured marketplaces
/plugin marketplace update X   # Refresh plugin listings
/plugin marketplace remove X   # Remove a marketplace (uninstalls its plugins)
```

### Team Marketplace Configuration

Configure automatic marketplace installation for projects via
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugins"
      }
    }
  },
  "enabledPlugins": {
    "code-formatter@company-tools": true
  }
}
```

### Managed Marketplace Restrictions

Administrators can restrict allowed marketplaces via `strictKnownMarketplaces`
in managed settings:

```json
{
  "strictKnownMarketplaces": [
    {
      "source": "github",
      "repo": "acme-corp/approved-plugins"
    },
    {
      "source": "hostPattern",
      "hostPattern": "^github\\.example\\.com$"
    }
  ]
}
```

An empty array `[]` locks down all marketplace additions. Omitting the
field allows unrestricted access.

### Marketplace Strict Mode

The `strict` field in plugin entries controls authority for component
definitions:

| Value | Behavior |
| ----- | -------- |
| `true` (default) | `plugin.json` is authoritative. Marketplace entry can supplement with additional components. |
| `false` | Marketplace entry is the entire definition. Plugin must not have its own component declarations in `plugin.json`. |

## aida-config.json Schema

AIDA-specific fields (`config` and `recommendedPermissions`) live in a
separate `aida-config.json` inside `.claude-plugin/`. This keeps the
standard `plugin.json` clean for the Claude Code plugin validator.

### Config Declaration

Plugins can declare user-configurable preferences:

```json
{
  "config": {
    "label": "My Plugin Settings",
    "description": "Configure preferences for My Plugin",
    "preferences": [
      {
        "key": "feature.enabled",
        "type": "boolean",
        "label": "Enable feature X",
        "default": true
      },
      {
        "key": "output.format",
        "type": "choice",
        "label": "Output format",
        "options": ["JSON", "YAML", "Text"],
        "default": "JSON"
      },
      {
        "key": "custom.path",
        "type": "string",
        "label": "Custom output path",
        "default": "./output"
      }
    ]
  }
}
```

**Supported preference types:**

- `boolean` -- on/off toggle
- `choice` -- select from a list (`options` array required)
- `string` -- free-text input

### Recommended Permissions Declaration

Plugins can declare permission recommendations:

```json
{
  "recommendedPermissions": {
    "git-operations": {
      "label": "Git Operations",
      "description": "Commit, push, branch, and other git commands",
      "rules": [
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(git push:*)"
      ],
      "suggested": "allow"
    }
  }
}
```

**Rule format:** `Tool(command:args)`. Use `*` for wildcard arguments.

## Versioning Strategy

Follow Semantic Versioning (SemVer):

### Major Version (X.0.0)

Breaking changes:

- Removing agents or skills
- Changing skill invocation argument formats
- Incompatible schema changes
- Renamed entry points

### Minor Version (0.X.0)

New features (backwards compatible):

- Adding new agents or skills
- New optional parameters
- Enhanced functionality
- New knowledge files

### Patch Version (0.0.X)

Bug fixes (backwards compatible):

- Fixing errors
- Documentation updates
- Performance improvements

### Version Resolution

Claude Code uses the version to determine whether to update a plugin. If
you change code but do not bump the version, existing users will not see
changes due to caching.

When version is set in both `plugin.json` and `marketplace.json`, the
`plugin.json` version takes priority silently.

## Dependencies

### Declaring Dependencies

```json
{
  "dependencies": {
    "base-plugin": "^1.0.0",
    "optional-plugin": "~2.3.0"
  }
}
```

### Version Operators

| Operator | Meaning | Example |
| -------- | ------- | ------- |
| `^` | Compatible | `^1.2.3` = `>=1.2.3 <2.0.0` |
| `~` | Patch updates | `~1.2.3` = `>=1.2.3 <1.3.0` |
| `>=` | Minimum | `>=1.0.0` |
| `=` | Exact | `=1.2.3` |

## Best Practices

### Naming Conventions

- Plugin names: `kebab-case`
- Be specific: `react-testing-tools` not `testing`
- Avoid generic terms: `awesome-plugin` is not useful
- Use scopes for organizations: `@myorg/plugin-name`

### Documentation

Include in README.md:

1. **What it does** -- Clear value proposition
2. **Installation** -- How to install
3. **Quick start** -- Basic usage example
4. **Components** -- List of agents, skills, hooks, MCP/LSP servers
5. **Configuration** -- Any setup required
6. **Examples** -- Common use cases

### Quality Checklist

Before publishing:

- [ ] All components have proper frontmatter
- [ ] README.md is comprehensive
- [ ] CHANGELOG.md documents changes
- [ ] No hardcoded paths (use `${CLAUDE_PLUGIN_ROOT}`)
- [ ] No secrets or credentials
- [ ] License file included (for public plugins)
- [ ] Version follows SemVer
- [ ] Tests pass (if applicable)
- [ ] Validated with `claude plugin validate .`

### Security Considerations

- Never include secrets or API keys
- Avoid shell commands that could be dangerous
- Document any external network calls
- Use parameter validation in scripts
- Prefer read operations over write operations
- Use `${CLAUDE_PLUGIN_ROOT}` for all file paths in hooks and MCP configs

## Plugin Organization Patterns

### Single-Purpose Plugin

```text
linting-plugin/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── lint/
        └── SKILL.md
```

### Toolkit Plugin

```text
testing-toolkit/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── test-advisor.md
└── skills/
    ├── test/
    │   └── SKILL.md
    ├── coverage/
    │   └── SKILL.md
    └── test-runner/
        └── SKILL.md
```

### Full-Featured Plugin

```text
enterprise-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── security-reviewer.md
│   └── compliance-checker.md
├── skills/
│   └── code-review/
│       └── SKILL.md
├── hooks/
│   └── hooks.json
├── settings.json
├── .mcp.json
├── .lsp.json
├── outputStyles/
│   └── detailed.md
├── scripts/
│   ├── security-scan.sh
│   └── format-code.py
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## Converting Standalone to Plugin

### Migration Steps

1. Create plugin directory with `.claude-plugin/plugin.json`
2. Copy `skills/`, `agents/`, `commands/` from `.claude/`
3. Move hooks from `settings.json` to `hooks/hooks.json` (same format)
4. Replace any absolute paths with `${CLAUDE_PLUGIN_ROOT}` references
5. Test with `claude --plugin-dir ./my-plugin`

### What Changes After Migration

| Standalone (`.claude/`) | Plugin |
| ----------------------- | ------ |
| Only available in one project | Can be shared via marketplaces |
| Files in `.claude/commands/` | Files in `plugin-name/commands/` |
| Hooks in `settings.json` | Hooks in `hooks/hooks.json` |
| Short skill names (`/review`) | Namespaced names (`/plugin:review`) |
| Must manually copy to share | Install with `claude plugin install` |

## Common Issues

### Path Resolution

**Problem:** Paths break when installed in different locations.

**Solution:** Use `${CLAUDE_PLUGIN_ROOT}` for all paths in hooks, MCP
servers, and scripts:

```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/process.sh"
}
```

For Python scripts, use relative path resolution:

```python
plugin_dir = Path(__file__).parent.parent.parent
template_path = plugin_dir / "templates" / "my-template.jinja2"
```

### Version Conflicts

**Problem:** Two plugins require incompatible versions of a dependency.

**Solution:**

1. Update to latest compatible versions
2. Contact plugin authors for updates
3. Fork and update dependency locally

### Missing Components

**Problem:** Skills or commands do not appear after installation.

**Solution:**

1. Ensure components are at plugin root, not inside `.claude-plugin/`
2. Validate with `claude plugin validate .`
3. Clear cache: `rm -rf ~/.claude/plugins/cache`
4. Restart Claude Code and reinstall
5. Test in clean environment with `--plugin-dir`
