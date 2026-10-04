"""Executor for PussyCat custom language.

Runs generated Python code and captures output.
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """Result of execution operation."""
    stdout: str
    stderr: str
    error: Optional[str]
    timed_out: bool
    returncode: int


def _remap_lines(stderr: str, line_map: dict[int, int]) -> str:
    """Replace Python line numbers in a traceback with PussyCat source lines."""
    def repl(m: re.Match) -> str:
        py_line = int(m.group(1))
        return f"line {line_map.get(py_line, py_line)} (PussyCat source)"
    return re.sub(r"line (\d+)", repl, stderr)


def execute(python_code: str, line_map: dict[int, int]) -> ExecutionResult:
    """Execute Python code and capture output."""
    tmp_path = None
    try:
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(python_code)
                tmp_path = tmp.name
        except OSError as e:
            return ExecutionResult("", "", f"[Executor Error] Could not write temp file: {e}", False, 1)

        # Try python3 first, fall back to python (Windows)
        result = None
        for interpreter in ("python3", "python"):
            try:
                result = subprocess.run(
                    [interpreter, tmp_path],
                    capture_output=True, text=True, timeout=10,
                )
                break
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    "", "", "[Timeout] Execution exceeded 10 seconds.", True, -1
                )

        if result is None:
            return ExecutionResult(
                "", "",
                "[Executor Error] Python interpreter not found. Ensure Python 3.10+ is installed.",
                False, 1,
            )

        if result.returncode == 0:
            return ExecutionResult(result.stdout, "", None, False, 0)

        return ExecutionResult(
            stdout=result.stdout,
            stderr=result.stderr,
            error=_remap_lines(result.stderr, line_map),
            timed_out=False,
            returncode=result.returncode,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)