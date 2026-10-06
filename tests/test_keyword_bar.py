"""Tests for the keyword button bar (Sprint-3 #32).

Skipped automatically when no display is available.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tkinter as tk

from constants import KEYWORD_MAP
from gui import PussyCatIDE


def _display_available() -> bool:
    try:
        tk.Tk().destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_display_available(), "no display available for tkinter")
class TestKeywordButtons(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PussyCatIDE(self.root)
        self.root.update()

    def tearDown(self):
        for after_id in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            self.root.after_cancel(after_id)
        self.root.destroy()

    def test_one_button_per_keyword(self):
        self.assertEqual(len(KEYWORD_MAP), 19)
        self.assertEqual(set(self.app.keyword_buttons), set(KEYWORD_MAP))
        for btn in self.app.keyword_buttons.values():
            self.assertIsInstance(btn, tk.Button)

    def test_button_shows_keyword_and_python_equivalent(self):
        for cat_kw, py_kw in KEYWORD_MAP.items():
            self.assertEqual(self.app.keyword_buttons[cat_kw].cget("text"), f"{cat_kw} → {py_kw}")

    def test_clicking_inserts_pussycat_keyword_not_python(self):
        self.app.keyword_buttons["meow"].invoke()
        self.app.keyword_buttons["nyan"].invoke()
        self.assertEqual(self.app.editor.get("1.0", "end-1c"), "meow nyan ")

    def test_inserts_at_cursor_position(self):
        self.app.editor.insert("1.0", "ab")
        self.app.editor.mark_set(tk.INSERT, "1.1")
        self.app.keyword_buttons["purr"].invoke()
        self.assertEqual(self.app.editor.get("1.0", "end-1c"), "apurr b")

    def test_inserted_keywords_run_end_to_end(self):
        for kw in ("nyan",):
            self.app.keyword_buttons[kw].invoke()
        self.app.editor.insert(tk.INSERT, '("button works")')
        self.app.run_pipeline()
        self.assertIn("button works", self.app.output.get("1.0", tk.END))

    def test_all_buttons_fit_in_window_width(self):
        self.root.deiconify()
        self.root.update()
        bar_right = self.app.keyword_bar.winfo_rootx() + self.app.keyword_bar.winfo_width()
        for btn in self.app.keyword_buttons.values():
            self.assertLessEqual(btn.winfo_rootx() + btn.winfo_width(), bar_right + 1)
            self.assertGreaterEqual(btn.winfo_reqwidth(), 1)


if __name__ == "__main__":
    unittest.main()
