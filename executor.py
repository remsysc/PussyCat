"""Executor for PussyCat custom language.

Runs generated Python code in a subprocess and captures output.
Remaps Python traceback line numbers back to PussyCat source lines
using the line_map produced by the transpiler.
"""

import subprocess
import sys
import tempfile
import os
import re
from dataclasses import dataclass
from typing import Optional

# Maximum wall-clock seconds a script is allowed to run before it is killed.
EXECUTION_TIMEOUT = 10


@dataclass
class ExecutionResult:
    """Result of execution operation."""
    stdout: str
    stderr: str
    error: Optional[str]
    timed_out: bool
    returncode: int


def _remap_traceback(stderr: str, line_map: dict[int, int]) -> str:
    """Rewrite Python line numbers in a traceback to PussyCat source lines.

    Looks for 'File "<string>", line N' patterns produced when running code
    from a temp file or exec() and replaces N with the mapped PussyCat line.
    Falls back to the original number if it isn't in line_map.
    """
    def _replace(match: re.Match) -> str:
        py_line = int(match.group(1))
        cat_line = line_map.get(py_line, py_line)
        return f'line {cat_line}'

    return re.sub(r'\bline (\d+)', _replace, stderr)


def execute(python_code: str, line_map: dict[int, int]) -> ExecutionResult:
    """Execute Python code in a subprocess and return captured output.

    Steps:
      1. Write python_code to a temporary .py file.
      2. Run it with the same Python interpreter that launched PussyCat.
      3. Capture stdout and stderr with a timeout.
      4. Remap any traceback line numbers via line_map.
      5. Clean up the temp file.

    Never raises; all error conditions are returned inside ExecutionResult.
    """
    # ── Guard: nothing to run ─────────────────────────────────────────────────
    if not python_code or not python_code.strip():
        return ExecutionResult(
            stdout="", stderr="", error=None, timed_out=False, returncode=0
        )

    tmp_path: Optional[str] = None
    try:
        # ── Write temp file ───────────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(python_code)
            tmp_path = tmp.name

        # ── Run subprocess ────────────────────────────────────────────────────
        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
            )
            timed_out = False
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                stdout="",
                stderr="",
                error=f"[Executor Error] Script timed out after {EXECUTION_TIMEOUT}s",
                timed_out=True,
                returncode=-1,
            )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        # ── Remap traceback lines ─────────────────────────────────────────────
        # Replace the temp-file path with a friendlier label before remapping
        stderr_clean = stderr.replace(tmp_path, "<pussycat>")
        if stderr_clean:
            stderr_clean = _remap_traceback(stderr_clean, line_map)

        # ── Build error string from stderr ────────────────────────────────────
        error: Optional[str] = None
        if proc.returncode != 0 and stderr_clean:
            # Extract the last meaningful error line (skip the full traceback
            # header and blank lines so the status bar stays readable)
            lines = [l for l in stderr_clean.splitlines() if l.strip()]
            error = "\n".join(lines)  # keep full remapped traceback for output pane

        return ExecutionResult(
            stdout=stdout.rstrip("\n"),
            stderr=stderr_clean,
            error=error,
            timed_out=False,
            returncode=proc.returncode,
        )

    except Exception as exc:  # pragma: no cover – unexpected OS-level failure
        return ExecutionResult(
            stdout="",
            stderr="",
            error=f"[Executor Error] Unexpected failure: {exc}",
            timed_out=False,
            returncode=-1,
        )
    finally:
        # ── Clean up temp file ────────────────────────────────────────────────
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
