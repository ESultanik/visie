import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from visie import DICT_ENV_VAR, __version__
from visie.__main__ import main

TEST_DIR = Path(__file__).parent.absolute()
LOCAL_DICT_PATH = str(TEST_DIR / "words")
MISSING_DICT_PATH = str(TEST_DIR / "no-such-wordlist")


class TestMain(unittest.TestCase):
    def test_the_version_flag_reports_the_package_version(self):
        """`--version` prints the version and exits 0 rather than demanding a constraint."""
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            main(["visie", "--version"])
        self.assertEqual(0, caught.exception.code)
        self.assertEqual(f"visie {__version__}", stdout.getvalue().strip())

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

    def test_a_missing_dictionary_is_reported(self):
        """An unreadable wordlist exits with status 1 instead of raising through `main`."""
        stderr = io.StringIO()
        with patch.dict(os.environ, {DICT_ENV_VAR: MISSING_DICT_PATH}), redirect_stderr(stderr):
            status = main(["visie", "pleasing orange home noise expeller"])
        self.assertEqual(1, status)
        self.assertIn(MISSING_DICT_PATH, stderr.getvalue())
        self.assertIn(DICT_ENV_VAR, stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

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
