import time
import unittest

from visie.variants import generate_variants


class TestVariants(unittest.TestCase):
    def test_single_letter_alternatives(self):
        """The original word comes first and every alternative letter is substituted."""
        self.assertEqual(["cat", "cut", "cot", "kat", "kut", "kot"], list(generate_variants("cat")))

    def test_multi_letter_alternatives(self):
        """An alternative spelling may be longer than the letter it replaces."""
        self.assertEqual(
            ["hope", "hupe", "hape", "khope", "khupe", "khape"],
            list(generate_variants("hope")),
        )

    def test_digraphs_are_a_single_position(self):
        self.assertEqual(["sh", "xi"], list(generate_variants("sh")))

    def test_empty_word(self):
        self.assertEqual([], list(generate_variants("   ")))

    def test_max_length_is_respected(self):
        max_length = 4
        for word in ("cat", "hope", "shoe", "wick"):
            with self.subTest(word=word):
                variants = list(generate_variants(word, max_length=max_length))
                self.assertTrue(variants)
                self.assertTrue(all(len(v) <= max_length for v in variants))

    def test_max_length_prunes_before_expanding(self):
        """Pruning keeps a pathological word from enumerating millions of discarded strings.

        Without prefix pruning, `pathologicopsychological` expands to 17,915,904 strings
        before any length filter applies, which takes over ten seconds.
        """
        started = time.monotonic()
        self.assertEqual([], list(generate_variants("pathologicopsychological", max_length=5)))
        self.assertLess(time.monotonic() - started, 5.0)
