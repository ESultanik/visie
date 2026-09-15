import io
import tempfile
import unittest
from collections.abc import Iterable, Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from visie import RANK_MODES, UnknownRankError, backronyms
from visie.__main__ import main
from visie.visie import _rhyme, _syllable_spread, _syllables

TEST_DIR = Path(__file__).parent.absolute()
LOCAL_DICT_PATH = str(TEST_DIR / "words")

LIMIT = 10
SEED = 1

SYLLABLE_TRUTH = {
    "cat": 1,
    "strength": 1,
    "rye": 1,
    "bake": 1,
    "bakes": 1,
    "table": 2,
    "simple": 2,
    "coffee": 2,
    "orange": 2,
    "boxes": 2,
    "cages": 2,
    "machine": 2,
    "buckeye": 2,
    "banana": 3,
    "beautiful": 3,
    "syllable": 3,
    "elephant": 3,
    "university": 5,
}

# Words that `_syllables` gets wrong, and what it counts instead. `poem`, `idea` and `create`
# are hiatus, `rhythm` spells a syllable with no vowel letter, and the silent `e` rule drops the
# spoken `-es` of `wishes` because `sh` is not one of the letters that rule looks for.
SYLLABLE_MISSES = {"rhythm": 1, "poem": 1, "idea": 2, "create": 1, "wishes": 1}

# Every phrase built from this wordlist ends in `-ly` twice over, so the guard can pick only one
# of them and has to fall back on the ones it held back.
RHYMING_WORDLIST = ("amply", "apply", "amberly", "bravely", "barely", "bodily")

# Distinct three character word endings among the `LIMIT` phrases of a run, with the diversity
# guard on and with `allow_similar` turning it off. Ranking for sound is what collapses them.
DISTINCT_ENDINGS = {
    ("HOPE", "rhyme"): (20, 12),
    ("HOPE", "harmony"): (23, 13),
    ("VISIE", "rhyme"): (28, 21),
    ("VISIE", "harmony"): (26, 22),
}


def phrases(
    acronym: str, *, rank: str, limit: int = LIMIT, seed: int = SEED, allow_similar: bool = False
) -> list[list[str]]:
    return [
        list(result)
        for result in backronyms(
            acronym,
            limit=limit,
            seed=seed,
            rank=rank,
            allow_similar=allow_similar,
            dict_path=LOCAL_DICT_PATH,
        )
    ]


def distinct_endings(results: Iterable[Sequence[str]], length: int = 3) -> int:
    return len({word.lower()[-length:] for result in results for word in result})


def mean(values: Iterable[float]) -> float:
    counted = list(values)
    return sum(counted) / len(counted)


def run(*arguments: str) -> tuple[int, list[str]]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = main(["visie", *arguments, "-d", LOCAL_DICT_PATH])
    return status, stdout.getvalue().splitlines()


class TestRankModes(unittest.TestCase):
    def test_every_mode_fills_the_limit(self):
        for rank in RANK_MODES:
            with self.subTest(rank=rank):
                results = phrases("HOPE", rank=rank)
                self.assertEqual(LIMIT, len(results))
                for result in results:
                    self.assertEqual(4, len(result))

    def test_rhyme_outscores_brevity_on_the_rhyme_metric(self):
        """Ranking for rhyme has to move the rhyme score, or the mode does nothing."""
        rhyming = mean(_rhyme(result) for result in phrases("HOPE", rank="rhyme"))
        brief = mean(_rhyme(result) for result in phrases("HOPE", rank="brevity"))
        self.assertGreater(rhyming, brief)

    def test_rhythm_narrows_the_syllable_spread(self):
        """Ranking for rhythm has to move the syllable spread, or the mode does nothing."""
        even = mean(_syllable_spread(result) for result in phrases("HOPE", rank="rhythm"))
        brief = mean(_syllable_spread(result) for result in phrases("HOPE", rank="brevity"))
        self.assertLess(even, brief)

    def test_a_seed_repeats_a_run_in_every_mode(self):
        for rank in RANK_MODES:
            with self.subTest(rank=rank):
                first = phrases("HOPE", rank=rank, limit=5)
                self.assertEqual(first, phrases("HOPE", rank=rank, limit=5))
                self.assertNotEqual(first, phrases("HOPE", rank=rank, limit=5, seed=SEED + 1))

    def test_an_unknown_mode_is_reported(self):
        """An unchecked mode used to reach the ranking table and raise a bare `KeyError`."""
        with self.assertRaises(UnknownRankError) as caught:
            list(backronyms("HOPE", limit=1, rank="bogus", dict_path=LOCAL_DICT_PATH))
        self.assertEqual("bogus", caught.exception.rank)
        for rank in RANK_MODES:
            self.assertIn(rank, str(caught.exception))


class TestDiversityGuard(unittest.TestCase):
    def test_the_guard_raises_the_count_of_distinct_endings(self):
        """Without the guard, every phrase of a run ends the same way without repeating a word."""
        for (acronym, rank), (guarded, unguarded) in DISTINCT_ENDINGS.items():
            with self.subTest(acronym=acronym, rank=rank):
                self.assertEqual(guarded, distinct_endings(phrases(acronym, rank=rank)))
                self.assertEqual(
                    unguarded, distinct_endings(phrases(acronym, rank=rank, allow_similar=True))
                )
                self.assertGreater(guarded, unguarded)

    def test_the_guard_still_fills_the_limit(self):
        """Holding phrases back must not cost the caller results the pool can supply."""
        for rank in RANK_MODES:
            with self.subTest(rank=rank):
                self.assertEqual(LIMIT, len(phrases("HOPE", rank=rank)))

    def test_the_guard_falls_back_when_every_phrase_ends_alike(self):
        """A cap with nothing to fall back on would answer with one phrase instead of five."""
        with tempfile.TemporaryDirectory() as directory:
            wordlist = Path(directory) / "words"
            wordlist.write_text("\n".join(RHYMING_WORDLIST), encoding="utf-8")
            results = list(backronyms("AB", limit=5, seed=SEED, rank="rhyme", dict_path=wordlist))
        self.assertEqual(5, len(results))
        self.assertEqual(5, len({" ".join(result) for result in results}))

    def test_the_guard_leaves_brevity_alone(self):
        """Short words rarely end alike, so the guard has nothing to hold back."""
        self.assertEqual(
            phrases("HOPE", rank="brevity"),
            phrases("HOPE", rank="brevity", allow_similar=True),
        )


class TestSyllables(unittest.TestCase):
    def test_the_count_matches_the_truth_table(self):
        for word, expected in SYLLABLE_TRUTH.items():
            with self.subTest(word=word):
                self.assertEqual(expected, _syllables(word))

    def test_the_known_misses_are_unchanged(self):
        """Spelling cannot settle these, so they are pinned rather than fixed."""
        for word, counted in SYLLABLE_MISSES.items():
            with self.subTest(word=word):
                self.assertEqual(counted, _syllables(word))


class TestRankModesMain(unittest.TestCase):
    def test_every_mode_writes_backronyms(self):
        for rank in RANK_MODES:
            with self.subTest(rank=rank):
                status, lines = run("-b", "HOPE", "--rank", rank, "--seed", "1", "-n", "5")
                self.assertEqual(0, status)
                self.assertEqual(5, len(lines))
                for line in lines:
                    self.assertTrue(line.startswith("HOPE: "))

    def test_the_rank_flag_reaches_the_ranking(self):
        """A flag that never reaches `backronyms` would leave every mode printing the default."""
        _, lines = run("-b", "HOPE", "--rank", "brevity", "--seed", str(SEED), "-n", "5")
        expected = [
            f"HOPE: {' '.join(result)}" for result in phrases("HOPE", rank="brevity", limit=5)
        ]
        self.assertEqual(expected, lines)

    def test_allow_similar_changes_the_ranked_output(self):
        _, guarded = run("-b", "HOPE", "--rank", "harmony", "--seed", "1", "-n", "5")
        _, unguarded = run(
            "-b", "HOPE", "--rank", "harmony", "--seed", "1", "-n", "5", "--allow-similar"
        )
        self.assertNotEqual(guarded, unguarded)

    def test_an_unknown_mode_exits_with_status_two(self):
        """Argparse rejects the value, so no phrase is ever ranked and no traceback is printed."""
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            run("-b", "HOPE", "--rank", "bogus", "-n", "5")
        self.assertEqual(2, caught.exception.code)
        self.assertIn("--rank", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
