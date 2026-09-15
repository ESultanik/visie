import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from visie.__main__ import main

LOCAL_DICT_PATH = str(Path(__file__).parent.absolute() / "words")


class TestMain(unittest.TestCase):
    def test_parse_errors_are_reported(self):
        """A malformed constraint exits with status 1 instead of raising through `main`."""
        for constraint in ("<abc", "?abc", "", "()"):
            with self.subTest(constraint=constraint):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    status = main(["visie", constraint, "-d", LOCAL_DICT_PATH])
                self.assertEqual(1, status)
                self.assertTrue(stderr.getvalue().strip())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_parse_error_without_a_dictionary_argument(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = main(["visie", "<abc"])
        self.assertEqual(1, status)
        self.assertIn("^", stderr.getvalue())

    def test_broken_pipe(self):
        """Closing the reader mid-stream exits cleanly rather than printing a traceback."""
        process = subprocess.Popen(
            [sys.executable, "-m", "visie", "<. . . . .>", "-d", LOCAL_DICT_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        try:
            first_line = process.stdout.readline()
        finally:
            process.stdout.close()
        _, stderr = process.communicate(timeout=120)
        self.assertTrue(first_line.strip())
        self.assertNotIn("Traceback", stderr)
        self.assertEqual(141, process.returncode)
