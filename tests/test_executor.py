import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from executor import execute


class TestExecutor(unittest.TestCase):

    def test_success(self):
        r = execute('print("hi")', {})
        self.assertEqual(r.stdout, "hi\n")
        self.assertIsNone(r.error)
        self.assertEqual(r.returncode, 0)

    def test_empty_code(self):
        r = execute("", {})
        self.assertIsNone(r.error)

    def test_error_remapped_to_source_line(self):
        r = execute("x = undefined_var", {1: 7})
        self.assertIsNotNone(r.error)
        self.assertIn("line 7 (PussyCat source)", r.error)

    def test_timeout(self):  # takes ~10 seconds
        r = execute("while True: pass", {})
        self.assertTrue(r.timed_out)
        self.assertIn("Timeout", r.error)


if __name__ == "__main__":
    unittest.main(verbosity=2)