# AIDA Core Plugin

Core functionality for the AIDA personal assistant system.

## What This Plugin Provides

### Commands
- `/init-aida` - Initialize your AIDA system
- `/remember` - Remember facts and decisions
- `/recall` - Search your memory
- `/start-day` - Morning routine
- `/end-day` - Evening routine

### Skills
- **memory-management** - Automatically manages your personal memory system

### Agents
- **assistant-core** - Core coordinator agent

## Installation
```bash
/plugin marketplace add oakensoul/aida-marketplace
/plugin install core@aida
```

## First Time Setup

After installation:
```bash
/init-aida
```

This creates your personal AIDA directory structure:
```
~/.claude/
├── memory/          # Your memory system
├── knowledge/       # Your knowledge base
└── config/          # Your settings
```

## Daily Usage

### Morning
```bash
/start-day
```

### During the Day
```bash
/remember chose React over Vue for better TypeScript support
/recall what did I decide about frameworks
```

### Evening
```bash
/end-day
```

## File Structure

AIDA creates and manages files in `~/.claude/`:
```
~/.claude/
├── memory/
│   ├── context.md          # Current state
│   ├── decisions.md        # Decision log
│   └── history/
│       └── 2025-10.md      # Monthly archives
├── knowledge/
│   ├── system.md           # How your system is organized
│   ├── projects.md         # Active project tracking
│   ├── preferences.md      # Your preferences
│   ├── procedures.md       # How to do things
│   └── workflows.md        # When to do things
└── config/
    └── settings.yaml       # Configuration
```

## Integration with Other Plugins

This core plugin works with:
- **Personality plugins** - Add personality to the assistant
- **Workflow plugins** - Add specialized workflows
- **Integration plugins** - Connect to other tools

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License
