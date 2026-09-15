import os
import unittest
from pathlib import Path
from unittest.mock import patch

from visie import DICT_ENV_VAR, DictionaryNotFoundError, find_dictionary, generate
from visie.parser import Parser

TEST_DIR = Path(__file__).parent.absolute()
LOCAL_DICT = TEST_DIR / "words"
LOCAL_DICT_PATH = str(LOCAL_DICT)
MISSING_DICT = TEST_DIR / "no-such-wordlist"

README_EXAMPLES: tuple[tuple[str, set[str]], ...] = (
    (
        "pleasing orange home noise expeller",
        {
            "HONE: home orange noise expeller",
            "HOPE: home orange pleasing expeller",
            "NOPE: noise orange pleasing expeller",
            "OPEN: orange pleasing expeller noise",
            "PEHO: pleasing expeller home orange",
            "PEON: pleasing expeller orange noise",
            "PHEON: pleasing home expeller orange noise",
            "PHON: pleasing home orange noise",
            "PHONE: pleasing home orange noise expeller",
            "PONE: pleasing orange noise expeller",
        },
    ),
    (
        "pleasing orange home <noise expeller>",
        {
            "HONE: home orange noise expeller",
            "PHONE: pleasing home orange noise expeller",
            "PONE: pleasing orange noise expeller",
        },
    ),
    (
        "[pleasing orange home <noise expeller>]",
        {
            "PHONE: pleasing home orange noise expeller",
        },
    ),
    (
        "pleasing home ({orange noise} expeller)",
        {
            "PHON: pleasing home orange noise",
        },
    ),
    (
        "<diaphone is? a? [pleasing orange home noise expeller]>",
        {
            "DIAPHONE: diaphone is a pleasing home orange noise expeller",
        },
    ),
    (
        "<. is? a? [pleasing orange home noise expeller]>",
        {
            "DIAPHONE: d is a pleasing home orange noise expeller",
            "WANHOPE: w a noise home orange pleasing expeller",
        },
    ),
)


def acronyms(constraint: str, use_variants: bool = False) -> set[str]:
    return {
        f"{a.name()}: {' '.join(a)}"
        for a in generate(
            Parser(constraint).parse(),
            min_length=4,
            use_variants=use_variants,
            dict_path=LOCAL_DICT_PATH,
        )
    }


class TestVisie(unittest.TestCase):
    def test_visie(self):
        for constraint, expected in README_EXAMPLES:
            with self.subTest(constraint=constraint):
                self.assertSetEqual(expected, acronyms(constraint))

    def test_min_length(self):
        expected = {
            "HEP: home expeller pleasing",
            "HOP: home orange pleasing",
            "PHO: pleasing home orange",
            "POH: pleasing orange home",
        }
        actual = {
            f"{a.name()}: {' '.join(a)}"
            for a in generate(
                Parser("pleasing home (orange noise expeller)").parse(),
                min_length=3,
                dict_path=LOCAL_DICT_PATH,
            )
        }
        self.assertSetEqual(expected, actual)

    def test_variants_extend_the_results(self):
        """Variant spellings add results without dropping any of the unmodified ones."""
        constraint = "pleasing orange home noise expeller"
        baseline = acronyms(constraint)
        with_variants = acronyms(constraint, use_variants=True)
        self.assertTrue(with_variants)
        self.assertLessEqual(baseline, with_variants)
        self.assertNotEqual(baseline, with_variants)


class TestFindDictionary(unittest.TestCase):
    def test_an_explicit_path_wins(self):
        """`--dict` and the `dict_path` argument outrank both lower precedence sources."""
        with (
            patch.dict(os.environ, {DICT_ENV_VAR: str(MISSING_DICT)}),
            patch("visie.visie.DICT_SEARCH_PATH", (MISSING_DICT,)),
        ):
            self.assertEqual(LOCAL_DICT, find_dictionary(LOCAL_DICT_PATH))

    def test_the_environment_variable_wins_over_the_search_path(self):
        with (
            patch.dict(os.environ, {DICT_ENV_VAR: LOCAL_DICT_PATH}),
            patch("visie.visie.DICT_SEARCH_PATH", (MISSING_DICT,)),
        ):
            self.assertEqual(LOCAL_DICT, find_dictionary())

    def test_unreadable_search_path_entries_are_skipped(self):
        """A path that exists but cannot be read must not shadow a readable one further down.

        The test directory stands in for the unreadable entry because opening it fails for every
        user, including root. A file with its permission bits cleared would not: root reads it
        anyway, and the suite often runs as root in a container.
        """
        search_path = (MISSING_DICT, TEST_DIR, LOCAL_DICT)
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("visie.visie.DICT_SEARCH_PATH", search_path),
        ):
            self.assertEqual(LOCAL_DICT, find_dictionary())

    def test_the_error_names_every_path_that_was_tried(self):
        search_path = (MISSING_DICT, TEST_DIR / "no-such-wordlist-either")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("visie.visie.DICT_SEARCH_PATH", search_path),
            self.assertRaises(DictionaryNotFoundError) as caught,
        ):
            find_dictionary()
        message = str(caught.exception)
        for path in search_path:
            self.assertIn(str(path), message)
        self.assertIn(DICT_ENV_VAR, message)

    def test_generate_reads_the_resolved_dictionary(self):
        constraint, expected = README_EXAMPLES[0]
        with (
            patch.dict(os.environ, {DICT_ENV_VAR: LOCAL_DICT_PATH}),
            patch("visie.visie.DICT_SEARCH_PATH", (MISSING_DICT,)),
        ):
            actual = {
                f"{a.name()}: {' '.join(a)}"
                for a in generate(Parser(constraint).parse(), min_length=4)
            }
        self.assertSetEqual(expected, actual)
