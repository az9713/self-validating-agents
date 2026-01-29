# Self-Validating Agents: A Claude Code Pattern

This project demonstrates a powerful pattern for building **self-validating AI agents** using Claude Code's hook system. The pattern creates a closed feedback loop where every file operation is automatically validated, and errors are fed back to the agent for immediate correction.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER REQUEST                                │
│            "Add a row to sample.csv"                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENTRY POINTS                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   /csvedit   │  │  csv-editor  │  │csv-edit-agent│          │
│  │   Command    │  │    Skill     │  │    Agent     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                   │
│                           │                                     │
│              All define the same hook:                          │
│              PostToolUse → csv-single-validator.py              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION                               │
│                                                                 │
│   Claude uses Read/Edit/Write tools on CSV files                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HOOK TRIGGER                                 │
│                                                                 │
│   PostToolUse hook fires after Read|Edit|Write                  │
│   Matcher: "Read|Edit|Write"                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                CSV VALIDATOR (Python)                           │
│                                                                 │
│   1. Receives tool_input via stdin (JSON)                       │
│   2. Extracts file_path                                         │
│   3. Skips non-CSV files (exit 0)                               │
│   4. Validates with pandas.read_csv()                           │
│   5. Logs to ~/.claude/logs/csv-validator.log                   │
│                                                                 │
│   Exit Codes:                                                   │
│   - 0: Success (validation passed or non-CSV file)              │
│   - 2: Error (feeds stderr back to Claude)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌───────────────┐   ┌───────────────┐
            │  EXIT 0       │   │  EXIT 2       │
            │  (Success)    │   │  (Error)      │
            │               │   │               │
            │  Continue     │   │  Error msg    │
            │  normally     │   │  fed back to  │
            │               │   │  Claude       │
            └───────────────┘   └───────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │  SELF-CORRECTION  │
                              │                   │
                              │  Claude reads the │
                              │  error, fixes the │
                              │  CSV, and retries │
                              │                   │
                              │  Loop continues   │
                              │  until valid      │
                              └───────────────────┘
```

## Component Details

### 1. Command: `/csvedit` (`.claude/commands/csvedit.md`)

The command is a user-invocable entry point. When a user types `/csvedit sample.csv - add a row`, this file defines:

- **What the command does**: Edit CSV files with automatic validation
- **The hook configuration**: PostToolUse and Stop hooks
- **Instructions for Claude**: Workflow, error handling, output format

```yaml
hooks:
  PostToolUse:
    - matcher: "Read|Edit|Write"
      hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-single-validator.py\""
  Stop:
    - hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-single-validator.py\""
```

The **Stop hook** provides a final validation when the command completes, ensuring no errors slip through.

### 2. Skill: `csv-editor` (`.claude/skills/csv-editor.md`)

Skills are automatically invoked when Claude determines they're relevant. The skill:

- Provides Claude with specialized knowledge about CSV editing
- Defines the same validation hook
- Includes guidelines for self-validation behavior

```yaml
hooks:
  PostToolUse:
    - matcher: "Read|Edit|Write"
      hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-single-validator.py\""
```

### 3. Agent: `csv-edit-agent` (`.claude/agents/csv-edit-agent.md`)

Agents are specialized subprocesses that handle specific tasks. The agent:

- Runs with restricted tools (Glob, Grep, Read, Edit, Write)
- Uses the Opus model for complex reasoning
- Has the same validation hook attached

```yaml
tools: Glob, Grep, Read, Edit, Write
model: opus
hooks:
  PostToolUse:
    - matcher: "Read|Edit|Write"
      hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-single-validator.py\""
```

### 4. Hook: `csv-single-validator.py` (`.claude/hooks/validators/`)

The validator is a Python script that:

1. **Receives input via stdin**: Claude Code passes a JSON object containing `tool_input` with the `file_path`
2. **Filters by file type**: Only validates `.csv` files, silently passes others
3. **Uses pandas for validation**: Catches parsing errors, empty files, malformed rows
4. **Logs all validations**: Writes to `~/.claude/logs/csv-validator.log` for observability
5. **Returns appropriate exit codes**:
   - `0`: Success - continue normally
   - `2`: Error - message is fed back to Claude for correction

```python
def validate_csv(file_path: str) -> tuple[bool, str]:
    try:
        df = pd.read_csv(file_path)
        return True, f"Valid CSV: {len(df)} rows, {len(df.columns)} columns"
    except pd.errors.ParserError as e:
        return False, f"CSV parse error: {e}"
```

## Example Walkthrough: test-data/sample.csv

### The Test File

```csv
id,name,amount,date
1,"John Doe",150.00,2024-01-15
2,"Jane Smith",275.50,2024-01-16
3,"Bob Wilson",100.00,2024-01-17
```

### Scenario: Adding a Malformed Row

**User Request**: `/csvedit test-data/sample.csv - add a row for Alice`

**What Happens**:

1. User invokes the command
2. Claude reads sample.csv using the Read tool
3. **PostToolUse hook fires** → Validator checks the file → Exit 0 (valid)
4. Claude edits the file to add a new row, but makes a mistake:
   ```csv
   4,"Alice Brown",200.00  # Missing date column!
   ```
5. **PostToolUse hook fires** → Validator runs pandas.read_csv()
6. Pandas detects inconsistent column count → Validator exits with code 2
7. Error message fed back to Claude:
   ```
   Resolve this CSV error in test-data/sample.csv:
   CSV parse error: Expected 4 fields in line 5, saw 3
   ```
8. Claude reads the error, understands the issue, and fixes the row:
   ```csv
   4,"Alice Brown",200.00,2024-01-18
   ```
9. **PostToolUse hook fires** → Validator passes → Exit 0
10. **Stop hook fires** → Final validation → Exit 0
11. Claude reports success to user

### The Self-Correction Loop

```
┌──────────────────┐
│   Claude Edit    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│    Validator     │────▶│   Exit 0?        │
└──────────────────┘     └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │ YES                       │ NO
                    ▼                           ▼
            ┌───────────────┐         ┌───────────────┐
            │   Continue    │         │  Feed error   │
            │   to next     │         │  back to      │
            │   operation   │         │  Claude       │
            └───────────────┘         └───────┬───────┘
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │ Claude fixes  │
                                      │ the issue     │
                                      └───────┬───────┘
                                              │
                                              └──────────▶ (retry)
```

## Why This Pattern Matters

### 1. **Automatic Quality Assurance**
Every file operation is validated without manual intervention. Claude cannot produce invalid output because errors are caught and corrected automatically.

### 2. **Domain-Specific Validation**
The hook uses pandas, a domain expert for CSV files. You can swap in any validator: JSON Schema, XML DTD, SQL syntax checker, etc.

### 3. **Closed Feedback Loop**
Errors don't just stop execution—they're fed back to Claude with actionable context. The agent learns what went wrong and fixes it.

### 4. **Multiple Entry Points, Single Validator**
Whether users invoke via command, skill, or agent, the same validation logic applies. This ensures consistency.

### 5. **Observability**
All validations are logged to `~/.claude/logs/csv-validator.log`, providing an audit trail for debugging and monitoring.

### 6. **Graceful Degradation**
Non-CSV files pass through silently (exit 0). The hook doesn't interfere with unrelated operations.

## Extending This Pattern

### Other Use Cases

- **JSON Validator**: Validate JSON against schemas after every edit
- **SQL Syntax Checker**: Verify SQL files are syntactically correct
- **YAML Linter**: Ensure YAML files are properly formatted
- **Code Formatter**: Run prettier/black after code edits
- **Test Runner**: Run relevant tests after code changes
- **Security Scanner**: Check for secrets or vulnerabilities

### Hook Configuration Reference

```yaml
hooks:
  PostToolUse:          # Fires after tool execution
    - matcher: "Read|Edit|Write"  # Regex matching tool names
      hooks:
        - type: command
          command: "your-validator-script"
  Stop:                 # Fires when command/agent completes
    - hooks:
        - type: command
          command: "final-validation-script"
```

### Exit Code Semantics

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | Continue normally |
| 1 | Fatal error | Stop execution |
| 2 | Correctable error | Feed stderr to Claude for correction |

## Environment Setup

The hook uses `$CLAUDE_PROJECT_DIR` environment variable. Set it to your project root:

**Linux/macOS (bash/zsh)**:
```bash
export CLAUDE_PROJECT_DIR="/path/to/project"
```

**Windows (PowerShell)**:
```powershell
$env:CLAUDE_PROJECT_DIR = "C:\path\to\project"
```

**Windows (System Environment Variable)**:
1. Open System Properties → Environment Variables
2. Add: `CLAUDE_PROJECT_DIR` = `C:\path\to\project`

## Conclusion

Self-validating agents represent a paradigm shift in AI-assisted development. Instead of hoping Claude produces valid output, we **guarantee** it through automatic validation and feedback loops. This pattern:

- Eliminates classes of errors entirely
- Reduces human oversight requirements
- Creates predictable, reliable agent behavior
- Enables domain-specific quality enforcement

The CSV example demonstrates the concept, but the pattern applies to any domain where validation can be automated.
