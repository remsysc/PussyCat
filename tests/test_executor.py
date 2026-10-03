"""Unit tests for executor.execute().

Covers Sprint-2 task #25: success, error, timeout, and edge cases.

Run with:  python tests/test_executor.py
       or: python -m unittest discover tests
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from executor import execute, ExecutionResult, EXECUTION_TIMEOUT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(code: str, line_map: dict = None) -> ExecutionResult:
    return execute(code, line_map or {})


# ---------------------------------------------------------------------------
# #23 — Temp file + subprocess.run + capture output
# ---------------------------------------------------------------------------

class TestSuccessCases(unittest.TestCase):

    def test_simple_print_captured(self):
        r = run("print('meow')")
        self.assertEqual(r.stdout, "meow")
        self.assertIsNone(r.error)
        self.assertEqual(r.returncode, 0)

    def test_multiple_prints_captured(self):
        r = run("print('a')\nprint('b')\nprint('c')")
        self.assertIn("a", r.stdout)
        self.assertIn("b", r.stdout)
        self.assertIn("c", r.stdout)

    def test_arithmetic_output(self):
        r = run("print(1 + 1)")
        self.assertIn("2", r.stdout)

    def test_variable_assignment_and_print(self):
        r = run("x = 42\nprint(x)")
        self.assertIn("42", r.stdout)

    def test_multiline_output(self):
        r = run("for i in range(3):\n    print(i)")
        self.assertIn("0", r.stdout)
        self.assertIn("1", r.stdout)
        self.assertIn("2", r.stdout)

    def test_no_stdout_returns_empty_string(self):
        r = run("x = 1 + 1")
        self.assertEqual(r.stdout, "")
        self.assertIsNone(r.error)

    def test_return_code_zero_on_success(self):
        self.assertEqual(run("x = 1").returncode, 0)

    def test_timed_out_false_on_success(self):
        self.assertFalse(run("print('ok')").timed_out)

    def test_string_output(self):
        r = run("print('PussyCat IDE')")
        self.assertIn("PussyCat IDE", r.stdout)

    def test_stdout_trailing_newline_stripped(self):
        # stdout is rstrip("\n") — no trailing newline
        r = run("print('hi')")
        self.assertFalse(r.stdout.endswith("\n"))


# ---------------------------------------------------------------------------
# #23 — Error / non-zero returncode cases
# ---------------------------------------------------------------------------

class TestErrorCases(unittest.TestCase):

    def test_syntax_error_captured(self):
        r = run("if True")   # missing colon — SyntaxError
        self.assertIsNotNone(r.error)
        self.assertNotEqual(r.returncode, 0)

    def test_name_error_captured(self):
        r = run("print(undefined_var)")
        self.assertIsNotNone(r.error)
        self.assertNotEqual(r.returncode, 0)

    def test_zero_division_captured(self):
        r = run("x = 1 / 0")
        self.assertIsNotNone(r.error)
        self.assertNotEqual(r.returncode, 0)

    def test_type_error_captured(self):
        r = run("x = 'cat' + 1")
        self.assertIsNotNone(r.error)

    def test_import_error_captured(self):
        r = run("import nonexistent_module_xyzzy")
        self.assertIsNotNone(r.error)

    def test_runtime_error_returncode_nonzero(self):
        r = run("raise ValueError('bad')")
        self.assertNotEqual(r.returncode, 0)

    def test_error_string_not_empty(self):
        r = run("1/0")
        self.assertIsNotNone(r.error)
        self.assertGreater(len(r.error), 0)

    def test_error_contains_exception_name(self):
        r = run("x = 1 / 0")
        self.assertIn("ZeroDivisionError", r.error)

    def test_temp_path_replaced_with_pussycat_label(self):
        # The raw temp file path must NOT appear in the remapped stderr
        r = run("if True")
        if r.error:
            self.assertNotIn("tmp", r.error.lower().replace("<pussycat>", ""))

    def test_success_has_no_error(self):
        self.assertIsNone(run("x = 1").error)


# ---------------------------------------------------------------------------
# #24 — stderr line number remapping
# ---------------------------------------------------------------------------

class TestLineRemapping(unittest.TestCase):

    def test_remapped_line_appears_in_error(self):
        # Python line 1 → PussyCat line 3 via line_map
        r = execute("x = 1 / 0", {1: 3})
        # The error text should reference line 3, not line 1
        self.assertIsNotNone(r.error)
        self.assertIn("3", r.error)

    def test_unmapped_line_falls_back_to_original(self):
        # line_map is empty — line number stays as-is
        r = execute("x = 1 / 0", {})
        self.assertIsNotNone(r.error)
        self.assertIn("1", r.error)

    def test_multi_line_map_remaps_correctly(self):
        # Error on Python line 2 → PussyCat line 5
        code = "x = 1\ny = 1 / 0"
        r = execute(code, {1: 4, 2: 5})
        self.assertIsNotNone(r.error)
        self.assertIn("5", r.error)

    def test_syntax_error_remapped(self):
        # SyntaxError on Python line 1 → PussyCat line 2
        r = execute("if True", {1: 2})
        self.assertIsNotNone(r.error)
        self.assertIn("2", r.error)


# ---------------------------------------------------------------------------
# #23 — Timeout case
# ---------------------------------------------------------------------------

class TestTimeoutCase(unittest.TestCase):

    def test_timeout_sets_timed_out_flag(self):
        # Mock TimeoutExpired so the test doesn't actually hang
        with patch("executor.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=10)):
            r = execute("while True: pass", {})
        self.assertTrue(r.timed_out)

    def test_timeout_returns_error_message(self):
        with patch("executor.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=10)):
            r = execute("while True: pass", {})
        self.assertIsNotNone(r.error)
        self.assertIn("timed out", r.error.lower())

    def test_timeout_returncode_is_negative(self):
        with patch("executor.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=10)):
            r = execute("while True: pass", {})
        self.assertEqual(r.returncode, -1)

    def test_timeout_stdout_is_empty(self):
        with patch("executor.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=10)):
            r = execute("while True: pass", {})
        self.assertEqual(r.stdout, "")

    def test_timeout_mentions_duration(self):
        with patch("executor.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=10)):
            r = execute("while True: pass", {})
        self.assertIn(str(EXECUTION_TIMEOUT), r.error)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_empty_string_returns_zero(self):
        r = run("")
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(r.error)
        self.assertEqual(r.stdout, "")

    def test_whitespace_only_returns_zero(self):
        r = run("   \n\n  ")
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(r.error)

    def test_comment_only_runs_fine(self):
        r = run("# just a comment")
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(r.error)

    def test_result_is_execution_result(self):
        self.assertIsInstance(run("x = 1"), ExecutionResult)

    def test_stdout_is_str(self):
        self.assertIsInstance(run("print('hi')").stdout, str)

    def test_stderr_is_str(self):
        self.assertIsInstance(run("x = 1").stderr, str)

    def test_returncode_is_int(self):
        self.assertIsInstance(run("x = 1").returncode, int)

    def test_timed_out_is_bool(self):
        self.assertIsInstance(run("x = 1").timed_out, bool)

    def test_large_output_captured(self):
        r = run("for i in range(500):\n    print(i)")
        self.assertIn("499", r.stdout)

    def test_unicode_output_captured(self):
        r = run("print('caf\\u00e9')")   # 'café' — ASCII-safe unicode escape
        self.assertIn("caf", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
