from pathlib import Path
import unittest

from visie import generate
from visie.parser import Parser


LOCAL_DICT_PATH = str(Path(__file__).parent.absolute() / "words")


class TestVisie(unittest.TestCase):
    def test_visie(self):
        for test, expected in (
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
                    }
                ),
                (
                    "pleasing orange home <noise expeller>",
                    {
                        'HONE: home orange noise expeller',
                        'PHONE: pleasing home orange noise expeller',
                        'PONE: pleasing orange noise expeller',
                    }
                ),
                (
                    "[pleasing orange home <noise expeller>]",
                    {
                        'PHONE: pleasing home orange noise expeller',
                    }
                ),
                (
                    "pleasing home ({orange noise} expeller)",
                    {
                        'PHON: pleasing home orange noise',
                    }
                ),
                (
                    "<diaphone is? a? [pleasing orange home noise expeller]>",
                    {
                        'DIAPHONE: diaphone is a pleasing home orange noise expeller',
                    }
                ),
                (
                    "<. is? a? [pleasing orange home noise expeller]>",
                    {
                        'DIAPHONE: d is a pleasing home orange noise expeller',
                        'WANHOPE: w a noise home orange pleasing expeller',
                    }
                ),

        ):
            actual = {
                f"{a.name()}: {' '.join(a)}"
                for a in generate(Parser(test).parse(), min_length=4, dict_path=LOCAL_DICT_PATH)
            }
            if actual != expected:
                r = (f"\n    {a!r}," for a in sorted(actual))
                print(f"Actual result:\n{{{''.join(r)}\n}}\n")
            self.assertSetEqual(actual, expected)
