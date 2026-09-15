import unittest
from pathlib import Path

from visie import generate
from visie.parser import Parser

LOCAL_DICT_PATH = str(Path(__file__).parent.absolute() / "words")

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
