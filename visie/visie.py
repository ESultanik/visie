import heapq
import itertools
import math
import os
import random
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path

from . import variants

DICT_ENV_VAR = "VISIE_DICT"

DICT_SEARCH_PATH: tuple[Path, ...] = (
    Path("/usr/share/dict/words"),
    Path("/usr/share/dict/web2"),
    Path("/usr/dict/words"),
)


class DictionaryNotFoundError(Exception):
    """Raised when none of the candidate wordlist paths can be read."""

    def __init__(self, tried: Iterable[Path]) -> None:
        self.tried: tuple[Path, ...] = tuple(tried)
        candidates = "\n".join(f"  {path}" for path in self.tried)
        super().__init__(
            f"no readable wordlist was found; tried:\n{candidates}\n"
            f"Install a wordlist, set the {DICT_ENV_VAR} environment variable to the path of "
            f"one, or pass the path with --dict."
        )


class UnmatchedLetterError(Exception):
    """Raised when no word in the wordlist begins with a required letter."""

    def __init__(self, letter: str, min_word_length: int) -> None:
        self.letter: str = letter
        self.min_word_length: int = min_word_length
        if letter.isalpha():
            reason = (
                f"the wordlist holds no word of {min_word_length} or more letters that begins "
                f"with it"
            )
        else:
            reason = "an acronym can only hold letters"
        super().__init__(f"cannot expand {letter!r}: {reason}")


def _candidates(dict_path: str | Path | None) -> tuple[Path, ...]:
    if dict_path is not None:
        return (Path(dict_path),)
    from_environment = os.environ.get(DICT_ENV_VAR)
    if from_environment:
        return (Path(from_environment),)
    return DICT_SEARCH_PATH


def _is_readable(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def find_dictionary(dict_path: str | Path | None = None) -> Path:
    """Locate the wordlist to enumerate initialisms from.

    An explicit path takes precedence over the `VISIE_DICT` environment variable, which in turn
    takes precedence over `DICT_SEARCH_PATH`. An explicit path and `VISIE_DICT` each name the one
    wordlist to use, so neither falls back to a lower precedence source; the entries of
    `DICT_SEARCH_PATH` are tried in order until one of them can be read.

    Args:
        dict_path: The path of a wordlist, such as the one given by the `--dict` flag. Pass
            `None` to resolve the path from the environment or the search path.

    Returns:
        The path of the first candidate wordlist that can be opened for reading.

    Raises:
        DictionaryNotFoundError: If none of the candidate paths can be read.
    """
    candidates = _candidates(dict_path)
    for candidate in candidates:
        if _is_readable(candidate):
            return candidate
    raise DictionaryNotFoundError(candidates)


class Acronym:
    def __init__(self, *matches: str, remainder: str | None = None) -> None:
        self._matches: tuple[str, ...] = matches
        self._remainder: str | None = remainder

    @property
    def remainder(self) -> str | None:
        return self._remainder

    def name(self) -> str:
        return "".join(w[0].upper() for w in self)

    def is_partial(self) -> bool:
        return bool(self._remainder)

    def __add__(self, acronym: "Acronym") -> "Acronym":
        return Acronym(*(self._matches + acronym._matches), remainder=acronym.remainder)

    def __bool__(self) -> bool:
        return not self.is_partial()

    def __iter__(self) -> Iterator[str]:
        return iter(self._matches)

    def __str__(self) -> str:
        words = " ".join(map(str, self))
        if self.is_partial():
            return f"{words}@{self.remainder}"
        else:
            return words

    def __repr__(self) -> str:
        ret = repr(self._matches)
        if self._remainder:
            ret = f"{ret}, remainder={self.remainder!r}"
        return f"{type(self).__name__}({ret})"


class Constraint(ABC):
    BEGIN_DELIM: str = ""
    END_DELIM: str = ""

    def __init__(self, children: Iterable["Constraint"] = ()) -> None:
        self._children: tuple[Constraint, ...] = tuple(children)

    @property
    def children(self) -> tuple["Constraint", ...]:
        return self._children

    @abstractmethod
    def match(self, word: str) -> Iterator[Acronym]:
        raise NotImplementedError()

    @abstractmethod
    def min_length(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def max_length(self) -> int:
        raise NotImplementedError()

    def matches(self, word: str) -> Iterator[Acronym]:
        return filter(None, self.match(word))

    def __str__(self) -> str:
        return f"{self.BEGIN_DELIM}{' '.join(map(str, self.children))}{self.END_DELIM}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.children!r})"


class DictionaryWord(Constraint):
    def __init__(self, word: str) -> None:
        super().__init__()
        self._word: str = word

    @property
    def word(self) -> str:
        return self._word

    def match(self, word: str) -> Iterator[Acronym]:
        if word[0].lower() == self.word[0].lower():
            yield Acronym(self.word, remainder=word[1:])

    def min_length(self) -> int:
        return 1

    def max_length(self) -> int:
        return 1

    def __str__(self) -> str:
        return self.word

    def __repr__(self) -> str:
        return repr(self.word)


class AnyOfConstraint(Constraint):
    """{any can occur in any order}"""

    BEGIN_DELIM = "{"
    END_DELIM = "}"

    def _match(self, remainder: str | None, children: tuple[Constraint, ...]) -> Iterator[Acronym]:
        if remainder is None:
            remainder = ""
        for i, child in enumerate(children):
            for match in child.match(remainder):
                if match:
                    yield match
                else:
                    for m in self._match(match.remainder, children[:i] + children[i + 1 :]):
                        yield match + m

    def match(self, word: str) -> Iterator[Acronym]:
        yield from self._match(word, self.children)

    def min_length(self) -> int:
        return 0

    def max_length(self) -> int:
        return sum(c.max_length() for c in self.children)


class OrderedConstraint(Constraint):
    """<all must occur in order>"""

    BEGIN_DELIM = "<"
    END_DELIM = ">"

    def _match(self, remainder: str | None, children: tuple[Constraint, ...]) -> Iterator[Acronym]:
        if not children:
            return
        if remainder is None:
            remainder = ""
        for match in children[0].match(remainder):
            if match:
                if len(children) == 1:
                    yield match
            elif len(children) == 1:
                yield match
            else:
                for m in self._match(match.remainder, children[1:]):
                    yield match + m

    def match(self, word: str) -> Iterator[Acronym]:
        return self._match(word, self.children)

    def min_length(self) -> int:
        return sum(c.min_length() for c in self.children)

    def max_length(self) -> int:
        return sum(c.max_length() for c in self.children)


class AllOfConstraint(Constraint):
    """[all must occur in any order]"""

    BEGIN_DELIM = "["
    END_DELIM = "]"

    def _match(self, remainder: str | None, children: frozenset[int]) -> Iterator[Acronym]:
        if remainder is None:
            remainder = ""
        for i, child in ((c, self.children[c]) for c in children):
            for match in child.match(remainder):
                if match:
                    if len(children) == 1:
                        yield match
                elif len(children) == 1:
                    yield match
                else:
                    for m in self._match(match.remainder, children - {i}):
                        yield match + m

    def match(self, word: str) -> Iterator[Acronym]:
        yield from self._match(word, frozenset(range(len(self.children))))

    def min_length(self) -> int:
        return sum(c.min_length() for c in self.children)

    def max_length(self) -> int:
        return sum(c.max_length() for c in self.children)


class ExactlyOneConstraint(Constraint):
    """(exactly one must occur)"""

    BEGIN_DELIM = "("
    END_DELIM = ")"

    def match(self, word: str) -> Iterator[Acronym]:
        for child in self.children:
            yield from child.match(word)

    def min_length(self) -> int:
        return min(c.min_length() for c in self.children)

    def max_length(self) -> int:
        return max(c.max_length() for c in self.children)


class Wildcard(Constraint):
    """."""

    def match(self, word: str) -> Iterator[Acronym]:
        yield Acronym(word[0], remainder=word[1:])

    def min_length(self) -> int:
        return 1

    def max_length(self) -> int:
        return 1

    def __str__(self) -> str:
        return "Wildcard<.>"

    def __repr__(self) -> str:
        return "Wildcard()"


class OptionalConstraint(OrderedConstraint):
    def match(self, word: str) -> Iterator[Acronym]:
        return itertools.chain((Acronym(remainder=word),), super().match(word))

    def min_length(self) -> int:
        return 0

    def __str__(self) -> str:
        if len(self.children) == 1:
            return f"{self.children[0]!s}?"
        else:
            return f"{super().__str__()}?"


def generate(
    constraints: Constraint,
    min_length: int = 3,
    use_variants: bool = False,
    dict_path: str | Path | None = None,
) -> Iterator[Acronym]:
    min_length = max(constraints.min_length(), min_length)
    max_length = constraints.max_length()
    with find_dictionary(dict_path).open(encoding="utf-8", errors="replace") as dictionary:
        yielded: set[str] = set()
        dict_words: Iterable[str] = (w.strip() for w in dictionary)
        if use_variants:
            dict_words = (
                variant for w in dict_words for variant in variants.generate_variants(w, max_length)
            )
        for word in dict_words:
            # Every constraint consumes exactly one letter, so a complete match is named
            # by the uppercased word it matched.
            if word.upper() in yielded:
                continue
            word_len = len(word)
            if word_len < min_length or word_len > max_length:
                continue
            for match in constraints.matches(word):
                yielded.add(match.name())
                yield match


def _first_non_letter(acronym: str) -> str:
    for character in acronym:
        if not character.isalpha():
            return character
    return ""


def _word_buckets(
    acronym: str, min_word_length: int, dict_path: str | Path | None
) -> tuple[tuple[str, ...], ...]:
    by_initial: dict[str, list[str]] = {letter: [] for letter in acronym}
    with find_dictionary(dict_path).open(encoding="utf-8", errors="replace") as dictionary:
        for line in dictionary:
            word = line.strip()
            if len(word) < min_word_length:
                continue
            bucket = by_initial.get(word[:1].upper())
            if bucket is not None:
                bucket.append(word)
    for letter in acronym:
        if not by_initial[letter]:
            raise UnmatchedLetterError(letter, min_word_length)
    return tuple(tuple(by_initial[letter]) for letter in acronym)


def _candidate_phrases(
    buckets: tuple[tuple[str, ...], ...], pool: int, seed: int | None
) -> list[tuple[str, ...]]:
    if math.prod(len(bucket) for bucket in buckets) <= pool:
        return list(itertools.product(*buckets))
    rng = random.Random(seed)
    sampled = (tuple(rng.choice(bucket) for bucket in buckets) for _ in range(pool))
    return list(dict.fromkeys(sampled))


def _phrase_length(words: tuple[str, ...]) -> int:
    return sum(len(word) for word in words)


# Every knob after the acronym is keyword-only, so the call sites PLR0913 guards against --
# a row of bare positional values -- cannot be written in the first place.
def backronyms(  # noqa: PLR0913
    acronym: str,
    *,
    min_word_length: int = 4,
    limit: int = 10,
    pool: int = 100_000,
    seed: int | None = None,
    dict_path: str | Path | None = None,
) -> Iterator[Acronym]:
    """Expand an acronym into phrases whose word initials spell it.

    The space of expansions is far too large to enumerate: four letters over a wordlist of a
    quarter of a million words already hold about 2.9e16 phrases. Ranking the whole space does
    not help, because the score is separable, so an exact best-of-K fixes every position but the
    last one and the results differ only in their final word. This function instead draws a
    random sample of `pool` phrases and ranks the sample, which keeps the variety that sampling
    gives and the readability that ranking gives. When the whole space holds no more than `pool`
    phrases, it is enumerated exactly rather than sampled.

    Phrases rank by total word length, shortest first. That is a crude proxy for how common the
    words are: a plain wordlist carries no frequency data, so visie cannot tell a familiar short
    word from an obscure one, and the quality of the results is bounded by the wordlist.

    Args:
        acronym: The letters to spell, such as `HOPE`. Case does not matter.
        min_word_length: The length of the shortest word to draw from the wordlist.
        limit: The greatest number of phrases to yield.
        pool: The number of phrases to sample before ranking them.
        seed: The seed of the sampler. Pass an `int` to make the results reproducible.
        dict_path: The path of a wordlist, or `None` to resolve one the way `find_dictionary`
            does.

    Yields:
        Up to `limit` phrases, best ranked first, each as a non-partial `Acronym`.

    Raises:
        UnmatchedLetterError: If `acronym` holds a character that is not a letter, or a letter
            that no wordlist entry of `min_word_length` or more characters begins with.
        DictionaryNotFoundError: If none of the candidate wordlist paths can be read.
    """
    letters = acronym.upper()
    if not letters.isalpha():
        raise UnmatchedLetterError(_first_non_letter(letters), min_word_length)
    buckets = _word_buckets(letters, min_word_length, dict_path)
    ranked = heapq.nsmallest(limit, _candidate_phrases(buckets, pool, seed), key=_phrase_length)
    return (Acronym(*words) for words in ranked)
