import itertools
import math
import os
import random
import re
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import cache
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


def _phrase_length(words: Sequence[str]) -> int:
    return sum(map(len, words))


_VOWELS = frozenset("aeiouy")
_VOWEL_BITS = {vowel: 1 << index for index, vowel in enumerate(sorted(_VOWELS))}
_MIN_RHYME = 2
_SIGNATURE_LENGTH = 2
_SIGNATURE_CAP = 1


@cache
def _syllables(word: str) -> int:
    """Count the syllables of a word from the way it is spelled.

    Counting vowel groups and then discarding a silent trailing `e` agrees with the hand counted
    table of `test/test_rank_modes.py` on 18 of its 23 words; counting vowel groups alone agrees
    on 16. Three of the five misses are hiatus, where adjacent vowel letters belong to separate
    syllables, as in `poem`, `idea` and `create`, which spelling cannot tell from a digraph such
    as the `oe` of `shoe`. Of the rest, `rhythm` spells a syllable with no vowel letter at all,
    and `wishes` loses its spoken `-es` because `sh` is not one of the letters the plural rule
    looks for. This approximates pronunciation rather than measuring it.

    Args:
        word: The word to count. Case does not matter.

    Returns:
        The number of syllables, never fewer than one.
    """
    word = word.lower()
    groups = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and groups > 1 and not word.endswith(("le", "ee", "ye")):
        groups -= 1
    if word.endswith("es") and groups > 1 and not re.search(r"[sxzcg]es$", word):
        groups -= 1
    return max(1, groups)


def _shared_suffix(first: str, second: str) -> int:
    """Count the characters two words share at the end, given that the last `_MIN_RHYME` match.

    Args:
        first: One word, whose last `_MIN_RHYME` characters equal those of `second`.
        second: The other word.

    Returns:
        The length of the longest suffix the two words share, at most the length of the shorter.
    """
    shortest = min(len(first), len(second))
    shared = _MIN_RHYME
    while shared < shortest and first[-1 - shared] == second[-1 - shared]:
        shared += 1
    return shared


def _rhyme(words: Sequence[str]) -> int:
    """Score how much the words of one phrase rhyme with each other.

    Every pair of unequal words scores the number of characters the two share at the end, as
    long as they share at least two and at least one of those is a vowel. Spelling stands in for
    sound, so this misses rhymes that spelling hides, such as `through` and `blue`, and reports
    rhymes that do not sound alike, such as `though` and `rough`.

    Args:
        words: The words of one phrase.

    Returns:
        The summed length of every rhyming suffix, higher the more the phrase rhymes.
    """
    total = 0
    for index, first in enumerate(words):
        tail = first[-_MIN_RHYME:]
        for second in words[index + 1 :]:
            if first == second or tail != second[-_MIN_RHYME:]:
                continue
            shared = _shared_suffix(first, second)
            if not _VOWELS.isdisjoint(first[-shared:]):
                total += shared
    return total


@cache
def _vowel_mask(word: str) -> int:
    mask = 0
    for character in word.lower():
        mask |= _VOWEL_BITS.get(character, 0)
    return mask


def _assonance(words: Sequence[str]) -> int:
    """Score how many vowel letters the words of one phrase share with each other.

    Each word becomes one bit per vowel letter it holds, so the set bits of a bitwise `and`
    count the vowels that a pair of words has in common.

    Args:
        words: The words of one phrase.

    Returns:
        The number of shared vowel letters, summed over every pair of words.
    """
    masks = [_vowel_mask(word) for word in words]
    return sum(
        (first & second).bit_count()
        for index, first in enumerate(masks)
        for second in masks[index + 1 :]
    )


def _syllable_spread(words: Sequence[str]) -> int:
    counts = [_syllables(word) for word in words]
    return max(counts) - min(counts)


def _brevity(words: Sequence[str]) -> float:
    return -_phrase_length(words)


def _rhythm(words: Sequence[str]) -> float:
    return -_syllable_spread(words)


def _harmony(words: Sequence[str]) -> float:
    """Blend the other three scores, weighting rhyme most.

    Rhyme drives the result, shared vowels break its ties, and the penalties on uneven syllable
    counts and on length keep the blend off long words that merely end alike. The weights were
    picked by hand against the wordlist of `test/words`.

    Args:
        words: The words of one phrase.

    Returns:
        The blended score, higher for phrases that read better aloud.
    """
    return (
        3 * _rhyme(words)
        + _assonance(words)
        - 2 * _syllable_spread(words)
        - 0.3 * _phrase_length(words)
    )


_RANKERS: dict[str, Callable[[Sequence[str]], float]] = {
    "brevity": _brevity,
    "rhyme": _rhyme,
    "rhythm": _rhythm,
    "harmony": _harmony,
}

RANK_MODES: tuple[str, ...] = tuple(_RANKERS)

DEFAULT_RANK = "harmony"


class UnknownRankError(Exception):
    """Raised when a ranking mode is not one of `RANK_MODES`."""

    def __init__(self, rank: str) -> None:
        self.rank: str = rank
        modes = ", ".join(RANK_MODES)
        super().__init__(f"unknown ranking mode {rank!r}; pick one of: {modes}")


def _ranker(rank: str) -> Callable[[Sequence[str]], float]:
    ranking = _RANKERS.get(rank)
    if ranking is None:
        raise UnknownRankError(rank)
    return ranking


def _ending_signature(words: Sequence[str]) -> str | None:
    """Name the ending that the most of a phrase's words share.

    Args:
        words: The words of one phrase.

    Returns:
        The `_SIGNATURE_LENGTH` final characters that the most words share, or `None` when every
        word of the phrase ends differently.
    """
    endings = Counter(word[-_SIGNATURE_LENGTH:].lower() for word in words)
    ending, shared_by = max(endings.items(), key=lambda item: (item[1], item[0]))
    return ending if shared_by > 1 else None


def _diverse(ranked: Sequence[tuple[str, ...]], limit: int) -> list[tuple[str, ...]]:
    """Take the best ranked phrases, capping how many of them end the same way.

    Ranking for sound collapses the variety of the endings: every phrase of a top ten can rhyme
    on `-ly` or `-ic` without repeating a single word, which reads as ten copies of one result.
    This walks the ranked phrases in order and holds back a phrase whose dominant ending, the
    one that the most of its words share, is already spoken for. Held back phrases fill the
    remaining places once the ranking runs out, so a large enough pool always fills `limit`.

    Args:
        ranked: Every candidate phrase, best ranked first.
        limit: The number of phrases to take.

    Returns:
        Up to `limit` phrases, in ranked order.
    """
    chosen: list[tuple[str, ...]] = []
    held: list[tuple[str, ...]] = []
    spoken_for: Counter[str] = Counter()
    for words in ranked:
        if len(chosen) >= limit:
            return chosen
        signature = _ending_signature(words)
        if signature is None:
            chosen.append(words)
        elif spoken_for[signature] >= _SIGNATURE_CAP:
            held.append(words)
        else:
            spoken_for[signature] += 1
            chosen.append(words)
    chosen.extend(held[: limit - len(chosen)])
    return chosen


# Every knob after the acronym is keyword-only, so the call sites PLR0913 guards against --
# a row of bare positional values -- cannot be written in the first place.
def backronyms(  # noqa: PLR0913
    acronym: str,
    *,
    min_word_length: int = 4,
    limit: int = 10,
    pool: int = 100_000,
    seed: int | None = None,
    rank: str = DEFAULT_RANK,
    allow_similar: bool = False,
    dict_path: str | Path | None = None,
) -> Iterator[Acronym]:
    """Expand an acronym into phrases whose word initials spell it.

    The space of expansions is far too large to enumerate: four letters over a wordlist of a
    quarter of a million words already hold about 2.9e16 phrases. Ranking the whole space would
    not help even if you could: the `brevity` score is separable, so an exact best-of-K fixes
    every position but the last one and the results differ only in their final word. This
    function instead draws a random sample of `pool` phrases and ranks the sample, which keeps
    the variety that sampling gives and the readability that ranking gives. When the whole space
    holds no more than `pool` phrases, it is enumerated exactly rather than sampled.

    `rank` picks what the ranking prefers. `brevity` prefers short words, which is a crude proxy
    for how common they are: a plain wordlist carries no frequency data, so visie cannot tell a
    familiar short word from an obscure one. `rhyme`, `rhythm` and `harmony` read the spelling of
    each word as a stand in for its sound, so they miss rhymes that spelling hides, such as
    `through` and `blue`, and report rhymes that do not sound alike, such as `though` and `rough`.
    Either way, the quality of the results is bounded by the wordlist.

    Ranking for sound leaves every phrase of a top ten ending the same way, so the phrases that
    are yielded are capped at one per dominant word ending unless `allow_similar` says otherwise.

    Args:
        acronym: The letters to spell, such as `HOPE`. Case does not matter.
        min_word_length: The length of the shortest word to draw from the wordlist.
        limit: The greatest number of phrases to yield.
        pool: The number of phrases to sample before ranking them.
        seed: The seed of the sampler. Pass an `int` to make the results reproducible.
        rank: What the ranking prefers, one of `RANK_MODES`.
        allow_similar: Pass `True` to yield the best ranked phrases even when they all end the
            same way.
        dict_path: The path of a wordlist, or `None` to resolve one the way `find_dictionary`
            does.

    Yields:
        Up to `limit` phrases, best ranked first, each as a non-partial `Acronym`.

    Raises:
        UnknownRankError: If `rank` is not one of `RANK_MODES`.
        UnmatchedLetterError: If `acronym` holds a character that is not a letter, or a letter
            that no wordlist entry of `min_word_length` or more characters begins with.
        DictionaryNotFoundError: If none of the candidate wordlist paths can be read.
    """
    ranking = _ranker(rank)
    letters = acronym.upper()
    if not letters.isalpha():
        raise UnmatchedLetterError(_first_non_letter(letters), min_word_length)
    buckets = _word_buckets(letters, min_word_length, dict_path)
    candidates = _candidate_phrases(buckets, pool, seed)
    ranked = sorted(candidates, key=ranking, reverse=True)
    best = ranked[:limit] if allow_similar else _diverse(ranked, limit)
    return (Acronym(*words) for words in best)
