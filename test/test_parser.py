import unittest

import visie
from visie.parser import ParseException, Parser, Token, tokenize


class TestParser(unittest.TestCase):
    def test_tokenize(self):
        self.assertTrue(
            all(
                isinstance(t, Token)
                for t in tokenize("foo bar? (one two) {three four} <five six [seven eight]>")
            )
        )
        self.assertRaises(ParseException, lambda: list(tokenize("illegal1")))
        self.assertRaises(ParseException, lambda: list(tokenize("illegal!")))

    def test_illegal_token_caret_position(self):
        """The caret marks the offending character, not an offset counted from the end."""
        with self.assertRaises(ParseException) as context:
            list(tokenize("abc9def"))
        text, caret = str(context.exception).splitlines()[:2]
        self.assertEqual("abc9def", text)
        self.assertEqual(caret.index("^"), text.index("9"))

    def test_multi_line_caret_position(self):
        """A token on a later line is shown with only that line, not the whole text."""
        fulltext = "alpha beta\ngamma delta"
        offset = fulltext.index("delta")
        line, caret = str(Token("delta", offset, fulltext)).splitlines()
        self.assertEqual("gamma delta", line)
        self.assertEqual(caret.index("^"), line.index("delta"))
        self.assertEqual("^" * len("delta"), caret.strip())

    def test_parse(self):
        self.assertIsInstance(Parser("foo").parse(), visie.DictionaryWord)
        self.assertIsInstance(Parser("foo bar").parse(), visie.AnyOfConstraint)
        self.assertIsInstance(Parser("{foo bar}").parse(), visie.AnyOfConstraint)
        self.assertIsInstance(Parser("<foo bar>").parse(), visie.OrderedConstraint)
        self.assertIsInstance(Parser("(foo bar)").parse(), visie.ExactlyOneConstraint)
        self.assertIsInstance(Parser("foo?").parse(), visie.OptionalConstraint)
        self.assertIsInstance(Parser(".").parse(), visie.Wildcard)

    def test_parse_errors(self):
        """Every malformed constraint raises `ParseException`, never a bare exception."""
        for constraint in ("<abc", "?abc", "", "(abc"):
            with self.subTest(constraint=constraint), self.assertRaises(ParseException):
                Parser(constraint).parse()
