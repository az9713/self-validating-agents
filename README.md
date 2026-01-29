# Self-Validating Agents

A Claude Code pattern demonstrating **self-validating AI agents** using hooks for automatic validation and error correction.

## What is This?

This project shows how to build AI agents that automatically validate their own output and self-correct when errors occur. Using Claude Code's hook system, every file operation triggers a validator that:

1. Checks the output for errors
2. Feeds errors back to Claude with actionable context
3. Allows Claude to fix the issue and retry
4. Loops until validation passes

## Architecture

```
User Request → Claude Edits File → Hook Validates → Error? → Feed Back → Self-Correct → Retry
                                                      ↓
                                                   Success → Continue
```

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| Command | `.claude/commands/csvedit.md` | User-invocable `/csvedit` command |
| Skill | `.claude/skills/csv-editor.md` | Auto-invoked CSV editing capability |
| Agent | `.claude/agents/csv-edit-agent.md` | Specialized subprocess for CSV tasks |
| Validator | `.claude/hooks/validators/csv-single-validator.py` | Pandas-based CSV validation |

## Quick Start

1. Set the environment variable:
   ```bash
   export CLAUDE_PROJECT_DIR="/path/to/this/project"
   ```

2. Use the command:
   ```
   /csvedit test-data/sample.csv - add a row for "Alice Brown", 200.00, 2024-01-18
   ```

3. Watch Claude automatically validate and self-correct any errors.

## Documentation

See [docs/SELF_VALIDATING_AGENTS.md](docs/SELF_VALIDATING_AGENTS.md) for detailed documentation including:

- Architecture diagrams
- Component details
- Example walkthrough with test data
- Extension patterns for other domains

## Test Data

- `test-data/sample.csv` - Valid CSV with 3 rows
- `test-data/broken.csv` - Intentionally malformed CSV for testing error correction

## License

MIT
