#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
CSV Single Validator - PostToolUse hook for csv-edit-agent
Validates CSV files after Read/Edit/Write operations.
Exit 0 = success, Exit 2 = error (fed back to Claude)
"""
import json
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

def validate_csv(file_path: str) -> tuple[bool, str]:
    """Validate CSV file using pandas. Returns (success, message)."""
    try:
        df = pd.read_csv(file_path)
        return True, f"Valid CSV: {len(df)} rows, {len(df.columns)} columns"
    except pd.errors.EmptyDataError:
        return False, "CSV file is empty"
    except pd.errors.ParserError as e:
        return False, f"CSV parse error: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"

def main():
    # Read hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)
        sys.exit(1)

    # Extract file path from tool_input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Skip non-CSV files silently
    if not file_path or not file_path.lower().endswith(".csv"):
        sys.exit(0)

    # Check file exists
    if not Path(file_path).exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Validate the CSV
    success, message = validate_csv(file_path)

    # Log results for observability
    log_path = Path.home() / ".claude" / "logs" / "csv-validator.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        status = "PASS" if success else "FAIL"
        f.write(f"[{datetime.now().isoformat()}] [{status}] {file_path}: {message}\n")

    if success:
        print(message)  # Shown in verbose mode
        sys.exit(0)
    else:
        # Exit code 2 feeds stderr back to Claude with action instruction
        print(f"Resolve this CSV error in {file_path}:\n{message}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
