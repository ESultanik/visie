import io
import tempfile
import unittest
from collections.abc import Iterable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from visie import Acronym, UnmatchedLetterError, backronyms
from visie.__main__ import main

TEST_DIR = Path(__file__).parent.absolute()
LOCAL_DICT_PATH = str(TEST_DIR / "words")

# No entry of `test/words` that starts with "y" is longer than fifteen letters, so this bucket is
# empty. `test_the_unmatched_letter_matches_at_the_default_word_length` guards the assumption.
UNMATCHED_LETTER = "Y"
UNMATCHED_MIN_WORD_LENGTH = 16

SMALL_WORDLIST = ("alpha", "amber", "ankle", "bravo", "bison")


def phrases(
    acronym: str, *, limit: int, seed: int | None = None, min_word_length: int = 4
) -> list[str]:
    return [
        " ".join(a)
        for a in backronyms(
            acronym,
            min_word_length=min_word_length,
            limit=limit,
            seed=seed,
            dict_path=LOCAL_DICT_PATH,
        )
    ]


def mean_word_length(results: Iterable[Acronym]) -> float:
    words = [word for result in results for word in result]
    return sum(len(word) for word in words) / len(words)


class TestBackronyms(unittest.TestCase):
    def test_the_same_seed_repeats_a_run(self):
        """Without a sampler of its own, `backronyms` would answer differently on every call."""
        first = phrases("HOPE", limit=10, seed=1)
        self.assertEqual(first, phrases("HOPE", limit=10, seed=1))
        self.assertNotEqual(first, phrases("HOPE", limit=10, seed=2))

    def test_the_initials_spell_the_acronym(self):
        for acronym in ("HOPE", "hope", "Visie", "ACRONYM"):
            with self.subTest(acronym=acronym):
                results = list(backronyms(acronym, limit=5, seed=3, dict_path=LOCAL_DICT_PATH))
                self.assertEqual(5, len(results))
                for result in results:
                    self.assertEqual(acronym.upper(), result.name())

    def test_every_word_is_long_enough(self):
        for min_word_length in (4, 9, 12):
            with self.subTest(min_word_length=min_word_length):
                results = list(
                    backronyms(
                        "HOPE",
                        min_word_length=min_word_length,
                        limit=10,
                        seed=4,
                        dict_path=LOCAL_DICT_PATH,
                    )
                )
                shortest = min(len(word) for result in results for word in result)
                self.assertGreaterEqual(shortest, min_word_length)

    def test_an_unmatched_letter_is_reported(self):
        """The letter has to be named: an empty bucket used to end the search without a word."""
        with self.assertRaises(UnmatchedLetterError) as caught:
            list(
                backronyms(
                    f"H{UNMATCHED_LETTER}",
                    min_word_length=UNMATCHED_MIN_WORD_LENGTH,
                    limit=1,
                    dict_path=LOCAL_DICT_PATH,
                )
            )
        self.assertEqual(UNMATCHED_LETTER, caught.exception.letter)
        self.assertIn(UNMATCHED_LETTER, str(caught.exception))

    def test_an_acronym_holds_only_letters(self):
        """An unchecked empty acronym yields one phrase that holds no words at all."""
        with self.assertRaises(UnmatchedLetterError) as caught:
            list(backronyms("HO-PE", limit=1, dict_path=LOCAL_DICT_PATH))
        self.assertEqual("-", caught.exception.letter)
        with self.assertRaises(UnmatchedLetterError):
            list(backronyms("", limit=1, dict_path=LOCAL_DICT_PATH))

    def test_the_unmatched_letter_matches_at_the_default_word_length(self):
        """`UNMATCHED_LETTER` goes unmatched only because of `UNMATCHED_MIN_WORD_LENGTH`."""
        self.assertEqual(1, len(phrases(UNMATCHED_LETTER, limit=1, seed=5)))

    def test_a_small_space_is_enumerated_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            wordlist = Path(directory) / "words"
            wordlist.write_text("\n".join(SMALL_WORDLIST), encoding="utf-8")
            results = [" ".join(a) for a in backronyms("AB", limit=20, seed=6, dict_path=wordlist)]
        self.assertEqual(6, len(results))
        self.assertEqual(len(results), len(set(results)))

    def test_the_limit_is_never_exceeded(self):
        for limit in (1, 3, 10, 25):
            with self.subTest(limit=limit):
                self.assertEqual(limit, len(phrases("HOPE", limit=limit, seed=7)))

    def test_ranking_a_pool_beats_sampling_alone(self):
        """A pool as small as the limit is an unranked sample: ranking cannot choose anything."""
        for seed in (1, 2, 3):
            with self.subTest(seed=seed):
                ranked = backronyms("HOPE", limit=10, seed=seed, dict_path=LOCAL_DICT_PATH)
                sampled = backronyms(
                    "HOPE", limit=10, pool=10, seed=seed, dict_path=LOCAL_DICT_PATH
                )
                self.assertLess(mean_word_length(ranked), mean_word_length(sampled))


class TestBackronymMain(unittest.TestCase):
    def test_backronyms_are_written_to_stdout(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["visie", "-b", "HOPE", "-d", LOCAL_DICT_PATH, "--seed", "1"])
        self.assertEqual(0, status)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(10, len(lines))
        for line in lines:
            self.assertTrue(line.startswith("HOPE: "))

    def test_an_unmatched_letter_exits_with_status_one(self):
        """An unmatched letter exits with status 1 instead of raising through `main`."""
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = main(
                [
                    "visie",
                    "-b",
                    UNMATCHED_LETTER,
                    "-d",
                    LOCAL_DICT_PATH,
                    "--min-word-length",
                    str(UNMATCHED_MIN_WORD_LENGTH),
                ]
            )
        self.assertEqual(1, status)
        self.assertIn(UNMATCHED_LETTER, stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
