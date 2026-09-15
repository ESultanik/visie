import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path

from . import variants

DICT_PATH = str(Path("/usr/share/dict/words"))


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
    dict_path: str = DICT_PATH,
) -> Iterator[Acronym]:
    min_length = max(constraints.min_length(), min_length)
    max_length = constraints.max_length()
    with Path(dict_path).open(encoding="utf-8", errors="replace") as dictionary:
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
