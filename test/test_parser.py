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
