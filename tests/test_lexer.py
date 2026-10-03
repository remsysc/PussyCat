"""Full test suite for lexer.tokenize().

Covers all token types, edge cases, and every fix applied across rounds 1 & 2.

Run with:  python tests/test_lexer.py
       or: python -m unittest discover tests
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import tokenize, Token, LexerResult
from constants import KEYWORD_MAP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lex_ok(source: str) -> list[Token]:
    result = tokenize(source)
    assert result.error is None, f"Unexpected lex error: {result.error}"
    return result.tokens


def token_types(source: str) -> list[str]:
    return [t.type for t in lex_ok(source)]


def token_values(source: str) -> list[str]:
    return [t.value for t in lex_ok(source)]


# ---------------------------------------------------------------------------
# Regex pattern & basic scanning
# ---------------------------------------------------------------------------

class TestRegexPattern(unittest.TestCase):

    def test_empty_source_returns_empty_list(self):
        result = tokenize("")
        self.assertIsNone(result.error)
        self.assertEqual(result.tokens, [])

    def test_single_identifier(self):
        tokens = lex_ok("x")
        self.assertEqual(tokens[0], Token(type="IDENT", value="x", line=1))

    def test_integer_number(self):
        self.assertIn("NUMBER", token_types("42"))

    def test_float_number(self):
        self.assertIn("NUMBER", token_types("3.14"))

    def test_double_quoted_string(self):
        tokens = lex_ok('"hello"')
        self.assertEqual(tokens[0].type, "STRING")
        self.assertEqual(tokens[0].value, '"hello"')

    def test_single_quoted_string(self):
        tokens = lex_ok("'world'")
        self.assertEqual(tokens[0].type, "STRING")

    def test_empty_double_quoted_string(self):
        tokens = lex_ok('""')
        self.assertEqual(tokens[0].type, "STRING")

    def test_empty_single_quoted_string(self):
        tokens = lex_ok("''")
        self.assertEqual(tokens[0].type, "STRING")

    def test_symbol_tokens(self):
        for sym in list("+-*/=<>!:(),"):
            tokens = lex_ok(sym)
            self.assertEqual(tokens[0].type, "SYMBOL", f"'{sym}' not SYMBOL")

    def test_whitespace_between_tokens(self):
        self.assertIn("WHITESPACE", token_types("x = 1"))

    def test_newlines_produce_whitespace(self):
        tokens = lex_ok("x\ny")
        self.assertTrue(any(t.type == "WHITESPACE" for t in tokens))


# ---------------------------------------------------------------------------
# Token classification
# ---------------------------------------------------------------------------

class TestTokenClassification(unittest.TestCase):

    def test_all_19_keywords_classified(self):
        for kw in KEYWORD_MAP:
            result = tokenize(kw)
            self.assertIsNone(result.error, f"Keyword '{kw}' caused error")
            self.assertEqual(result.tokens[0].type, "KEYWORD")

    def test_identifier_not_keyword(self):
        self.assertEqual(lex_ok("myVar")[0].type, "IDENT")

    def test_underscore_identifier(self):
        self.assertEqual(lex_ok("_private")[0].type, "IDENT")

    def test_mixed_case_identifier(self):
        self.assertEqual(lex_ok("MyClass")[0].type, "IDENT")

    def test_comment_token(self):
        self.assertEqual(lex_ok("# a comment")[0].type, "COMMENT")

    def test_number_types(self):
        nums = [t for t in lex_ok("0 1 99 3.14 0.5") if t.type == "NUMBER"]
        self.assertEqual(len(nums), 5)

    def test_whitespace_type(self):
        self.assertEqual(lex_ok("   ")[0].type, "WHITESPACE")

    def test_keyword_inside_ident_not_split(self):
        # 'o' is a keyword but 'foo' must be a single IDENT
        tokens = lex_ok("foo")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, "IDENT")


# ---------------------------------------------------------------------------
# Line tracking
# ---------------------------------------------------------------------------

class TestLineTracking(unittest.TestCase):

    def test_single_line_all_line_1(self):
        for t in lex_ok("x = 1"):
            self.assertEqual(t.line, 1)

    def test_newline_increments_line(self):
        tokens = lex_ok("x\ny")
        idents = {t.value: t.line for t in tokens if t.type == "IDENT"}
        self.assertEqual(idents["x"], 1)
        self.assertEqual(idents["y"], 2)

    def test_multi_line_tracking(self):
        idents = [t for t in lex_ok("a\nb\nc") if t.type == "IDENT"]
        self.assertEqual(idents[0].line, 1)
        self.assertEqual(idents[1].line, 2)
        self.assertEqual(idents[2].line, 3)

    def test_error_reports_correct_line(self):
        result = tokenize("x = 1\ny = @")
        self.assertIsNotNone(result.error)
        self.assertIn("Line 2", result.error)


# ---------------------------------------------------------------------------
# Unknown tokens / LexerError
# ---------------------------------------------------------------------------

class TestUnknownTokens(unittest.TestCase):

    def test_at_sign_is_unknown(self):
        result = tokenize("@")
        self.assertIsNotNone(result.error)
        self.assertIsNone(result.tokens)

    def test_dollar_sign_is_unknown(self):
        result = tokenize("$var")
        self.assertIsNotNone(result.error)

    def test_error_message_format(self):
        result = tokenize("@ x = 5")
        self.assertIn("[Lexer Error]", result.error)
        self.assertIn("Line 1", result.error)
        self.assertIn("@", result.error)

    def test_unknown_token_aborts_early(self):
        result = tokenize("@ bad\nx = 1")
        self.assertIsNone(result.tokens)

    def test_unknown_on_line_2(self):
        result = tokenize("x = 1\n@bad")
        self.assertIn("Line 2", result.error)

    def test_stray_double_quote_is_unknown(self):
        result = tokenize('"')
        self.assertIsNotNone(result.error)
        self.assertIsNone(result.tokens)

    def test_stray_single_quote_is_unknown(self):
        result = tokenize("'")
        self.assertIsNotNone(result.error)
        self.assertIsNone(result.tokens)


# ---------------------------------------------------------------------------
# Non-throwing invariant (fix #6)
# ---------------------------------------------------------------------------

class TestNonThrowingInvariant(unittest.TestCase):

    def test_none_does_not_raise(self):
        try:
            result = tokenize(None)
        except Exception as e:
            self.fail(f"tokenize(None) raised {type(e).__name__}")
        self.assertIsNotNone(result.error)
        self.assertIsNone(result.tokens)

    def test_int_input_returns_error(self):
        result = tokenize(42)
        self.assertIsNotNone(result.error)

    def test_list_input_returns_error(self):
        result = tokenize(["kung x:"])
        self.assertIsNotNone(result.error)

    def test_dict_input_returns_error(self):
        result = tokenize({"code": "x"})
        self.assertIsNotNone(result.error)

    def test_error_message_mentions_string(self):
        self.assertIn("string", tokenize(None).error.lower())

    def test_empty_string_works(self):
        result = tokenize("")
        self.assertIsNone(result.error)
        self.assertEqual(result.tokens, [])


# ---------------------------------------------------------------------------
# Comment handling (fix #1)
# ---------------------------------------------------------------------------

class TestComments(unittest.TestCase):

    def test_full_comment_is_single_token(self):
        tokens = lex_ok("# this is a comment")
        comments = [t for t in tokens if t.type == "COMMENT"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].value, "# this is a comment")

    def test_hash_alone_is_comment(self):
        tokens = lex_ok("#")
        self.assertEqual(tokens[0].type, "COMMENT")

    def test_keyword_inside_comment_stays_verbatim(self):
        tokens = lex_ok("# kung totoo")
        self.assertEqual(tokens[0].type, "COMMENT")
        self.assertEqual(tokens[0].value, "# kung totoo")

    def test_bad_symbols_inside_comment_no_crash(self):
        result = tokenize("# 100% email: a@b.com $5")
        self.assertIsNone(result.error)

    def test_comment_followed_by_code(self):
        tokens = lex_ok("# comment\nx = 1")
        idents = [t for t in tokens if t.type == "IDENT"]
        self.assertTrue(any(t.value == "x" for t in idents))

    def test_two_comment_lines(self):
        comments = [t for t in lex_ok("# one\n# two") if t.type == "COMMENT"]
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].value, "# one")
        self.assertEqual(comments[1].value, "# two")


# ---------------------------------------------------------------------------
# String edge cases (fixes #3 & #7)
# ---------------------------------------------------------------------------

class TestStringEdgeCases(unittest.TestCase):

    def test_string_with_escaped_double_quote(self):
        result = tokenize(r'"foo \" bar"')
        self.assertIsNone(result.error)
        self.assertEqual(result.tokens[0].type, "STRING")

    def test_string_with_escaped_single_quote(self):
        result = tokenize(r"'it\'s fine'")
        self.assertIsNone(result.error)
        self.assertEqual(result.tokens[0].type, "STRING")

    def test_string_with_escaped_backslash(self):
        result = tokenize(r'"path\\file"')
        self.assertIsNone(result.error)
        self.assertEqual(result.tokens[0].type, "STRING")

    def test_unclosed_double_quote_stops_at_newline(self):
        result = tokenize('"unclosed\nx = 1')
        self.assertIsNotNone(result.error)

    def test_unclosed_single_quote_stops_at_newline(self):
        result = tokenize("'unclosed\nx = 1")
        self.assertIsNotNone(result.error)

    def test_unclosed_quote_does_not_swallow_next_line(self):
        result = tokenize('"oops\nkung x > 0:')
        self.assertIsNotNone(result.error)

    def test_two_strings_on_separate_lines(self):
        result = tokenize('"first"\n"second"')
        self.assertIsNone(result.error)
        strings = [t for t in result.tokens if t.type == "STRING"]
        self.assertEqual(len(strings), 2)

    def test_string_with_spaces(self):
        tokens = lex_ok('"hello world"')
        self.assertEqual(tokens[0].type, "STRING")


# ---------------------------------------------------------------------------
# Missing operators (fix #3)
# ---------------------------------------------------------------------------

class TestOperators(unittest.TestCase):

    def test_modulo_is_symbol(self):
        self.assertEqual(lex_ok("%")[0].type, "SYMBOL")

    def test_ampersand_is_symbol(self):
        self.assertEqual(lex_ok("&")[0].type, "SYMBOL")

    def test_pipe_is_symbol(self):
        self.assertEqual(lex_ok("|")[0].type, "SYMBOL")

    def test_caret_is_symbol(self):
        self.assertEqual(lex_ok("^")[0].type, "SYMBOL")

    def test_tilde_is_symbol(self):
        self.assertEqual(lex_ok("~")[0].type, "SYMBOL")

    def test_semicolon_is_symbol(self):
        self.assertEqual(lex_ok(";")[0].type, "SYMBOL")

    def test_modulo_expression_no_crash(self):
        self.assertIsNone(tokenize("x = 10 % 3").error)

    def test_bitwise_expression_no_crash(self):
        self.assertIsNone(tokenize("x = a & b | c ^ ~d").error)

    def test_at_still_unknown(self):
        self.assertIsNotNone(tokenize("@").error)

    def test_dollar_still_unknown(self):
        self.assertIsNotNone(tokenize("$").error)


# ---------------------------------------------------------------------------
# Full snippet integration
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def test_full_pussycat_snippet(self):
        source = (
            "trick halaga(x):\n"
            "    meow x > 0:\n"
            "        furball purr\n"
            "    mew:\n"
            "        furball hiss\n"
        )
        result = tokenize(source)
        self.assertIsNone(result.error)
        kws = [t.value for t in result.tokens if t.type == "KEYWORD"]
        for kw in ["trick", "meow", "furball", "purr", "mew", "hiss"]:
            self.assertIn(kw, kws)

    def test_never_raises(self):
        for src in ["@@@", "$$$", "\x00", "~~ bad", None, 42]:
            try:
                result = tokenize(src)
                self.assertIsInstance(result, LexerResult)
            except Exception as e:
                self.fail(f"tokenize raised {type(e).__name__} on {src!r}")

    def test_result_type(self):
        self.assertIsInstance(tokenize("x = 1"), LexerResult)


if __name__ == "__main__":
    unittest.main(verbosity=2)
