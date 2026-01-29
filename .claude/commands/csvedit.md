---
name: csvedit
description: Edit a CSV file with automatic validation
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
---

# CSV Edit Command

Edit the specified CSV file: $ARGUMENTS

## Workflow
1. Read the target CSV file
2. Perform the requested modification
3. Validate the result (automatic via hook)
4. Report the changes made

## Error Handling
If a CSV validation error occurs:
1. Analyze the error message
2. Fix the malformed CSV
3. The validator will re-run automatically
4. Continue only when validation passes

## Output Format
After completion, report:
- Original structure (rows, columns)
- Changes made
- Final structure
- Validation status

## Usage Examples
```
/csvedit test-data/sample.csv - add a row for "Alice Brown", 200.00, 2024-01-18
/csvedit test-data/broken.csv - report structure
/csvedit data.csv - remove the last row
/csvedit users.csv - add column "status" with default value "active"
```

## Self-Correction Loop
This command creates a closed-loop system:
- Every file operation triggers automatic validation
- Errors are fed back for immediate correction
- Final validation runs when the command completes
- No manual intervention needed for recoverable errors
