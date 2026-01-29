# CSV Edit Agent: Self-Validating Agent Documentation

## Overview

The **csv-edit-agent** is a specialized Claude Code subagent that automatically validates CSV files after every file operation. It uses PostToolUse hooks to intercept Read, Edit, and Write operations, running a Python validator that detects and reports CSV errors in real-time.

This pattern enables **self-healing behavior**: when the agent writes broken CSV, the hook detects the error and feeds it back to Claude, which then automatically attempts to fix the issue.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CSV EDIT AGENT SYSTEM                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌──────────────────┐         ┌───────────────────┐
│                 │         │                  │         │                   │
│   User Prompt   │────────▶│  csv-edit-agent  │────────▶│   Tool Execution  │
│                 │         │   (Claude LLM)   │         │  Read/Edit/Write  │
│                 │         │                  │         │                   │
└─────────────────┘         └────────┬─────────┘         └─────────┬─────────┘
                                     │                             │
                                     │                             │
                                     ▼                             ▼
                            ┌────────────────┐            ┌────────────────────┐
                            │                │            │                    │
                            │  Agent Output  │◀───────────│  PostToolUse Hook  │
                            │   (Response)   │            │     Triggered      │
                            │                │            │                    │
                            └────────────────┘            └─────────┬──────────┘
                                     ▲                              │
                                     │                              ▼
                                     │                    ┌────────────────────┐
                                     │                    │                    │
                                     │                    │   uv run           │
                                     │                    │   csv-single-      │
                                     │                    │   validator.py     │
                                     │                    │                    │
                                     │                    └─────────┬──────────┘
                                     │                              │
                                     │                              ▼
                                     │                    ┌────────────────────┐
                                     │                    │  Validate CSV      │
                                     │                    │  with pandas       │
                                     │                    │                    │
                                     │                    │  ┌──────────────┐  │
                                     │                    │  │ pd.read_csv()│  │
                                     │                    │  └──────────────┘  │
                                     │                    └─────────┬──────────┘
                                     │                              │
                                     │              ┌───────────────┴───────────────┐
                                     │              │                               │
                                     │              ▼                               ▼
                                     │    ┌─────────────────┐             ┌─────────────────┐
                                     │    │   EXIT CODE 0   │             │   EXIT CODE 2   │
                                     │    │                 │             │                 │
                                     │    │  Valid CSV      │             │  Invalid CSV    │
                                     │    │  Continue...    │             │  Error → stderr │
                                     │    │                 │             │                 │
                                     │    └────────┬────────┘             └────────┬────────┘
                                     │             │                               │
                                     │             ▼                               ▼
                                     │    ┌─────────────────┐             ┌─────────────────┐
                                     │    │                 │             │                 │
                                     └────│  Agent proceeds │             │  Error fed back │
                                          │  normally       │             │  to Claude LLM  │
                                          │                 │             │                 │
                                          └─────────────────┘             └────────┬────────┘
                                                                                   │
                                                                                   ▼
                                                                          ┌─────────────────┐
                                                                          │                 │
                                                                          │  Claude auto-   │
                                                                          │  fixes the CSV  │
                                                                          │  (retry loop)   │
                                                                          │                 │
                                                                          └─────────────────┘
```

---

## Communication Flow: Broken CSV Example

This diagram shows exactly what happens when the agent reads `test-data/broken.csv`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP-BY-STEP FLOW: Reading test-data/broken.csv                            │
└─────────────────────────────────────────────────────────────────────────────┘

  USER                      AGENT                     HOOK                   FILE
   │                          │                         │                      │
   │  "Report on broken.csv"  │                         │                      │
   │─────────────────────────▶│                         │                      │
   │                          │                         │                      │
   │                          │  Read(broken.csv)       │                      │
   │                          │────────────────────────────────────────────────▶│
   │                          │                         │                      │
   │                          │◀───────────────────────────────────────────────│
   │                          │  File contents returned │                      │
   │                          │                         │                      │
   │                          │  ┌──────────────────────────────────────────┐  │
   │                          │  │ PostToolUse Hook Triggered               │  │
   │                          │  │ matcher: "Read|Edit|Write" ✓ MATCH       │  │
   │                          │  └──────────────────────────────────────────┘  │
   │                          │                         │                      │
   │                          │  Hook receives JSON:    │                      │
   │                          │─────────────────────────▶                      │
   │                          │  {                      │                      │
   │                          │    "tool_name": "Read", │                      │
   │                          │    "tool_input": {      │                      │
   │                          │      "file_path":       │                      │
   │                          │      "broken.csv"       │                      │
   │                          │    },                   │                      │
   │                          │    "tool_response": {}  │                      │
   │                          │  }                      │                      │
   │                          │                         │                      │
   │                          │                         │  pandas.read_csv()   │
   │                          │                         │─────────────────────▶│
   │                          │                         │                      │
   │                          │                         │◀─────────────────────│
   │                          │                         │  ParserError!        │
   │                          │                         │                      │
   │                          │  stderr + exit(2)       │                      │
   │                          │◀─────────────────────────                      │
   │                          │                         │                      │
   │                          │  ┌──────────────────────────────────────────┐  │
   │                          │  │ ERROR MESSAGE INJECTED INTO CONTEXT:     │  │
   │                          │  │                                          │  │
   │                          │  │ "Resolve this CSV error in broken.csv:   │  │
   │                          │  │  CSV parse error: Expected 4 fields in   │  │
   │                          │  │  line 4, saw 6"                          │  │
   │                          │  └──────────────────────────────────────────┘  │
   │                          │                         │                      │
   │                          │  Agent sees error,      │                      │
   │                          │  decides to fix CSV     │                      │
   │                          │                         │                      │
   │                          │  Edit(broken.csv,       │                      │
   │                          │       fix line 4)       │                      │
   │                          │────────────────────────────────────────────────▶│
   │                          │                         │                      │
   │                          │  ┌──────────────────────────────────────────┐  │
   │                          │  │ PostToolUse Hook Triggered Again         │  │
   │                          │  │ Validates the edited file                │  │
   │                          │  └──────────────────────────────────────────┘  │
   │                          │                         │                      │
   │                          │                         │  pandas.read_csv()   │
   │                          │                         │─────────────────────▶│
   │                          │                         │                      │
   │                          │                         │◀─────────────────────│
   │                          │                         │  SUCCESS ✓           │
   │                          │                         │                      │
   │                          │  exit(0) - continue     │                      │
   │                          │◀─────────────────────────                      │
   │                          │                         │                      │
   │  "Fixed CSV: 3 rows,     │                         │                      │
   │   4 columns"             │                         │                      │
   │◀─────────────────────────│                         │                      │
   │                          │                         │                      │
```

---

## Component Details

### 1. Agent Definition (`.claude/agents/csv-edit-agent.md`)

```yaml
---
name: csv-edit-agent
description: Make modifications or report on CSV files
tools: Glob, Grep, Read, Edit, Write
model: opus
hooks:
  PostToolUse:
    - matcher: "Read|Edit|Write"
      hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-single-validator.py\""
color: cyan
---
```

**Key Configuration:**

| Field | Value | Purpose |
|-------|-------|---------|
| `tools` | Glob, Grep, Read, Edit, Write | Restricts agent to file operations |
| `model` | opus | Uses Claude Opus for high-quality reasoning |
| `hooks.PostToolUse` | Validation trigger | Runs after every tool execution |
| `matcher` | `"Read\|Edit\|Write"` | Regex matching file operation tools |
| `command` | `uv run ...` | Executes validator with auto-dependency management |

### 2. Validator Script (`.claude/hooks/validators/csv-single-validator.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CSV VALIDATOR INTERNALS                      │
└─────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │   JSON stdin    │
                         │   from hook     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Extract         │
                         │ file_path from  │
                         │ tool_input      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Is it a .csv    │
                         │ file?           │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │ NO                        │ YES
                    ▼                           ▼
           ┌─────────────────┐         ┌─────────────────┐
           │   exit(0)       │         │ pandas.read_csv │
           │   Skip silently │         │                 │
           └─────────────────┘         └────────┬────────┘
                                                │
                                  ┌─────────────┴─────────────┐
                                  │ SUCCESS                   │ FAILURE
                                  ▼                           ▼
                         ┌─────────────────┐         ┌─────────────────┐
                         │ Log to file     │         │ Log to file     │
                         │ [PASS]          │         │ [FAIL]          │
                         └────────┬────────┘         └────────┬────────┘
                                  │                           │
                                  ▼                           ▼
                         ┌─────────────────┐         ┌─────────────────┐
                         │ stdout:         │         │ stderr:         │
                         │ "Valid CSV:     │         │ "Resolve this   │
                         │  3 rows, 4 cols"│         │  CSV error..."  │
                         │                 │         │                 │
                         │ exit(0)         │         │ exit(2)         │
                         └─────────────────┘         └─────────────────┘
```

**Exit Codes:**

| Code | Meaning | Behavior |
|------|---------|----------|
| `0` | Success / Skip | Agent continues normally |
| `1` | Hook error | Hook failed (not CSV error) |
| `2` | Validation error | stderr fed back to Claude for correction |

### 3. The Broken CSV File

**File: `test-data/broken.csv`**
```csv
id,name,amount,date
1,"John Doe",150.00,2024-01-15
2,"Jane Smith",275.50
3,"Bob Wilson",100.00,2024-01-17,extra_field,another_extra
```

**Problems:**
```
Line 1: id,name,amount,date              ← Header defines 4 columns
Line 2: 1,"John Doe",150.00,2024-01-15   ← ✓ 4 fields (valid)
Line 3: 2,"Jane Smith",275.50            ← ✗ 3 fields (missing date)
Line 4: 3,"Bob Wilson",...,extra,extra   ← ✗ 6 fields (2 extra)
```

---

## Hook Data Flow

When Claude executes `Read("test-data/broken.csv")`, the hook receives:

```json
{
  "tool_name": "Read",
  "tool_input": {
    "file_path": "C:\\Users\\simon\\Downloads\\self_validating_agents_dan\\test-data\\broken.csv"
  },
  "tool_response": {
    "content": "id,name,amount,date\n1,\"John Doe\",150.00,2024-01-15\n..."
  }
}
```

The validator:
1. Extracts `file_path` from `tool_input`
2. Checks extension is `.csv`
3. Runs `pandas.read_csv(file_path)`
4. Catches `ParserError`: "Expected 4 fields in line 4, saw 6"
5. Writes to `~/.claude/logs/csv-validator.log`
6. Outputs to stderr and exits with code 2

**Stderr output (fed back to Claude):**
```
Resolve this CSV error in test-data/broken.csv:
CSV parse error: Error tokenizing data. C error: Expected 4 fields in line 4, saw 6
```

---

## Self-Healing Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SELF-HEALING VALIDATION LOOP                        │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │ Agent performs   │
     │ file operation   │
     └────────┬─────────┘
              │
              ▼
     ┌──────────────────┐
     │ PostToolUse      │
     │ hook triggers    │
     └────────┬─────────┘
              │
              ▼
     ┌──────────────────┐         ┌──────────────────┐
     │ Validator runs   │────────▶│ CSV Valid?       │
     └──────────────────┘         └────────┬─────────┘
                                           │
                          ┌────────────────┴────────────────┐
                          │ YES                             │ NO
                          ▼                                 ▼
                 ┌──────────────────┐              ┌──────────────────┐
                 │ exit(0)          │              │ exit(2)          │
                 │ Agent continues  │              │ Error → Claude   │
                 └──────────────────┘              └────────┬─────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │ Claude receives: │
                                                  │ "Resolve this    │
                                                  │  CSV error..."   │
                                                  └────────┬─────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │ Claude edits     │
                                                  │ file to fix      │
                                                  └────────┬─────────┘
                                                           │
                                                           │ (loops back)
                                                           ▼
                                                  ┌──────────────────┐
                                                  │ PostToolUse      │
                                                  │ triggers again   │──────┐
                                                  └──────────────────┘      │
                                                                            │
                                           ┌────────────────────────────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ Re-validate...   │
                                  │ (repeat until    │
                                  │  valid or stuck) │
                                  └──────────────────┘
```

---

## Log Output

All validations are logged to `~/.claude/logs/csv-validator.log`:

```
[2026-01-28T20:28:30.850202] [PASS] .../sample.csv: Valid CSV: 3 rows, 4 columns
[2026-01-28T20:28:32.676313] [FAIL] .../broken.csv: CSV parse error: Expected 4 fields in line 4, saw 6
[2026-01-28T20:29:15.123456] [PASS] .../broken.csv: Valid CSV: 3 rows, 4 columns  ← After fix
```

---

## Key Design Principles

1. **Non-blocking for non-CSV files**: Validator exits 0 immediately for non-.csv files
2. **Actionable error messages**: "Resolve this CSV error in [path]" tells Claude exactly what to do
3. **Observability**: All validations logged with timestamps and status
4. **Dependency isolation**: `uv run` with script headers auto-installs pandas
5. **Idempotent validation**: Same file always produces same validation result

---

## File Structure

```
.claude/
├── agents/
│   └── csv-edit-agent.md        # Subagent definition with hooks
└── hooks/
    └── validators/
        └── csv-single-validator.py   # Python validator (uv script)

test-data/
├── sample.csv                   # Valid test file
└── broken.csv                   # Intentionally broken test file

~/.claude/logs/
└── csv-validator.log            # Validation audit log
```
