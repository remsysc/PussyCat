"""Full test suite for transpiler.transpile().

Covers code building, keyword substitution, line_map generation, and all
fixes applied across rounds 1 & 2.

Run with:  python tests/test_transpiler.py
       or: python -m unittest discover tests
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import tokenize
from transpiler import transpile, TranspileResult
from constants import KEYWORD_MAP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lex_and_transpile(source: str) -> TranspileResult:
    result = tokenize(source)
    assert result.error is None, f"Lex error: {result.error}"
    return transpile(result.tokens)


# ---------------------------------------------------------------------------
# Code building (#20)
# ---------------------------------------------------------------------------

class TestCodeBuilding(unittest.TestCase):

    def test_empty_tokens_returns_empty_string(self):
        r = transpile([])
        self.assertEqual(r.python, "")

    def test_ident_unchanged(self):
        self.assertEqual(lex_and_transpile("x").python, "x")

    def test_number_unchanged(self):
        self.assertEqual(lex_and_transpile("42").python, "42")

    def test_float_unchanged(self):
        self.assertEqual(lex_and_transpile("3.14").python, "3.14")

    def test_string_unchanged(self):
        self.assertEqual(lex_and_transpile('"hello"').python, '"hello"')

    def test_symbol_unchanged(self):
        self.assertEqual(lex_and_transpile("(").python, "(")

    def test_comment_unchanged(self):
        self.assertIn("# a comment", lex_and_transpile("# a comment").python)

    def test_whitespace_preserved(self):
        self.assertEqual(lex_and_transpile("x = 1").python, "x = 1")

    def test_newlines_preserved(self):
        self.assertEqual(lex_and_transpile("x = 1\ny = 2").python, "x = 1\ny = 2")

    def test_indentation_preserved(self):
        r = lex_and_transpile("meow x > 0:\n    nyan(x)")
        self.assertIn("    ", r.python)

    def test_result_is_transpile_result(self):
        self.assertIsInstance(lex_and_transpile("x = 1"), TranspileResult)

    def test_python_is_str(self):
        self.assertIsInstance(lex_and_transpile("x = 1").python, str)


# ---------------------------------------------------------------------------
# Keyword substitution (#22)
# ---------------------------------------------------------------------------

class TestKeywordSubstitution(unittest.TestCase):

    def test_all_19_keywords_substituted(self):
        for kw, py in KEYWORD_MAP.items():
            r = lex_and_transpile(kw)
            self.assertEqual(r.python, py, f"'{kw}' → expected '{py}', got '{r.python}'")

    def test_meow_becomes_if(self):
        self.assertTrue(lex_and_transpile("meow x > 0:").python.startswith("if"))

    def test_mew_becomes_else(self):
        self.assertIn("else", lex_and_transpile("mew:").python)

    def test_chase_becomes_while(self):
        self.assertIn("while", lex_and_transpile("chase purr:").python)

    def test_paws_becomes_for(self):
        self.assertIn("for", lex_and_transpile("paws i in range(5):").python)

    def test_furball_becomes_return(self):
        self.assertIn("return", lex_and_transpile("furball x").python)

    def test_purr_becomes_True(self):
        self.assertEqual(lex_and_transpile("purr").python, "True")

    def test_hiss_becomes_False(self):
        self.assertEqual(lex_and_transpile("hiss").python, "False")

    def test_box_becomes_None(self):
        self.assertEqual(lex_and_transpile("box").python, "None")

    def test_nyan_becomes_print(self):
        self.assertTrue(lex_and_transpile('nyan("hi")').python.startswith("print"))

    def test_non_keyword_not_substituted(self):
        self.assertEqual(lex_and_transpile("myVar").python, "myVar")

    def test_comment_keyword_not_substituted(self):
        r = lex_and_transpile("# kung totoo")
        self.assertEqual(r.python, "# kung totoo")
        self.assertNotIn("if True", r.python)


# ---------------------------------------------------------------------------
# line_map generation (#21)
# ---------------------------------------------------------------------------

class TestLineMapGeneration(unittest.TestCase):

    def test_empty_source_empty_map(self):
        self.assertEqual(transpile([]).line_map, {})

    def test_single_line_maps_to_1(self):
        r = lex_and_transpile("x = 1")
        for v in r.line_map.values():
            self.assertEqual(v, 1)

    def test_two_line_map(self):
        r = lex_and_transpile("x = 1\ny = 2")
        self.assertEqual(r.line_map.get(1), 1)
        self.assertEqual(r.line_map.get(2), 2)

    def test_keyword_on_line_2(self):
        r = lex_and_transpile("x = 1\nkung x > 0:")
        self.assertEqual(r.line_map.get(2), 2)

    def test_five_line_function_map(self):
        source = (
            "gawain saludo(n):\n"
            "    ipakita(n)\n"
            "    ibalik totoo\n"
            "    wala\n"
            "    mali\n"
        )
        r = lex_and_transpile(source)
        for n in range(1, 6):
            self.assertEqual(r.line_map.get(n), n, f"line {n} mismatch")

    def test_consecutive_blank_lines_each_map_to_own_source_line(self):
        # Fix #1 (round 2): token.line + i, not token.line
        source = "x = 1\n\n\ny = 2"
        r = lex_and_transpile(source)
        # blank lines 2 and 3 must NOT all map to line 1
        self.assertNotEqual(r.line_map.get(2), 1)
        self.assertNotEqual(r.line_map.get(3), 1)
        self.assertEqual(r.line_map.get(2), 2)
        self.assertEqual(r.line_map.get(3), 3)

    def test_no_gaps_in_line_map(self):
        source = "a = 1\n\nb = 2\n\nc = 3"
        r = lex_and_transpile(source)
        max_line = max(r.line_map.keys())
        for n in range(1, max_line + 1):
            self.assertIn(n, r.line_map, f"gap at line {n}")

    def test_line_map_keys_positive_ints(self):
        r = lex_and_transpile("x = 1\ny = 2")
        for k in r.line_map:
            self.assertIsInstance(k, int)
            self.assertGreater(k, 0)

    def test_line_map_values_positive_ints(self):
        r = lex_and_transpile("x = 1\ny = 2")
        for v in r.line_map.values():
            self.assertIsInstance(v, int)
            self.assertGreater(v, 0)

    def test_line_map_is_dict(self):
        self.assertIsInstance(lex_and_transpile("x = 1").line_map, dict)


# ---------------------------------------------------------------------------
# Integration — full PussyCat snippets
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def test_print_hello(self):
        self.assertEqual(lex_and_transpile('nyan("hello")').python, 'print("hello")')

    def test_if_else_block(self):
        source = "meow x > 0:\n    nyan(x)\nmew:\n    nyan(0)\n"
        r = lex_and_transpile(source)
        self.assertIn("if x > 0:", r.python)
        self.assertIn("else:", r.python)

    def test_while_loop(self):
        r = lex_and_transpile("chase x > 0:\n    x = x - 1\n")
        self.assertIn("while x > 0:", r.python)

    def test_function_definition(self):
        r = lex_and_transpile("trick add(a, b):\n    furball a + b\n")
        self.assertIn("def add(a, b):", r.python)
        self.assertIn("return a + b", r.python)

    def test_try_except_finally(self):
        source = "pounce:\n    nyan(x)\nmiss:\n    nyan(0)\nnap:\n    nyan(1)\n"
        r = lex_and_transpile(source)
        self.assertIn("try:", r.python)
        self.assertIn("except:", r.python)
        self.assertIn("finally:", r.python)

    def test_boolean_literals(self):
        r = lex_and_transpile("x = purr\ny = hiss\nz = box")
        self.assertIn("True",  r.python)
        self.assertIn("False", r.python)
        self.assertIn("None",  r.python)

    def test_logical_operators(self):
        r = lex_and_transpile("meow x > 0 whiskers y > 0:")
        self.assertIn("and", r.python)

    def test_modulo_expression(self):
        r = lex_and_transpile("x = 10 % 3")
        self.assertEqual(r.python, "x = 10 % 3")

    def test_bitwise_expression(self):
        r = lex_and_transpile("x = a & b | c")
        self.assertIn("&", r.python)
        self.assertIn("|", r.python)

    def test_escaped_string_passthrough(self):
        r = lex_and_transpile(r'nyan("hello \"world\"")')
        self.assertIn('print', r.python)
        self.assertIn('\\"', r.python)

    def test_import_from(self):
        r = lex_and_transpile("shelter os adopt path")
        self.assertIn("from", r.python)
        self.assertIn("import", r.python)


if __name__ == "__main__":
    unittest.main(verbosity=2)
