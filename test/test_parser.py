import unittest

import visie
from visie.parser import Parser, ParseException, Token, tokenize


class TestParser(unittest.TestCase):
    def test_tokenize(self):
        self.assertTrue(
            all(isinstance(t, Token) for t in tokenize("foo bar? (one two) {three four} <five six [seven eight]>"))
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
